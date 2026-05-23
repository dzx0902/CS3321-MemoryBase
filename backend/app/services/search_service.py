from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from ..core.database import Database
from ..models.search import SearchRequest, SearchResponse
from ._search_query import build_websearch_query
from .recall_service import _expand_query_text

# Empirically tuned on PR4 adversarial gold; future eval-driven tuning starts here.
TRIGRAM_SIMILARITY_THRESHOLD = 0.35


class SearchRepository(Protocol):
    def execute_search(self, payload: SearchRequest) -> SearchResponse:
        ...


@dataclass(slots=True)
class SearchService:
    repository: SearchRepository

    def execute(self, payload: SearchRequest) -> SearchResponse:
        return self.repository.execute_search(payload)


class PostgresSearchRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def execute_search(self, payload: SearchRequest) -> SearchResponse:
        tokenized_query = _expand_query_text(payload.query_text)
        params = {
            "workspace_id": payload.workspace_id,
            "agent_id": payload.agent_id,
            "query_text": payload.query_text,
            "tokenized_query": tokenized_query,
            "websearch_query": build_websearch_query(tokenized_query),
            "limit": payload.limit,
            "include_chunks": payload.scope in ("all", "chunks"),
            "include_memories": payload.scope in ("all", "memories"),
            "include_sources": payload.scope in ("all", "sources"),
            "trigram_threshold": TRIGRAM_SIMILARITY_THRESHOLD,
        }
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(SEARCH_SQL, params)
                rows = cur.fetchall()

        items = [
            {
                "result_type": row["result_type"],
                "result_id": row["result_id"],
                "doc_id": row["doc_id"],
                "source_path": row["source_path"],
                "source_title": row["source_title"],
                "start_line": row["start_line"],
                "end_line": row["end_line"],
                "snippet": _make_snippet(row["body_text"]),
                "score": float(row["rrf_score"]),
                "strategies": list(row["strategies"] or []),
            }
            for row in rows
        ]
        return SearchResponse(
            workspace_id=payload.workspace_id,
            query_text=payload.query_text,
            tokenized_query=tokenized_query,
            result_count=len(items),
            items=items,
        )


def _make_snippet(text: str | None, *, max_chars: int = 240) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 1].rstrip()}…"


