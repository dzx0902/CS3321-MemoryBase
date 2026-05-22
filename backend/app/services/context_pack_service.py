from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.recall import RecallEvidenceResponse, RecallMemoryResponse, RecallResponse
from .chunking import _estimate_token_count

try:  # pragma: no cover - dependency presence differs between local bootstrap states.
    import tiktoken
except ImportError:  # pragma: no cover - fallback is covered through count_tokens behavior.
    tiktoken = None


@dataclass(frozen=True, slots=True)
class ContextPackMarkdown:
    markdown: str
    citation_map: dict[str, Any]
    token_count: int


def format_context_pack(recall: RecallResponse, *, max_tokens: int = 3000) -> ContextPackMarkdown:
    memories = sorted(
        recall.memories,
        key=lambda memory: (memory.score, memory.importance, memory.confidence),
        reverse=True,
    )

    included_count = len(memories)
    while included_count > 0:
        candidate = build_markdown(recall, memories[:included_count], truncated=False)
        token_count = count_tokens(candidate.markdown)
        if token_count <= max_tokens:
            return ContextPackMarkdown(
                markdown=candidate.markdown,
                citation_map=candidate.citation_map,
                token_count=token_count,
            )
        included_count -= 1

    candidate = build_markdown(recall, memories[:1], truncated=True)
    markdown = trim_to_token_budget(candidate.markdown, max_tokens)
    return ContextPackMarkdown(
        markdown=markdown,
        citation_map=candidate.citation_map,
        token_count=count_tokens(markdown),
    )


def build_markdown(
    recall: RecallResponse,
    memories: list[RecallMemoryResponse],
    *,
    truncated: bool,
) -> ContextPackMarkdown:
    citation_map: dict[str, Any] = {"memories": {}, "evidence": {}}
    lines: list[str] = [
        "# MemoryBase Context",
        "",
        "## Relevant Memories",
    ]

    if not memories:
        lines.append("- None returned.")

    evidence_lines: list[str] = []
    risk_lines: list[str] = []
    do_not_assume_lines: list[str] = []
    evidence_index = 1

    for memory_index, memory in enumerate(memories, start=1):
        memory_ref = f"M{memory_index}"
        canonical_text = compact_text(memory.canonical_text, 600 if not truncated else 220)
        lines.append(
            "- "
            f"[{memory_ref}] [{memory.memory_type}] {canonical_text} "
            f"(score={memory.score:.3f}, confidence={memory.confidence:.3f}, "
            f"importance={memory.importance}, access={memory.access_level})"
        )
        citation_map["memories"][memory_ref] = {
            "memory_id": str(memory.memory_id),
            "memory_type": memory.memory_type,
            "status": memory.status,
            "access_level": memory.access_level,
        }
        if memory.memory_type == "risk" or memory.status == "conflicted":
            risk_lines.append(f"- [{memory_ref}] {canonical_text}")
        if memory.status in {"forgotten", "superseded", "archived"}:
            do_not_assume_lines.append(f"- [{memory_ref}] {canonical_text}")

        for evidence in memory.evidence:
            evidence_ref = f"E{evidence_index}"
            evidence_lines.append(
                format_evidence_line(evidence_ref, memory_ref, evidence, truncated)
            )
            citation_map["evidence"][evidence_ref] = {
                "memory_ref": memory_ref,
                "chunk_id": str(evidence.chunk_id),
                "doc_id": str(evidence.doc_id),
                "source_title": evidence.source_title,
                "chunk_no": evidence.chunk_no,
                "start_line": evidence.start_line,
                "end_line": evidence.end_line,
                "evidence_role": evidence.evidence_role,
            }
            evidence_index += 1

    lines.extend(["", "## Evidence"])
    lines.extend(evidence_lines or ["- None returned."])

    lines.extend(["", "## Known Conflicts / Risks"])
    lines.extend(risk_lines or ["- None returned."])

    lines.extend(["", "## Do Not Assume"])
    lines.extend(
        do_not_assume_lines or ["- No forgotten, superseded, or archived memory returned."]
    )

    lines.extend(
        [
            "",
            "## Recall Metadata",
            f"- query: {recall.query_text}",
            f"- recall_id: {recall.recall_id}",
            f"- workspace_id: {recall.workspace_id}",
            f"- result_count: {recall.result_count}",
        ]
    )
    if recall.created_at is not None:
        lines.append(f"- created_at: {recall.created_at.isoformat()}")

    if truncated:
        lines.extend(["", "[Truncated to fit token budget]"])

    markdown = "\n".join(lines).rstrip() + "\n"
    return ContextPackMarkdown(
        markdown=markdown,
        citation_map=citation_map,
        token_count=count_tokens(markdown),
    )


def format_evidence_line(
    evidence_ref: str,
    memory_ref: str,
    evidence: RecallEvidenceResponse,
    truncated: bool,
) -> str:
    line_range = ""
    if evidence.start_line is not None and evidence.end_line is not None:
        line_range = f" lines {evidence.start_line}-{evidence.end_line}"
    chunk_text = compact_text(evidence.chunk_text, 420 if not truncated else 160)
    source_label = "[agent-note] " if evidence.source_title.startswith("agent_note_") else ""
    return (
        f"- [{evidence_ref}] supports [{memory_ref}] "
        f"Source: {source_label}{evidence.source_title}, chunk {evidence.chunk_no}{line_range}, "
        f"role={evidence.evidence_role}, weight={evidence.weight:.2f}. {chunk_text}"
    )


def compact_text(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max(0, max_chars - 1)].rstrip() + "…"


def trim_to_token_budget(markdown: str, max_tokens: int) -> str:
    suffix = "\n\n[Truncated to fit token budget]\n"
    candidate = markdown
    while count_tokens(candidate) > max_tokens and len(candidate) > len(suffix) + 80:
        keep_chars = max(len(suffix) + 80, int(len(candidate) * 0.82))
        candidate = candidate[:keep_chars].rstrip() + suffix
    while count_tokens(candidate) > max_tokens and len(candidate) > len(suffix) + 20:
        candidate = candidate[:-40].rstrip() + suffix
    return candidate


def count_tokens(text: str) -> int:
    if tiktoken is not None:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    return max(_estimate_token_count(text), len(text) // 2, 1)
