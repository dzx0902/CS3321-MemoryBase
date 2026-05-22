from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.memory import (
    ActorContext,
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryDetailResponse,
    MemoryEvidenceInput,
    MemoryListResponse,
    MemorySummaryResponse,
    MemoryUpdateRequest,
)


class MemoryNotFoundError(Exception):
    pass


class MemoryValidationError(Exception):
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
    ) -> MemoryListResponse:
        ...

    def get_memory(self, memory_id: UUID, workspace_id: UUID) -> MemoryDetailResponse | None:
        ...

    def update_memory(
        self,
        memory_id: UUID,
        workspace_id: UUID,
        payload: MemoryUpdateRequest,
        actor: ActorContext,
    ) -> MemoryDetailResponse | None:
        ...

    def delete_memory(
        self, memory_id: UUID, workspace_id: UUID, actor: ActorContext
    ) -> MemoryDeleteResponse | None:
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
    ) -> MemoryListResponse:
        return self.repository.list_memories(
            workspace_id=workspace_id,
            memory_type=memory_type,
            status=status,
            access_level=access_level,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def get_memory(self, memory_id: UUID, workspace_id: UUID) -> MemoryDetailResponse:
        memory = self.repository.get_memory(memory_id, workspace_id)
        if memory is None:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        return memory

    def update_memory(
        self,
        memory_id: UUID,
        workspace_id: UUID,
        payload: MemoryUpdateRequest,
        actor: ActorContext,
    ) -> MemoryDetailResponse:
        memory = self.repository.update_memory(memory_id, workspace_id, payload, actor)
        if memory is None:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        return memory

    def delete_memory(
        self, memory_id: UUID, workspace_id: UUID, actor: ActorContext
    ) -> MemoryDeleteResponse:
        memory = self.repository.delete_memory(memory_id, workspace_id, actor)
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

                self._validate_evidence_chunks(cur, payload.workspace_id, payload.evidence)
                for evidence in payload.evidence:
                    cur.execute(
                        """
                        INSERT INTO memory_evidence (
                            memory_id,
                            chunk_id,
                            evidence_role,
                            weight,
                            note
                        )
                        VALUES (
                            %(memory_id)s,
                            %(chunk_id)s,
                            %(evidence_role)s,
                            %(weight)s,
                            %(note)s
                        )
                        """,
                        {
                            "memory_id": memory_id,
                            "chunk_id": evidence.chunk_id,
                            "evidence_role": evidence.evidence_role,
                            "weight": evidence.weight,
                            "note": evidence.note,
                        },
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
    ) -> MemoryListResponse:
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
        if status is None:
            filters.append("mi.status = 'active'")
        elif status != "all":
            filters.append("mi.status = %(status)s")
            params["status"] = status
        if access_level is not None:
            filters.append("mi.access_level = %(access_level)s")
            params["access_level"] = access_level
        if keyword is not None:
            filters.append(
                (
                    "(mi.canonical_text ILIKE %(keyword)s "
                    "OR COALESCE(mi.summary, '') ILIKE %(keyword)s)"
                )
            )
            params["keyword"] = f"%{keyword}%"

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        count_query = f"SELECT COUNT(*) AS total FROM memory_item mi {where_clause}"
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
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                cur.execute(query, params)
                rows = cur.fetchall()
        return MemoryListResponse(
            items=[MemorySummaryResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_memory(self, memory_id: UUID, workspace_id: UUID) -> MemoryDetailResponse | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                base = self._fetch_memory_detail(cur, memory_id, workspace_id)
                if base is None:
                    return None
                evidence = self._fetch_memory_evidence(cur, memory_id)
                revisions = self._fetch_memory_revisions(cur, memory_id)
                entities = self._fetch_memory_entities(cur, memory_id, workspace_id)
                scenes = self._fetch_memory_scenes(cur, memory_id, workspace_id)
        return MemoryDetailResponse(
            **base,
            evidence=evidence,
            revisions=revisions,
            entities=entities,
            scenes=scenes,
        )

    def update_memory(
        self,
        memory_id: UUID,
        workspace_id: UUID,
        payload: MemoryUpdateRequest,
        actor: ActorContext,
    ) -> MemoryDetailResponse | None:
        existing = self._get_memory_detail(memory_id, workspace_id)
        if existing is None:
            return None

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT set_config('app.actor_type', %(actor_type)s, true)
                    """,
                    {"actor_type": actor.actor_type},
                )
                cur.execute(
                    """
                    SELECT set_config('app.actor_id', %(actor_id)s, true)
                    """,
                    {"actor_id": str(actor.actor_id) if actor.actor_id else ""},
                )
                cur.execute(
                    """
                    SELECT set_config('app.revision_reason', %(revision_reason)s, true)
                    """,
                    {"revision_reason": actor.revision_reason},
                )

                cur.execute(
                    """
                    UPDATE memory_item
                    SET
                        canonical_text = %(canonical_text)s,
                        summary = %(summary)s,
                        confidence = %(confidence)s,
                        importance = %(importance)s,
                        status = %(status)s,
                        access_level = %(access_level)s
                    WHERE memory_id = %(memory_id)s
                      AND workspace_id = %(workspace_id)s
                    RETURNING *
                    """,
                    {
                        "memory_id": memory_id,
                        "workspace_id": workspace_id,
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
                    },
                )
                updated_row = cur.fetchone()
                if updated_row is None:
                    return None

                if payload.evidence is not None:
                    self._validate_evidence_chunks(cur, workspace_id, payload.evidence)
                    cur.execute(
                        "DELETE FROM memory_evidence WHERE memory_id = %(memory_id)s",
                        {"memory_id": memory_id},
                    )
                    for evidence in payload.evidence:
                        cur.execute(
                            """
                            INSERT INTO memory_evidence (
                                memory_id,
                                chunk_id,
                                evidence_role,
                                weight,
                                note
                            )
                            VALUES (
                                %(memory_id)s,
                                %(chunk_id)s,
                                %(evidence_role)s,
                                %(weight)s,
                                %(note)s
                            )
                            """,
                            {
                                "memory_id": memory_id,
                                "chunk_id": evidence.chunk_id,
                                "evidence_role": evidence.evidence_role,
                                "weight": evidence.weight,
                                "note": evidence.note,
                            },
                        )
            conn.commit()

        return self.get_memory(memory_id, workspace_id)

    def delete_memory(
        self, memory_id: UUID, workspace_id: UUID, actor: ActorContext
    ) -> MemoryDeleteResponse | None:
        existing = self._get_memory_detail(memory_id, workspace_id)
        if existing is None:
            return None

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT set_config('app.actor_type', %(actor_type)s, true)
                    """,
                    {"actor_type": actor.actor_type},
                )
                cur.execute(
                    """
                    SELECT set_config('app.actor_id', %(actor_id)s, true)
                    """,
                    {"actor_id": str(actor.actor_id) if actor.actor_id else ""},
                )
                cur.execute(
                    """
                    SELECT set_config('app.revision_reason', %(revision_reason)s, true)
                    """,
                    {"revision_reason": actor.revision_reason},
                )
                cur.execute(
                    """
                    UPDATE memory_item
                    SET status = 'archived',
                        valid_to = coalesce(valid_to, now())
                    WHERE memory_id = %(memory_id)s
                      AND workspace_id = %(workspace_id)s
                    RETURNING memory_id, status
                    """,
                    {"memory_id": memory_id, "workspace_id": workspace_id},
                )
                row = cur.fetchone()
                if row is None:
                    return None
            conn.commit()
        return MemoryDeleteResponse(**row)

    def _get_memory_summary(
        self, memory_id: UUID, workspace_id: UUID | None = None
    ) -> MemorySummaryResponse | None:
        workspace_filter = "AND mi.workspace_id = %(workspace_id)s" if workspace_id else ""
        params: dict[str, object] = {"memory_id": memory_id}
        if workspace_id:
            params["workspace_id"] = workspace_id
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
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
                    {workspace_filter}
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
                    params,
                )
                row = cur.fetchone()
        if row is None:
            return None
        return MemorySummaryResponse(**row)

    def _get_memory_detail(
        self, memory_id: UUID, workspace_id: UUID | None = None
    ) -> dict[str, object] | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                return self._fetch_memory_detail(cur, memory_id, workspace_id)

    def _fetch_memory_detail(
        self, cur, memory_id: UUID, workspace_id: UUID | None = None
    ) -> dict[str, object] | None:
        workspace_filter = "AND mi.workspace_id = %(workspace_id)s" if workspace_id else ""
        params: dict[str, object] = {"memory_id": memory_id}
        if workspace_id:
            params["workspace_id"] = workspace_id
        cur.execute(
            f"""
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
            {workspace_filter}
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
            params,
        )
        return cur.fetchone()

    def _get_memory_evidence(self, memory_id: UUID) -> list[dict[str, object]]:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                return self._fetch_memory_evidence(cur, memory_id)

    def _fetch_memory_evidence(self, cur, memory_id: UUID) -> list[dict[str, object]]:
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
              AND sd.status = 'active'
            ORDER BY sc.chunk_no ASC
            """,
            {"memory_id": memory_id},
        )
        return cur.fetchall()

    def _validate_evidence_chunks(
        self, cur, workspace_id: UUID, evidence_items: list[MemoryEvidenceInput]
    ) -> None:
        for evidence in evidence_items:
            cur.execute(
                """
                SELECT sd.workspace_id
                FROM source_chunk sc
                JOIN source_document sd ON sd.doc_id = sc.doc_id
                WHERE sc.chunk_id = %(chunk_id)s
                """,
                {"chunk_id": evidence.chunk_id},
            )
            row = cur.fetchone()
            if row is None or row["workspace_id"] != workspace_id:
                raise MemoryValidationError(
                    f"evidence chunk {evidence.chunk_id} does not belong "
                    f"to workspace {workspace_id}"
                )

    def _get_memory_revisions(self, memory_id: UUID) -> list[dict[str, object]]:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                return self._fetch_memory_revisions(cur, memory_id)

    def _fetch_memory_revisions(self, cur, memory_id: UUID) -> list[dict[str, object]]:
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

    def _get_memory_entities(
        self, memory_id: UUID, workspace_id: UUID
    ) -> list[dict[str, object]]:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                return self._fetch_memory_entities(cur, memory_id, workspace_id)

    def _fetch_memory_entities(
        self, cur, memory_id: UUID, workspace_id: UUID
    ) -> list[dict[str, object]]:
        cur.execute(
            """
            SELECT
                e.entity_id,
                e.canonical_name,
                e.entity_type,
                me.relation_role
            FROM memory_entity me
            JOIN entity e ON e.entity_id = me.entity_id
            WHERE me.memory_id = %(memory_id)s
              AND me.workspace_id = %(workspace_id)s
              AND e.status = 'active'
            ORDER BY e.canonical_name ASC, me.relation_role ASC
            """,
            {"memory_id": memory_id, "workspace_id": workspace_id},
        )
        return cur.fetchall()

    def _get_memory_scenes(
        self, memory_id: UUID, workspace_id: UUID
    ) -> list[dict[str, object]]:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                return self._fetch_memory_scenes(cur, memory_id, workspace_id)

    def _fetch_memory_scenes(
        self, cur, memory_id: UUID, workspace_id: UUID
    ) -> list[dict[str, object]]:
        cur.execute(
            """
            SELECT
                ms.scene_id,
                ms.scene_slug,
                ms.title,
                msc.cell_role,
                msc.sort_order
            FROM memory_scene_cell msc
            JOIN memory_scene ms ON ms.scene_id = msc.scene_id
            WHERE msc.memory_id = %(memory_id)s
              AND msc.workspace_id = %(workspace_id)s
            ORDER BY msc.sort_order ASC, ms.title ASC
            """,
            {"memory_id": memory_id, "workspace_id": workspace_id},
        )
        return cur.fetchall()


def _json_dumps(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, default=str)
