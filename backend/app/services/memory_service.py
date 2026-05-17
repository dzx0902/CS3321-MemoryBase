from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core.database import Database
from app.models.memory import (
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryDetailResponse,
    MemorySummaryResponse,
    MemoryUpdateRequest,
)


class MemoryNotFoundError(Exception):
    pass


class MemoryRepository(Protocol):
    def create_memory(self, payload: MemoryCreateRequest) -> MemorySummaryResponse:
        ...

    def list_memories(
        self,
        *,
        workspace_id: UUID | None,
        memory_type: str | None,
        status: str | None,
        access_level: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> list[MemorySummaryResponse]:
        ...

    def get_memory(self, memory_id: UUID) -> MemoryDetailResponse | None:
        ...

    def update_memory(
        self, memory_id: UUID, payload: MemoryUpdateRequest
    ) -> MemoryDetailResponse | None:
        ...

    def delete_memory(self, memory_id: UUID) -> MemoryDeleteResponse | None:
        ...


@dataclass(slots=True)
class MemoryService:
    repository: MemoryRepository

    def create_memory(self, payload: MemoryCreateRequest) -> MemorySummaryResponse:
        return self.repository.create_memory(payload)

    def list_memories(
        self,
        *,
        workspace_id: UUID | None,
        memory_type: str | None,
        status: str | None,
        access_level: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> list[MemorySummaryResponse]:
        return self.repository.list_memories(
            workspace_id=workspace_id,
            memory_type=memory_type,
            status=status,
            access_level=access_level,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def get_memory(self, memory_id: UUID) -> MemoryDetailResponse:
        memory = self.repository.get_memory(memory_id)
        if memory is None:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        return memory

    def update_memory(self, memory_id: UUID, payload: MemoryUpdateRequest) -> MemoryDetailResponse:
        memory = self.repository.update_memory(memory_id, payload)
        if memory is None:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        return memory

    def delete_memory(self, memory_id: UUID) -> MemoryDeleteResponse:
        memory = self.repository.delete_memory(memory_id)
        if memory is None:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        return memory


class PostgresMemoryRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create_memory(self, payload: MemoryCreateRequest) -> MemorySummaryResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memory_item (
                        workspace_id,
                        created_from_doc_id,
                        memory_type,
                        canonical_text,
                        summary,
                        confidence,
                        importance,
                        access_level,
                        owner_user_id,
                        owner_agent_id
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(created_from_doc_id)s,
                        %(memory_type)s,
                        %(canonical_text)s,
                        %(summary)s,
                        %(confidence)s,
                        %(importance)s,
                        %(access_level)s,
                        %(owner_user_id)s,
                        %(owner_agent_id)s
                    )
                    RETURNING memory_id
                    """,
                    payload.model_dump(),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("failed to create memory")
                memory_id = row["memory_id"]

                for chunk_id in payload.evidence_chunk_ids:
                    cur.execute(
                        """
                        INSERT INTO memory_evidence (
                            memory_id,
                            chunk_id,
                            evidence_role,
                            weight
                        )
                        VALUES (%(memory_id)s, %(chunk_id)s, 'supports', 1.0)
                        """,
                        {"memory_id": memory_id, "chunk_id": chunk_id},
                    )

            conn.commit()
        summary = self._get_memory_summary(memory_id)
        if summary is None:
            raise RuntimeError("created memory cannot be loaded")
        return summary

    def list_memories(
        self,
        *,
        workspace_id: UUID | None,
        memory_type: str | None,
        status: str | None,
        access_level: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> list[MemorySummaryResponse]:
        filters: list[str] = []
        params: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        if workspace_id is not None:
            filters.append("mi.workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        if memory_type is not None:
            filters.append("mi.memory_type = %(memory_type)s")
            params["memory_type"] = memory_type
        if status is not None:
            filters.append("mi.status = %(status)s")
            params["status"] = status
        if access_level is not None:
            filters.append("mi.access_level = %(access_level)s")
            params["access_level"] = access_level
        if keyword is not None:
            filters.append(
                (
                    "mi.canonical_text ILIKE %(keyword)s "
                    "OR COALESCE(mi.summary, '') ILIKE %(keyword)s"
                )
            )
            params["keyword"] = f"%{keyword}%"

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        query = f"""
            SELECT
                mi.memory_id,
                mi.workspace_id,
                mi.created_from_doc_id,
                mi.memory_type,
                mi.canonical_text,
                mi.summary,
                mi.confidence,
                mi.importance,
                mi.status,
                mi.access_level,
                mi.current_revision_no,
                mi.created_at,
                mi.updated_at,
                COUNT(me.evidence_id) AS evidence_count
            FROM memory_item mi
            LEFT JOIN memory_evidence me ON me.memory_id = mi.memory_id
            {where_clause}
            GROUP BY
                mi.memory_id,
                mi.workspace_id,
                mi.created_from_doc_id,
                mi.memory_type,
                mi.canonical_text,
                mi.summary,
                mi.confidence,
                mi.importance,
                mi.status,
                mi.access_level,
                mi.current_revision_no,
                mi.created_at,
                mi.updated_at
            ORDER BY mi.updated_at DESC
            LIMIT %(limit)s OFFSET %(offset)s
        """
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [MemorySummaryResponse(**row) for row in rows]

    def get_memory(self, memory_id: UUID) -> MemoryDetailResponse | None:
        base = self._get_memory_detail(memory_id)
        if base is None:
            return None
        evidence = self._get_memory_evidence(memory_id)
        revisions = self._get_memory_revisions(memory_id)
        return MemoryDetailResponse(**base, evidence=evidence, revisions=revisions)

    def update_memory(
        self, memory_id: UUID, payload: MemoryUpdateRequest
    ) -> MemoryDetailResponse | None:
        existing = self._get_memory_detail(memory_id)
        if existing is None:
            return None

        next_revision_no = existing["current_revision_no"] + 1
        updated_row = None

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE memory_item
                    SET
                        canonical_text = %(canonical_text)s,
                        summary = %(summary)s,
                        confidence = %(confidence)s,
                        importance = %(importance)s,
                        status = %(status)s,
                        access_level = %(access_level)s,
                        current_revision_no = %(current_revision_no)s
                    WHERE memory_id = %(memory_id)s
                    RETURNING *
                    """,
                    {
                        "memory_id": memory_id,
                        "canonical_text": payload.canonical_text or existing["canonical_text"],
                        "summary": payload.summary
                        if payload.summary is not None
                        else existing["summary"],
                        "confidence": payload.confidence
                        if payload.confidence is not None
                        else existing["confidence"],
                        "importance": payload.importance
                        if payload.importance is not None
                        else existing["importance"],
                        "status": payload.status or existing["status"],
                        "access_level": payload.access_level or existing["access_level"],
                        "current_revision_no": next_revision_no,
                    },
                )
                updated_row = cur.fetchone()
                if updated_row is None:
                    return None

                cur.execute(
                    """
                    INSERT INTO memory_revision (
                        memory_id,
                        revision_no,
                        revision_text,
                        revision_summary,
                        revision_reason,
                        editor_type,
                        editor_id
                    )
                    VALUES (
                        %(memory_id)s,
                        %(revision_no)s,
                        %(revision_text)s,
                        %(revision_summary)s,
                        %(revision_reason)s,
                        %(editor_type)s,
                        %(editor_id)s
                    )
                    """,
                    {
                        "memory_id": memory_id,
                        "revision_no": next_revision_no,
                        "revision_text": updated_row["canonical_text"],
                        "revision_summary": updated_row["summary"],
                        "revision_reason": payload.revision_reason,
                        "editor_type": payload.editor_type,
                        "editor_id": payload.editor_id,
                    },
                )

                if payload.evidence_chunk_ids is not None:
                    cur.execute(
                        "DELETE FROM memory_evidence WHERE memory_id = %(memory_id)s",
                        {"memory_id": memory_id},
                    )
                    for chunk_id in payload.evidence_chunk_ids:
                        cur.execute(
                            """
                            INSERT INTO memory_evidence (
                                memory_id,
                                chunk_id,
                                evidence_role,
                                weight
                            )
                            VALUES (%(memory_id)s, %(chunk_id)s, 'supports', 1.0)
                            """,
                            {"memory_id": memory_id, "chunk_id": chunk_id},
                        )

                cur.execute(
                    """
                    INSERT INTO audit_log (
                        workspace_id,
                        actor_type,
                        actor_id,
                        action_type,
                        target_type,
                        target_id,
                        before_json,
                        after_json
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(actor_type)s,
                        %(actor_id)s,
                        'memory.update',
                        'memory_item',
                        %(target_id)s,
                        %(before_json)s::jsonb,
                        %(after_json)s::jsonb
                    )
                    """,
                    {
                        "workspace_id": existing["workspace_id"],
                        "actor_type": payload.editor_type,
                        "actor_id": payload.editor_id,
                        "target_id": memory_id,
                        "before_json": _json_dumps(existing),
                        "after_json": _json_dumps(updated_row),
                    },
                )

            conn.commit()

        return self.get_memory(memory_id)

    def delete_memory(self, memory_id: UUID) -> MemoryDeleteResponse | None:
        existing = self._get_memory_detail(memory_id)
        if existing is None:
            return None

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE memory_item
                    SET status = 'archived'
                    WHERE memory_id = %(memory_id)s
                    RETURNING memory_id, status
                    """,
                    {"memory_id": memory_id},
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cur.execute(
                    """
                    INSERT INTO audit_log (
                        workspace_id,
                        actor_type,
                        action_type,
                        target_type,
                        target_id,
                        before_json,
                        after_json
                    )
                    VALUES (
                        %(workspace_id)s,
                        'system',
                        'memory.soft_delete',
                        'memory_item',
                        %(target_id)s,
                        %(before_json)s::jsonb,
                        %(after_json)s::jsonb
                    )
                    """,
                    {
                        "workspace_id": existing["workspace_id"],
                        "target_id": memory_id,
                        "before_json": _json_dumps(existing),
                        "after_json": _json_dumps(row),
                    },
                )
            conn.commit()
        return MemoryDeleteResponse(**row)

    def _get_memory_summary(self, memory_id: UUID) -> MemorySummaryResponse | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        mi.memory_id,
                        mi.workspace_id,
                        mi.created_from_doc_id,
                        mi.memory_type,
                        mi.canonical_text,
                        mi.summary,
                        mi.confidence,
                        mi.importance,
                        mi.status,
                        mi.access_level,
                        mi.current_revision_no,
                        mi.created_at,
                        mi.updated_at,
                        COUNT(me.evidence_id) AS evidence_count
                    FROM memory_item mi
                    LEFT JOIN memory_evidence me ON me.memory_id = mi.memory_id
                    WHERE mi.memory_id = %(memory_id)s
                    GROUP BY
                        mi.memory_id,
                        mi.workspace_id,
                        mi.created_from_doc_id,
                        mi.memory_type,
                        mi.canonical_text,
                        mi.summary,
                        mi.confidence,
                        mi.importance,
                        mi.status,
                        mi.access_level,
                        mi.current_revision_no,
                        mi.created_at,
                        mi.updated_at
                    """,
                    {"memory_id": memory_id},
                )
                row = cur.fetchone()
        if row is None:
            return None
        return MemorySummaryResponse(**row)

    def _get_memory_detail(self, memory_id: UUID) -> dict[str, object] | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        mi.memory_id,
                        mi.workspace_id,
                        mi.created_from_doc_id,
                        mi.memory_type,
                        mi.canonical_text,
                        mi.summary,
                        mi.confidence,
                        mi.importance,
                        mi.status,
                        mi.access_level,
                        mi.owner_user_id,
                        mi.owner_agent_id,
                        mi.valid_from,
                        mi.valid_to,
                        mi.superseded_by_memory_id,
                        mi.current_revision_no,
                        mi.created_at,
                        mi.updated_at,
                        COUNT(me.evidence_id) AS evidence_count
                    FROM memory_item mi
                    LEFT JOIN memory_evidence me ON me.memory_id = mi.memory_id
                    WHERE mi.memory_id = %(memory_id)s
                    GROUP BY
                        mi.memory_id,
                        mi.workspace_id,
                        mi.created_from_doc_id,
                        mi.memory_type,
                        mi.canonical_text,
                        mi.summary,
                        mi.confidence,
                        mi.importance,
                        mi.status,
                        mi.access_level,
                        mi.owner_user_id,
                        mi.owner_agent_id,
                        mi.valid_from,
                        mi.valid_to,
                        mi.superseded_by_memory_id,
                        mi.current_revision_no,
                        mi.created_at,
                        mi.updated_at
                    """,
                    {"memory_id": memory_id},
                )
                return cur.fetchone()

    def _get_memory_evidence(self, memory_id: UUID) -> list[dict[str, object]]:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        me.evidence_id,
                        me.chunk_id,
                        me.evidence_role,
                        me.weight,
                        me.note,
                        sc.doc_id,
                        sd.title AS source_title,
                        sc.chunk_no,
                        sc.chunk_text,
                        sc.start_line,
                        sc.end_line
                    FROM memory_evidence me
                    JOIN source_chunk sc ON sc.chunk_id = me.chunk_id
                    JOIN source_document sd ON sd.doc_id = sc.doc_id
                    WHERE me.memory_id = %(memory_id)s
                    ORDER BY sc.chunk_no ASC
                    """,
                    {"memory_id": memory_id},
                )
                return cur.fetchall()

    def _get_memory_revisions(self, memory_id: UUID) -> list[dict[str, object]]:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        revision_no,
                        revision_text,
                        revision_summary,
                        revision_reason,
                        editor_type,
                        editor_id,
                        created_at
                    FROM memory_revision
                    WHERE memory_id = %(memory_id)s
                    ORDER BY created_at ASC, revision_no ASC
                    """,
                    {"memory_id": memory_id},
                )
                return cur.fetchall()


def _json_dumps(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, default=str)
