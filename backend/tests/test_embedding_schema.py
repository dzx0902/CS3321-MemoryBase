from __future__ import annotations

from pathlib import Path


def test_embedding_tables_are_declared_in_schema() -> None:
    schema = Path("database/02_schema_memory.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS memory_embedding" in schema
    assert "CREATE TABLE IF NOT EXISTS source_chunk_embedding" in schema
    assert "embedding_json JSONB NOT NULL" in schema


def test_embedding_indexes_are_declared() -> None:
    indexes = Path("database/04_indexes.sql").read_text(encoding="utf-8")

    assert "idx_memory_embedding_workspace_model" in indexes
    assert "idx_source_chunk_embedding_workspace_model" in indexes
