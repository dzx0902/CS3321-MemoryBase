from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.recall import RecallRequest, RetrievalInfo
from app.services._search_query import build_websearch_query
from app.services.recall_service import (
    HYBRID_FALLBACK_REASON,
    LocalHashingEmbeddingProvider,
    PostgresRecallRepository,
    _embedding_json_to_vector,
    _rank_reason,
    _recency_score,
    _text_keyword_score,
)


def test_recall_websearch_query_uses_or_semantics_for_agent_queries() -> None:
    assert build_websearch_query("JSON pipeline exit code") == ("JSON OR pipeline OR exit OR code")


def test_recall_vector_helpers_parse_and_score_rows() -> None:
    assert _embedding_json_to_vector("[1, 0.5, -1]") == [1.0, 0.5, -1.0]
    assert _text_keyword_score(text="MemoryBase uses PostgreSQL.", terms=["postgres"]) == 0.15

    updated_at = datetime.now(timezone.utc) - timedelta(days=1)
    assert _recency_score(updated_at) > 0
    assert _rank_reason(0.15, 0.7, 0.1, 0.2) == (
        "semantic match + keyword match + recent memory + weighted evidence"
    )


def test_recall_request_accepts_explicit_retrieval_modes() -> None:
    payload = {
        "workspace_id": "00000000-0000-0000-0000-000000000201",
        "query_text": "project memory",
    }

    assert RecallRequest(**payload).retrieval_mode == "hybrid"
    assert RecallRequest(**{**payload, "retrieval_mode": "keyword"}).retrieval_mode == "keyword"
    assert RecallRequest(**{**payload, "retrieval_mode": "vector"}).retrieval_mode == "vector"


def test_recall_request_defaults_to_hybrid_mode() -> None:
    payload = RecallRequest(
        workspace_id="00000000-0000-0000-0000-000000000201",
        query_text="memory retrieval",
    )

    assert payload.retrieval_mode == "hybrid"


def test_merge_vector_rows_reports_keyword_fallback_when_no_embedding_rows() -> None:
    class FakeCursor:
        def execute(self, *_args, **_kwargs) -> None:
            return None

        def fetchall(self):
            return []

    repository = PostgresRecallRepository(
        database=object(),
        embedding_provider=LocalHashingEmbeddingProvider(),
        embedding_provider_name="local",
        embedding_model="hashing-v1",
        embedding_dimension=16,
    )
    payload = RecallRequest(
        workspace_id=uuid4(),
        query_text="cafeteria system",
        retrieval_mode="hybrid",
    )
    retrieval_info = RetrievalInfo(
        requested_mode="hybrid",
        effective_mode="hybrid",
        embedding_provider="local",
        embedding_model="hashing-v1",
    )

    rows, info = repository._merge_vector_rows(
        cur=FakeCursor(),
        payload=payload,
        where_clause="mi.workspace_id = %(workspace_id)s",
        params={"workspace_id": payload.workspace_id, "limit": payload.limit},
        keyword_rows=[],
        retrieval_info=retrieval_info,
    )

    assert rows == []
    assert info.effective_mode == "keyword"
    assert info.vector_used is False
    assert info.fallback_reason == HYBRID_FALLBACK_REASON
