from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from ..core.database import Database
from ..models.memory import (
    ActorContext,
    MemoryCreateRequest,
    MemoryEvidenceInput,
    MemoryListResponse,
    MemorySummaryResponse,
    MemoryType,
    MemoryUpdateRequest,
)
from ..models.memory_extraction import MemoryExtractionFromChunksRequest
from .llm_analysis import (
    LlmAnalysisDefaults,
    LlmAnalysisError,
    LlmCandidateDraft,
    OpenAICompatibleAnalysisClient,
    ResolvedLlmAnalysisOptions,
    SourceChunkForAnalysis,
    resolve_llm_options,
)
from .memory_service import MemoryService


class MemoryExtractionValidationError(Exception):
    pass


@dataclass(slots=True)
class MemoryExtractionService:
    database: Database
    memory_service: MemoryService
    llm_client: OpenAICompatibleAnalysisClient | None = None
    llm_defaults: LlmAnalysisDefaults = field(default_factory=LlmAnalysisDefaults)

    def extract_from_chunks(
        self,
        payload: MemoryExtractionFromChunksRequest,
        actor: ActorContext,
    ) -> list[MemorySummaryResponse]:
        # Extraction writes candidate memories, not active facts. Human/admin review
        # promotes or rejects them through the same memory lifecycle used elsewhere.
        chunk_rows = self._fetch_chunks(payload.workspace_id, payload.chunk_ids)
        if len(chunk_rows) != len(set(payload.chunk_ids)):
            raise MemoryExtractionValidationError(
                "all chunk_ids must exist and belong to the requested workspace"
            )

        run_id = uuid4()
        llm_options: ResolvedLlmAnalysisOptions | None = None
        if payload.method == "llm":
            try:
                llm_options = resolve_llm_options(payload.llm, self.llm_defaults)
            except LlmAnalysisError as exc:
                raise MemoryExtractionValidationError(str(exc)) from exc

        # Run-level audit lets the demo answer "which chunks produced these
        # candidate memories" without introducing extra analysis-run tables.
        start_json: dict[str, object] = {
            "run_id": str(run_id),
            "method": _audit_method(payload.method),
            "requested_chunk_ids": [str(chunk_id) for chunk_id in payload.chunk_ids],
            "max_candidates": payload.max_candidates,
        }
        if llm_options is not None:
            start_json["llm"] = {
                "provider": llm_options.provider,
                "base_url": llm_options.base_url,
                "model": llm_options.model,
                "temperature": llm_options.temperature,
                "max_tokens": llm_options.max_tokens,
            }
        self._insert_run_audit(
            workspace_id=payload.workspace_id,
            actor=actor,
            action_type="memory_extraction.run.start",
            after_json=start_json,
        )

        try:
            drafts = (
                self._llm_candidate_drafts(
                    chunk_rows,
                    max_candidates=payload.max_candidates,
                    options=llm_options,
                )
                if payload.method == "llm"
                else self._rule_based_candidate_drafts(
                    chunk_rows,
                    max_candidates=payload.max_candidates,
                )
            )
        except LlmAnalysisError as exc:
            raise MemoryExtractionValidationError(str(exc)) from exc

        row_by_chunk_id = {str(row["chunk_id"]): row for row in chunk_rows}
        candidates = [
            self._create_candidate(
                draft,
                row_by_chunk_id=row_by_chunk_id,
                workspace_id=payload.workspace_id,
                method=payload.method,
                actor=actor,
            )
            for draft in drafts
        ]
        self._insert_run_audit(
            workspace_id=payload.workspace_id,
            actor=actor,
            action_type="memory_extraction.run.complete",
            after_json={
                "run_id": str(run_id),
                "candidate_count": len(candidates),
                "candidate_memory_ids": [str(candidate.memory_id) for candidate in candidates],
            },
        )
        return candidates

    def _rule_based_candidate_drafts(
        self,
        chunk_rows: list[dict[str, object]],
        *,
        max_candidates: int,
    ) -> list[LlmCandidateDraft]:
        drafts: list[LlmCandidateDraft] = []
        seen_text: set[str] = set()
        for row in chunk_rows:
            for text in _candidate_texts(str(row["chunk_text"])):
                normalized = " ".join(text.lower().split())
                if normalized in seen_text:
                    continue
                seen_text.add(normalized)
                drafts.append(
                    LlmCandidateDraft(
                        chunk_id=_uuid_value(row["chunk_id"]),
                        canonical_text=text,
                        memory_type=_classify_memory_type(text),
                        summary=_summary(text),
                        confidence=0.65,
                        importance=_importance(text),
                    )
                )
                if len(drafts) >= max_candidates:
                    return drafts
        return drafts

    def _llm_candidate_drafts(
        self,
        chunk_rows: list[dict[str, object]],
        *,
        max_candidates: int,
        options: ResolvedLlmAnalysisOptions | None,
    ) -> list[LlmCandidateDraft]:
        if options is None:
            raise LlmAnalysisError("LLM analysis options were not resolved.")
        client = self.llm_client or OpenAICompatibleAnalysisClient()
        chunks = [
            SourceChunkForAnalysis(
                chunk_id=_uuid_value(row["chunk_id"]),
                chunk_no=int(row["chunk_no"]),
                text=str(row["chunk_text"]),
                start_line=_optional_int(row.get("start_line")),
                end_line=_optional_int(row.get("end_line")),
            )
            for row in chunk_rows
        ]
        return client.analyze(
            chunks=chunks,
            max_candidates=max_candidates,
            options=options,
        )

    def _create_candidate(
        self,
        draft: LlmCandidateDraft,
        *,
        row_by_chunk_id: dict[str, dict[str, object]],
        workspace_id: UUID,
        method: str,
        actor: ActorContext,
    ) -> MemorySummaryResponse:
        row = row_by_chunk_id[str(draft.chunk_id)]
        note = (
            "Generated by LLM-backed memory extraction."
            if method == "llm"
            else "Generated by rule-based memory extraction."
        )
        return self.memory_service.create_memory(
            MemoryCreateRequest(
                workspace_id=workspace_id,
                created_from_doc_id=row["doc_id"],
                memory_type=draft.memory_type,
                canonical_text=draft.canonical_text,
                summary=draft.summary,
                confidence=draft.confidence,
                importance=draft.importance,
                status="candidate",
                access_level="project",
                evidence=[
                    MemoryEvidenceInput(
                        chunk_id=draft.chunk_id,
                        evidence_role="source",
                        weight=1.0,
                        note=note,
                    )
                ],
            ),
            actor,
        )

    def list_candidates(
        self,
        *,
        workspace_id: UUID | None,
        memory_type: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> MemoryListResponse:
        return self.memory_service.list_memories(
            workspace_id=workspace_id,
            memory_type=memory_type,
            status="candidate",
            access_level=None,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def approve_candidate(
        self,
        memory_id: UUID,
        workspace_id: UUID,
        actor: ActorContext,
    ) -> MemorySummaryResponse:
        detail = self.memory_service.update_memory(
            memory_id,
            workspace_id,
            MemoryUpdateRequest(status="active"),
            actor,
        )
        return MemorySummaryResponse(**detail.model_dump(exclude={"evidence", "revisions"}))

    def reject_candidate(
        self,
        memory_id: UUID,
        workspace_id: UUID,
        actor: ActorContext,
    ) -> MemorySummaryResponse:
        detail = self.memory_service.update_memory(
            memory_id,
            workspace_id,
            MemoryUpdateRequest(status="rejected"),
            actor,
        )
        return MemorySummaryResponse(**detail.model_dump(exclude={"evidence", "revisions"}))

    def _fetch_chunks(
        self,
        workspace_id: UUID,
        chunk_ids: list[UUID],
    ) -> list[dict[str, object]]:
        with self.database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        sc.chunk_id,
                        sc.doc_id,
                        sc.chunk_no,
                        sc.chunk_text,
                        sc.start_line,
                        sc.end_line
                    FROM source_chunk sc
                    JOIN source_document sd ON sd.doc_id = sc.doc_id
                    WHERE sd.workspace_id = %(workspace_id)s
                      AND sd.status = 'active'
                      AND sc.chunk_id = ANY(%(chunk_ids)s::uuid[])
                    ORDER BY sc.chunk_no ASC
                    """,
                    {"workspace_id": workspace_id, "chunk_ids": chunk_ids},
                )
                return cur.fetchall()

    def _insert_run_audit(
        self,
        *,
        workspace_id: UUID,
        actor: ActorContext,
        action_type: str,
        after_json: dict[str, object],
    ) -> None:
        with self.database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log (
                        workspace_id,
                        actor_type,
                        actor_id,
                        action_type,
                        target_type,
                        target_id,
                        after_json
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(actor_type)s,
                        %(actor_id)s,
                        %(action_type)s,
                        'workspace',
                        %(workspace_id)s,
                        %(after_json)s::jsonb
                    )
                    """,
                    {
                        "workspace_id": workspace_id,
                        "actor_type": actor.actor_type,
                        "actor_id": actor.actor_id,
                        "action_type": action_type,
                        "after_json": json.dumps(after_json),
                    },
                )
            conn.commit()


def _candidate_texts(chunk_text: str) -> list[str]:
    normalized = " ".join(chunk_text.split())
    if not normalized:
        return []
    parts = [
        part.strip(" -")
        for part in re.split(r"(?<=[.!?。！？])\s+|\n+", normalized)
        if part.strip(" -")
    ]
    if not parts:
        parts = [normalized]
    return [part[:1000] for part in parts if len(part) >= 12]


def _classify_memory_type(text: str) -> MemoryType:
    lowered = text.lower()
    if any(term in lowered for term in ("decided", "decision", "选择", "决定")):
        return "decision"
    if any(term in lowered for term in ("must", "constraint", "required", "必须", "约束")):
        return "constraint"
    if any(term in lowered for term in ("policy", "permission", "权限", "规则")):
        return "policy"
    if any(term in lowered for term in ("risk", "blocked", "风险")):
        return "risk"
    if any(term in lowered for term in ("todo", "task", "should", "任务", "应该")):
        return "task"
    if any(term in lowered for term in ("prefer", "preference", "偏好")):
        return "preference"
    return "fact"


def _importance(text: str) -> int:
    memory_type = _classify_memory_type(text)
    if memory_type in {"decision", "constraint", "policy", "risk"}:
        return 4
    return 3


def _summary(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= 80:
        return compact
    return compact[:77].rstrip() + "..."


def _audit_method(method: str) -> str:
    return "rule-based" if method == "rule_based" else method


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _uuid_value(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
