from app.services._search_query import build_websearch_query


def test_recall_websearch_query_uses_or_semantics_for_agent_queries() -> None:
    assert build_websearch_query("JSON pipeline exit code") == (
        "JSON OR pipeline OR exit OR code"
    )
