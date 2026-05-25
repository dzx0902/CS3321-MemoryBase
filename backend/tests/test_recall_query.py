from datetime import datetime, timedelta, timezone

from app.services._search_query import build_websearch_query
from app.services.recall_service import (
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
