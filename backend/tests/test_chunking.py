from __future__ import annotations

from app.services.chunking import build_chunks


def test_build_chunks_uses_short_lines_as_reviewable_chunks() -> None:
    chunks = build_chunks(
        "\n".join(
            [
                "We decided to abandon the campus cafeteria system because it was too CRUD-heavy.",
                "MemoryBase should use PostgreSQL as the source of truth.",
                "Private budget notes must stay hidden from project-only retriever agents unless explicitly allowed.",
            ]
        )
    )

    assert [chunk.chunk_no for chunk in chunks] == [1, 2, 3]
    assert [chunk.start_line for chunk in chunks] == [1, 2, 3]
    assert [chunk.end_line for chunk in chunks] == [1, 2, 3]
    assert chunks[0].chunk_text.startswith("We decided to abandon")
    assert chunks[1].chunk_text == "MemoryBase should use PostgreSQL as the source of truth."
    assert chunks[2].chunk_text.startswith("Private budget notes")


def test_build_chunks_falls_back_to_size_based_chunks_for_long_lines() -> None:
    chunks = build_chunks("alpha beta gamma delta", max_chars=10, overlap_lines=0)

    assert len(chunks) == 1
    assert chunks[0].chunk_text == "alpha beta gamma delta"