SEARCH_SQL = """
WITH
query_input AS (
  SELECT
    %(workspace_id)s::uuid AS workspace_id,
    %(agent_id)s::uuid AS agent_id,
    %(query_text)s::text AS query_text,
    %(tokenized_query)s::text AS tokenized_query,
    websearch_to_tsquery('simple', %(websearch_query)s) AS token_query,
    %(include_chunks)s::boolean AS include_chunks,
    %(include_memories)s::boolean AS include_memories,
    %(include_sources)s::boolean AS include_sources,
    %(trigram_threshold)s::double precision AS trigram_threshold
),
chunk_fts AS (
  SELECT
    'chunk'::text AS result_type,
    sc.chunk_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    sc.start_line,
    sc.end_line,
    sc.chunk_text AS body_text,
    'chunk_fts'::text AS strategy,
    ts_rank_cd(sc.search_vector, qi.token_query) AS raw_score,
    1.0::numeric AS route_weight
  FROM query_input qi
  JOIN source_document sd ON sd.workspace_id = qi.workspace_id
  JOIN source_chunk sc ON sc.doc_id = sd.doc_id
  WHERE qi.include_chunks
    AND sd.status = 'active'
    AND sc.search_vector @@ qi.token_query
),
memory_fts_public AS (
  SELECT
    'memory'::text AS result_type,
    mi.memory_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    mi.canonical_text AS body_text,
    'memory_fts'::text AS strategy,
    ts_rank_cd(mi.search_vector, qi.token_query) AS raw_score,
    1.0::numeric AS route_weight
  FROM query_input qi
  JOIN memory_item mi ON mi.workspace_id = qi.workspace_id
  LEFT JOIN source_document sd ON sd.doc_id = mi.created_from_doc_id
  WHERE qi.include_memories
    AND mi.status = 'active'
    AND qi.agent_id IS NULL
    AND mi.access_level IN ('public', 'project')
    AND mi.search_vector @@ qi.token_query
),
memory_fts_agent_visible AS (
  SELECT
    'memory'::text AS result_type,
    mi.memory_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    mi.canonical_text AS body_text,
    'memory_fts'::text AS strategy,
    ts_rank_cd(mi.search_vector, qi.token_query) AS raw_score,
    1.0::numeric AS route_weight
  FROM query_input qi
  JOIN memory_item mi ON mi.workspace_id = qi.workspace_id
  LEFT JOIN source_document sd ON sd.doc_id = mi.created_from_doc_id
  WHERE qi.include_memories
    AND mi.status = 'active'
    AND qi.agent_id IS NOT NULL
    AND mi.search_vector @@ qi.token_query
    AND EXISTS (
      SELECT 1
      FROM v_agent_visible_memory vam
      WHERE vam.agent_id = qi.agent_id
        AND vam.memory_id = mi.memory_id
    )
),
trigram_chunk_fuzzy AS (
  SELECT
    'chunk'::text AS result_type,
    sc.chunk_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    sc.start_line,
    sc.end_line,
    sc.chunk_text AS body_text,
    'trigram_fuzzy'::text AS strategy,
    word_similarity(qi.query_text, sc.chunk_text) AS raw_score,
    0.6::numeric AS route_weight
  FROM query_input qi
  JOIN source_document sd ON sd.workspace_id = qi.workspace_id
  JOIN source_chunk sc ON sc.doc_id = sd.doc_id
  WHERE qi.include_chunks
    AND sd.status = 'active'
    AND word_similarity(qi.query_text, sc.chunk_text) > qi.trigram_threshold
),
trigram_memory_public AS (
  SELECT
    'memory'::text AS result_type,
    mi.memory_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    mi.canonical_text AS body_text,
    'trigram_fuzzy'::text AS strategy,
    word_similarity(qi.query_text, mi.canonical_text) AS raw_score,
    0.6::numeric AS route_weight
  FROM query_input qi
  JOIN memory_item mi ON mi.workspace_id = qi.workspace_id
  LEFT JOIN source_document sd ON sd.doc_id = mi.created_from_doc_id
  WHERE qi.include_memories
    AND mi.status = 'active'
    AND qi.agent_id IS NULL
    AND mi.access_level IN ('public', 'project')
    AND word_similarity(qi.query_text, mi.canonical_text) > qi.trigram_threshold
),
trigram_memory_agent_visible AS (
  SELECT
    'memory'::text AS result_type,
    mi.memory_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    mi.canonical_text AS body_text,
    'trigram_fuzzy'::text AS strategy,
    word_similarity(qi.query_text, mi.canonical_text) AS raw_score,
    0.6::numeric AS route_weight
  FROM query_input qi
  JOIN memory_item mi ON mi.workspace_id = qi.workspace_id
  LEFT JOIN source_document sd ON sd.doc_id = mi.created_from_doc_id
  WHERE qi.include_memories
    AND mi.status = 'active'
    AND qi.agent_id IS NOT NULL
    AND word_similarity(qi.query_text, mi.canonical_text) > qi.trigram_threshold
    AND EXISTS (
      SELECT 1
      FROM v_agent_visible_memory vam
      WHERE vam.agent_id = qi.agent_id
        AND vam.memory_id = mi.memory_id
    )
),
title_boost AS (
  SELECT
    'source'::text AS result_type,
    sd.doc_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    sd.raw_text AS body_text,
    'title_boost'::text AS strategy,
    word_similarity(qi.query_text, sd.title) AS raw_score,
    0.5::numeric AS route_weight
  FROM query_input qi
  JOIN source_document sd ON sd.workspace_id = qi.workspace_id
  WHERE qi.include_sources
    AND sd.status = 'active'
    AND word_similarity(qi.query_text, sd.title) > qi.trigram_threshold
),
route_union AS (
  SELECT * FROM chunk_fts
  UNION ALL
  SELECT * FROM memory_fts_public
  UNION ALL
  SELECT * FROM memory_fts_agent_visible
  UNION ALL
  SELECT * FROM trigram_chunk_fuzzy
  UNION ALL
  SELECT * FROM trigram_memory_public
  UNION ALL
  SELECT * FROM trigram_memory_agent_visible
  UNION ALL
  SELECT * FROM title_boost
),
ranked AS (
  SELECT
    *,
    row_number() OVER (
      PARTITION BY strategy
      ORDER BY raw_score DESC, result_id
    ) AS route_rank
  FROM route_union
),
fused AS (
  SELECT
    result_type,
    result_id,
    doc_id,
    source_title,
    source_path,
    start_line,
    end_line,
    body_text,
    array_agg(strategy ORDER BY strategy) AS strategies,
    sum(route_weight / (60 + route_rank)) AS rrf_score
  FROM ranked
  GROUP BY
    result_type,
    result_id,
    doc_id,
    source_title,
    source_path,
    start_line,
    end_line,
    body_text
)
SELECT *
FROM fused
ORDER BY rrf_score DESC, result_type, result_id
LIMIT %(limit)s;
"""
