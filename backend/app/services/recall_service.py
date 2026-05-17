from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core.database import Database
from app.models.recall import RecallRequest, RecallResponse


class RecallRepository(Protocol):
    def execute_recall(self, payload: RecallRequest) -> RecallResponse:
        ...


@dataclass(slots=True)
class RecallService:
    repository: RecallRepository

    def execute(self, payload: RecallRequest) -> RecallResponse:
        return self.repository.execute_recall(payload)


class PostgresRecallRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def execute_recall(self, payload: RecallRequest) -> RecallResponse:
        filters: list[str] = ["mi.workspace_id = %(workspace_id)s"]
        params: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "query_text": payload.query_text,
            "keyword": f"%{payload.query_text}%",
            "limit": payload.limit,
        }
        if payload.status is not None:
            filters.append("mi.status = %(status)s")
            params["status"] = payload.status
        if payload.memory_type is not None:
            filters.append("mi.memory_type = %(memory_type)s")
            params["memory_type"] = payload.memory_type
        if payload.access_level is not None:
            filters.append("mi.access_level = %(access_level)s")
            params["access_level"] = payload.access_level
        if payload.agent_id is not None:
            filters.append(
                """
                EXISTS (
                    SELECT 1
                    FROM v_agent_visible_memory vam
                    WHERE vam.agent_id = %(agent_id)s
                      AND vam.memory_id = mi.memory_id
                )
                """
            )
            params["agent_id"] = payload.agent_id

        where_clause = " AND ".join(filters)
        memories: list[dict[str, object]] = []
        memory_ids: list[UUID] = []
        recall_id = None
        created_at = None
        context_pack: dict[str, object] = {
            "query_text": payload.query_text,
            "filters": {
                "memory_type": payload.memory_type,
                "access_level": payload.access_level,
                "status": payload.status,
                "agent_id": str(payload.agent_id) if payload.agent_id else None,
            },
            "top_memory_ids": [],
            "matched_source_ids": [],
        }

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    WITH matched_chunks AS (
                        SELECT
                            sc.chunk_id,
                            sc.doc_id,
                            sd.title AS source_title,
                            sc.chunk_no,
                            sc.chunk_text,
                            sc.start_line,
                            sc.end_line,
                            GREATEST(
                                ts_rank(
                                    sc.search_vector,
                                    websearch_to_tsquery('simple', %(query_text)s)
                                ),
                                CASE
                                    WHEN sc.chunk_text ILIKE %(keyword)s THEN 0.25
                                    ELSE 0
                                END
                            ) AS chunk_rank
                        FROM source_chunk sc
                        JOIN source_document sd ON sd.doc_id = sc.doc_id
                        WHERE sd.workspace_id = %(workspace_id)s
                          AND (
                            sc.search_vector @@ websearch_to_tsquery('simple', %(query_text)s)
                            OR sc.chunk_text ILIKE %(keyword)s
                          )
                    ),
                    matched_memories AS (
                        SELECT
                            mi.memory_id,
                            mi.memory_type,
                            mi.canonical_text,
                            mi.summary,
                            mi.confidence,
                            mi.importance,
                            mi.status,
                            mi.access_level,
                            MAX(mc.chunk_rank)
                            + (AVG(me.weight) * 0.2)
                            + (mi.importance * 0.1) AS score
                        FROM matched_chunks mc
                        JOIN memory_evidence me ON me.chunk_id = mc.chunk_id
                        JOIN memory_item mi ON mi.memory_id = me.memory_id
                        WHERE {where_clause}
                        GROUP BY
                            mi.memory_id,
                            mi.memory_type,
                            mi.canonical_text,
                            mi.summary,
                            mi.confidence,
                            mi.importance,
                            mi.status,
                            mi.access_level
                    )
                    SELECT *
                    FROM matched_memories
                    UNION
                    SELECT
                        mi.memory_id,
                        mi.memory_type,
                        mi.canonical_text,
                        mi.summary,
                        mi.confidence,
                        mi.importance,
                        mi.status,
                        mi.access_level,
                        0.15 + (mi.importance * 0.1) AS score
                    FROM memory_item mi
                    WHERE {where_clause}
                      AND (
                        mi.canonical_text ILIKE %(keyword)s
                        OR COALESCE(mi.summary, '') ILIKE %(keyword)s
                      )
                    ORDER BY score DESC, importance DESC, confidence DESC
                    LIMIT %(limit)s
                    """,
                    params,
                )
                memory_rows = cur.fetchall()

                for row in memory_rows:
                    if row["memory_id"] in memory_ids:
                        continue
                    memory_ids.append(row["memory_id"])
                    cur.execute(
                        """
                        SELECT
                            me.chunk_id,
                            sc.doc_id,
                            sd.title AS source_title,
                            sc.chunk_no,
                            sc.chunk_text,
                            sc.start_line,
                            sc.end_line,
                            me.evidence_role,
                            me.weight
                        FROM memory_evidence me
                        JOIN source_chunk sc ON sc.chunk_id = me.chunk_id
                        JOIN source_document sd ON sd.doc_id = sc.doc_id
                        WHERE me.memory_id = %(memory_id)s
                        ORDER BY me.weight DESC, sc.chunk_no ASC
                        LIMIT 3
                        """,
                        {"memory_id": row["memory_id"]},
                    )
                    evidence_rows = cur.fetchall()
                    memories.append({**row, "evidence": evidence_rows})

                context_pack["top_memory_ids"] = [str(memory_id) for memory_id in memory_ids]
                context_pack["matched_source_ids"] = sorted(
                    {
                        str(evidence["doc_id"])
                        for memory in memories
                        for evidence in memory["evidence"]
                    }
                )

                cur.execute(
                    """
                    INSERT INTO recall_log (
                        workspace_id,
                        agent_id,
                        query_text,
                        filter_json,
                        result_count,
                        top_memory_ids_json,
                        context_pack_json
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(agent_id)s,
                        %(query_text)s,
                        %(filter_json)s::jsonb,
                        %(result_count)s,
                        %(top_memory_ids_json)s::jsonb,
                        %(context_pack_json)s::jsonb
                    )
                    RETURNING recall_id, created_at
                    """,
                    {
                        "workspace_id": payload.workspace_id,
                        "agent_id": payload.agent_id,
                        "query_text": payload.query_text,
                        "filter_json": _json_dumps(context_pack["filters"]),
                        "result_count": len(memories),
                        "top_memory_ids_json": _json_dumps(context_pack["top_memory_ids"]),
                        "context_pack_json": _json_dumps(context_pack),
                    },
                )
                recall_row = cur.fetchone()
                if recall_row is not None:
                    recall_id = recall_row["recall_id"]
                    created_at = recall_row["created_at"]
            conn.commit()

        return RecallResponse(
            recall_id=recall_id,
            workspace_id=payload.workspace_id,
            query_text=payload.query_text,
            result_count=len(memories),
            memories=memories,
            context_pack=context_pack,
            created_at=created_at,
        )


def _json_dumps(payload: object) -> str:
    import json

    return json.dumps(payload, default=str)
