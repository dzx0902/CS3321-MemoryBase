from __future__ import annotations

from app.services.tokenizer import build_search_text


def test_build_search_text_segments_chinese_for_postgres_simple_fts() -> None:
    search_text = build_search_text("为什么放弃校园食堂方向")

    assert "校园" in search_text.split()
    assert "食堂" in search_text.split()
    assert "方向" in search_text.split()


def test_build_search_text_preserves_english_terms_for_demo_recall() -> None:
    search_text = build_search_text("MemoryBase can trace cafeteria decisions.")

    lowered_terms = {term.lower() for term in search_text.split()}
    assert {"memorybase", "cafeteria", "decisions"}.issubset(lowered_terms)
