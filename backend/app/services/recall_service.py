from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.recall import RecallRequest, RecallResponse
from .tokenizer import build_search_text

QUERY_EXPANSION_FILE = (
    Path(__file__).resolve().parents[3] / "data" / "recall" / "demo_query_expansions.json"
)


def _load_query_expansions(path: Path) -> dict[str, tuple[str, ...]]:
    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError(f"query expansion file must contain an object: {path}")

    expansions: dict[str, tuple[str, ...]] = {}
    for source, terms in raw_payload.items():
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"query expansion source must be a non-empty string: {path}")
        if not isinstance(terms, list) or not terms:
            raise ValueError(f"query expansion terms must be a non-empty list: {source}")
        normalized_terms: list[str] = []
        for term in terms:
            if not isinstance(term, str) or not term.strip():
                raise ValueError(f"query expansion term must be a non-empty string: {source}")
            normalized_terms.append(term.strip())
        expansions[source.strip()] = tuple(normalized_terms)
    return expansions


DEMO_QUERY_EXPANSIONS = _load_query_expansions(QUERY_EXPANSION_FILE)


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
        search_text = _expand_query_text(payload.query_text)
        keyword_patterns = [f"%{term}%" for term in _keyword_terms(payload.query_text)]
        filters: list[str] = ["mi.workspace_id = %(workspace_id)s"]
        params: dict[str, object] = {
            "workspace_id": payload.workspace_id,
            "query_text": payload.query_text,
            "search_text": search_text,
            "keyword_patterns": keyword_patterns,
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
        else:
            filters.append("mi.access_level IN ('public', 'project')")
        if payload.as_of is not None:
            filters.append(
                """
                mi.valid_from <= %(as_of)s
                AND (mi.valid_to IS NULL OR mi.valid_to > %(as_of)s)
                """
            )
            params["as_of"] = payload.as_of

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
                "as_of": payload.as_of.isoformat() if payload.as_of else None,
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
                                    websearch_to_tsquery('simple', %(search_text)s)
                                ),
                                CASE
                                    WHEN sc.chunk_text ILIKE ANY(%(keyword_patterns)s::text[])
                                    THEN 0.25
                                    ELSE 0
                                END
                            ) AS chunk_rank
                        FROM source_chunk sc
                        JOIN source_document sd ON sd.doc_id = sc.doc_id
                        WHERE sd.workspace_id = %(workspace_id)s
                          AND sd.status = 'active'
                          AND (
                            sc.search_vector @@ websearch_to_tsquery('simple', %(search_text)s)
                            OR sc.chunk_text ILIKE ANY(%(keyword_patterns)s::text[])
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
                        mi.canonical_text ILIKE ANY(%(keyword_patterns)s::text[])
                        OR COALESCE(mi.summary, '') ILIKE ANY(%(keyword_patterns)s::text[])
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
    return json.dumps(payload, default=str)


def _keyword_terms(query_text: str) -> list[str]:
    terms = [query_text]
    for source, expansions in DEMO_QUERY_EXPANSIONS.items():
        if source in query_text:
            terms.extend(expansions)
    return _dedupe_terms(terms)


def _expand_query_text(query_text: str) -> str:
    return build_search_text(" ".join(_keyword_terms(query_text)))


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for term in terms:
        normalized = term.strip()
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        deduped.append(normalized)
    return deduped
