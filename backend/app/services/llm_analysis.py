"""Optional LLM-backed candidate extraction.

This is the opt-in counterpart to the rule-based extraction path. It calls an
OpenAI-compatible chat-completions endpoint, asks the model to return strict
JSON, and turns that JSON into candidate-memory drafts. The output stays
compatible with the rule-based pipeline: every draft is meant to become a
``status='candidate'`` MemoryItem bound to exactly one source chunk and still
needs human approval before it enters the active lifecycle. The model never
writes facts directly, so all responses are validated and clamped here rather
than trusted as-is.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from uuid import UUID

import httpx

from ..models.memory import MemoryType
from ..models.memory_extraction import LlmAnalysisOptions

# Memory types we accept back from the model. Any value outside this set is
# coerced to "fact" so a hallucinated label can never reach the database.
ALLOWED_MEMORY_TYPES: tuple[MemoryType, ...] = (
    "episodic",
    "semantic",
    "fact",
    "profile",
    "procedural",
    "decision",
    "preference",
    "task",
    "risk",
    "constraint",
    "policy",
    "summary",
)


class LlmAnalysisError(Exception):
    """Raised for any failure in the LLM analysis path (config, transport, JSON)."""


@dataclass(frozen=True, slots=True)
class LlmAnalysisDefaults:
    """Fallback options sourced from settings/env (the ``LLM_ANALYSIS_*`` vars).

    ``api_key`` is empty by default: the feature is off until a key is supplied
    either here (from env) or per-request.
    """

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    provider: str = "openai-compatible"
    temperature: float = 0.1
    max_tokens: int = 1200


@dataclass(frozen=True, slots=True)
class SourceChunkForAnalysis:
    """A single source chunk handed to the model, with optional line range."""

    chunk_id: UUID
    chunk_no: int
    text: str
    start_line: int | None = None
    end_line: int | None = None


@dataclass(frozen=True, slots=True)
class LlmCandidateDraft:
    """One validated candidate memory parsed from the model response."""

    chunk_id: UUID
    canonical_text: str
    memory_type: MemoryType
    summary: str | None
    confidence: float
    importance: int


@dataclass(frozen=True, slots=True)
class ResolvedLlmAnalysisOptions:
    """Effective options after merging per-request overrides with defaults."""

    api_key: str
    base_url: str
    model: str
    provider: str
    temperature: float
    max_tokens: int


class OpenAICompatibleAnalysisClient:
    """Thin client over any OpenAI-compatible ``/chat/completions`` endpoint."""

    def __init__(self, *, timeout: float = 60.0) -> None:
        self._timeout = timeout

    def analyze(
        self,
        *,
        chunks: list[SourceChunkForAnalysis],
        max_candidates: int,
        options: ResolvedLlmAnalysisOptions,
    ) -> list[LlmCandidateDraft]:
        """Send chunks to the model and return validated candidate drafts."""
        if not chunks:
            return []
        content = self._complete_json(
            system_prompt=_system_prompt(),
            user_prompt=_user_prompt(chunks=chunks, max_candidates=max_candidates),
            options=options,
        )
        return parse_llm_candidates(content, chunks=chunks, max_candidates=max_candidates)

    def _complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        options: ResolvedLlmAnalysisOptions,
    ) -> str:
        """POST one chat completion and return the raw message content string."""
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{options.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {options.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": options.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": options.temperature,
                    "max_tokens": options.max_tokens,
                    # Ask the endpoint for a JSON object; we still parse defensively
                    # below since not every compatible provider honors this.
                    "response_format": {"type": "json_object"},
                },
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LlmAnalysisError(f"LLM analysis request failed: {exc}") from exc
        data = response.json()
        # Pull choices[0].message.content without assuming the shape is present.
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise LlmAnalysisError("LLM analysis response did not contain JSON content.")
        return content


def resolve_llm_options(
    requested: LlmAnalysisOptions | None,
    defaults: LlmAnalysisDefaults,
) -> ResolvedLlmAnalysisOptions:
    """Merge per-request options over env defaults and validate the result.

    Per-request values win when set, otherwise the env-backed defaults apply.
    A missing API key / base URL / model raises ``LlmAnalysisError`` so callers
    fail fast instead of sending an unauthenticated request.
    """
    api_key = (requested.api_key if requested and requested.api_key else defaults.api_key).strip()
    base_url = (
        requested.base_url if requested and requested.base_url else defaults.base_url
    ).strip()
    model = (requested.model if requested and requested.model else defaults.model).strip()
    provider = (
        requested.provider if requested and requested.provider else defaults.provider
    ).strip()
    temperature = (
        requested.temperature
        if requested and requested.temperature is not None
        else defaults.temperature
    )
    max_tokens = (
        requested.max_tokens
        if requested and requested.max_tokens is not None
        else defaults.max_tokens
    )
    if not api_key:
        raise LlmAnalysisError(
            "LLM analysis requires an API key in request.llm.api_key or LLM_ANALYSIS_API_KEY."
        )
    if not base_url:
        raise LlmAnalysisError("LLM analysis requires a base URL.")
    if not model:
        raise LlmAnalysisError("LLM analysis requires a model name.")
    return ResolvedLlmAnalysisOptions(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        model=model,
        provider=provider or "openai-compatible",
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )


def parse_llm_candidates(
    content: str,
    *,
    chunks: list[SourceChunkForAnalysis],
    max_candidates: int,
) -> list[LlmCandidateDraft]:
    """Parse model JSON into validated drafts, dropping anything unusable.

    Every candidate is anchored to a real source chunk, deduplicated by
    normalized text, length-filtered, and has its type/confidence/importance
    coerced into valid ranges. Malformed entries are skipped rather than raising,
    so one bad item never discards the whole response.
    """
    try:
        payload = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError as exc:
        raise LlmAnalysisError(f"LLM analysis returned invalid JSON: {exc}") from exc

    raw_candidates = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(raw_candidates, list):
        raise LlmAnalysisError("LLM analysis JSON must contain a candidates array.")

    chunk_ids = {str(chunk.chunk_id): chunk.chunk_id for chunk in chunks}
    drafts: list[LlmCandidateDraft] = []
    seen_text: set[str] = set()
    for raw in raw_candidates:
        if not isinstance(raw, dict):
            continue
        # Drop candidates we cannot anchor back to one of the input chunks.
        chunk_id = _resolve_chunk_id(raw.get("chunk_id"), raw.get("chunk_no"), chunks, chunk_ids)
        if chunk_id is None:
            continue
        text = _coerce_text(raw.get("canonical_text") or raw.get("text"))
        if len(text) < 12:  # too short to be a meaningful memory
            continue
        # Deduplicate on case/whitespace-insensitive text.
        normalized = " ".join(text.lower().split())
        if normalized in seen_text:
            continue
        seen_text.add(normalized)
        drafts.append(
            LlmCandidateDraft(
                chunk_id=chunk_id,
                canonical_text=text[:1000],
                memory_type=_coerce_memory_type(raw.get("memory_type") or raw.get("type")),
                summary=_optional_summary(raw.get("summary"), text),
                confidence=_coerce_float(raw.get("confidence"), default=0.7, minimum=0, maximum=1),
                importance=_coerce_int(raw.get("importance"), default=3, minimum=1, maximum=5),
            )
        )
        if len(drafts) >= max_candidates:
            break
    return drafts


def _system_prompt() -> str:
    # Pins the model to the rule-based pipeline's contract: JSON only, candidate
    # semantics, allowed types, and the same confidence/importance conventions.
    return (
        "You are MemoryBase's optional LLM analysis pipeline. Extract candidate memories "
        "from source chunks for later human review. Keep behavior compatible with the "
        "rule-based pipeline: every output item must become a status='candidate' "
        "MemoryItem linked to exactly one source chunk. Return only JSON. Do not include "
        "markdown or explanations. Use the original language of the source text. "
        "Prefer concise, atomic memories that preserve decisions, constraints, policies, "
        "risks, tasks, preferences, durable facts, procedures, and summaries. Avoid "
        "duplicates and avoid unsupported inference. Memory type must be one of: "
        f"{', '.join(ALLOWED_MEMORY_TYPES)}. Confidence is 0..1; use 0.65 for weak "
        "rule-like extraction, 0.75-0.9 when the text directly supports the candidate. "
        "Importance is 1..5; use 4 for decisions, constraints, policies, and risks; "
        "use 3 for ordinary facts/tasks; use 5 only for central project commitments."
    )


def _user_prompt(*, chunks: list[SourceChunkForAnalysis], max_candidates: int) -> str:
    # Serializes each chunk as one JSON line and spells out the exact response
    # shape, so the model echoes back chunk_id values we can re-anchor against.
    chunk_lines = []
    for chunk in chunks:
        line_range = (
            f"lines {chunk.start_line}-{chunk.end_line}"
            if chunk.start_line is not None and chunk.end_line is not None
            else "lines unknown"
        )
        chunk_lines.append(
            json.dumps(
                {
                    "chunk_id": str(chunk.chunk_id),
                    "chunk_no": chunk.chunk_no,
                    "line_range": line_range,
                    "text": chunk.text,
                },
                ensure_ascii=False,
            )
        )
    return (
        "Extract at most "
        f"{max_candidates} candidate memories from these chunks.\n\n"
        "Return this exact JSON shape:\n"
        "{\n"
        '  "candidates": [\n'
        "    {\n"
        '      "chunk_id": "uuid copied from source chunk",\n'
        '      "canonical_text": "atomic memory text supported by that chunk",\n'
        '      "memory_type": '
        '"decision|constraint|policy|risk|task|preference|fact|summary|'
        'semantic|procedural|episodic|profile",\n'
        '      "summary": "short label, max 80 chars",\n'
        '      "confidence": 0.0,\n'
        '      "importance": 3\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Source chunks:\n"
        + "\n".join(chunk_lines)
    )


def _strip_json_fence(content: str) -> str:
    # Some providers wrap JSON in a ```json ... ``` markdown fence; remove it.
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _resolve_chunk_id(
    raw_chunk_id: object,
    raw_chunk_no: object,
    chunks: list[SourceChunkForAnalysis],
    chunk_ids: dict[str, UUID],
) -> UUID | None:
    # Prefer an exact chunk_id match, then fall back to chunk_no. If neither is
    # given but only one chunk was sent, attribute it to that chunk; otherwise
    # we cannot anchor the candidate and return None so the caller drops it.
    if isinstance(raw_chunk_id, str) and raw_chunk_id in chunk_ids:
        return chunk_ids[raw_chunk_id]
    chunk_no = _coerce_int_or_none(raw_chunk_no)
    if chunk_no is not None:
        for chunk in chunks:
            if chunk.chunk_no == chunk_no:
                return chunk.chunk_id
    return chunks[0].chunk_id if len(chunks) == 1 else None


# The helpers below defensively coerce untrusted model output: collapse text
# whitespace, cap summary length, validate the memory type, and clamp numeric
# fields into their allowed ranges so a bad value never reaches the database.


def _coerce_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _optional_summary(value: object, fallback_text: str) -> str:
    summary = _coerce_text(value)
    if not summary:
        summary = fallback_text
    if len(summary) <= 80:
        return summary
    return summary[:77].rstrip() + "..."


def _coerce_memory_type(value: object) -> MemoryType:
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        if normalized in ALLOWED_MEMORY_TYPES:
            return normalized  # type: ignore[return-value]
    return "fact"


def _coerce_float(value: object, *, default: float, minimum: float, maximum: float) -> float:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        candidate = default
    return min(max(candidate, minimum), maximum)


def _coerce_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    candidate = _coerce_int_or_none(value)
    if candidate is None:
        candidate = default
    return min(max(candidate, minimum), maximum)


def _coerce_int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
