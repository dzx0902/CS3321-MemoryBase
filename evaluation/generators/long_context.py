from __future__ import annotations

import json
from pathlib import Path

import tiktoken

FACT = "Remember this durable project code: Aurora."
QUERY = "What is the durable project code?"
FILLER = (
    "The team reviewed routine implementation details, unrelated modules, meeting notes, "
    "test fixtures, documentation edits, and ordinary progress updates. "
)
DEFAULT_FILLER_CHUNK_TOKENS = 1000


def generate_long_context_cases(
    output: Path,
    *,
    token_lengths: list[int],
    encoding_name: str = "cl100k_base",
) -> Path:
    encoding = tiktoken.get_encoding(encoding_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        _build_case(target_tokens, encoding=encoding, encoding_name=encoding_name)
        for target_tokens in token_lengths
    ]
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return output


def _build_case(target_tokens: int, *, encoding, encoding_name: str) -> dict[str, object]:
    if target_tokens < 128:
        raise ValueError("long-context token lengths must be at least 128")
    fact_tokens = encoding.encode(FACT)
    remaining = max(target_tokens - len(fact_tokens), 0)
    filler_chunks: list[str] = []
    while remaining:
        chunk_tokens = min(remaining, DEFAULT_FILLER_CHUNK_TOKENS)
        filler_chunks.append(
            _filler_with_exact_tokens(
                chunk_tokens,
                encoding=encoding,
                encoding_name=encoding_name,
            )
        )
        remaining -= chunk_tokens
    actual_tokens = len(fact_tokens) + sum(len(encoding.encode(chunk)) for chunk in filler_chunks)
    sessions = [
        {
            "session_id": "s0000",
            "turns": [{"role": "user", "content": FACT}],
        }
    ]
    sessions.extend(
        {
            "session_id": f"s{index:04d}",
            "turns": [{"role": "user", "content": chunk}],
        }
        for index, chunk in enumerate(filler_chunks, start=1)
    )
    sessions.append(
        {
            "session_id": f"s{len(filler_chunks) + 1:04d}",
            "turns": [{"role": "user", "content": QUERY}],
        }
    )
    return {
        "case_id": f"long_context_{target_tokens}",
        "source": "synthetic_long_context",
        "category": "long_context_retention",
        "sessions": sessions,
        "query": QUERY,
        "expected_answer": "Aurora",
        "expected_answer_contains": ["Aurora"],
        "forbidden_answers": [],
        "forbidden_patterns": [],
        "gold_memory_ids": [],
        "expected_behavior": "answer",
        "metadata": {
            "history_length_tokens": target_tokens,
            "actual_history_tokens": actual_tokens,
            "memory_turn_count": len(filler_chunks) + 1,
            "filler_chunk_tokens": DEFAULT_FILLER_CHUNK_TOKENS,
            "tokenizer": encoding_name,
        },
        "notes": "Generated long-context retention case with measured filler tokens.",
    }


def _filler_with_exact_tokens(
    target_tokens: int,
    *,
    encoding,
    encoding_name: str,
) -> str:
    filler_tokens = encoding.encode(FILLER)
    filler = FILLER * (target_tokens // len(filler_tokens))
    padding = " x"
    padding_tokens = encoding.encode(padding)
    if len(padding_tokens) != 1:
        raise ValueError(f"tokenizer {encoding_name!r} does not encode padding as one token")
    while len(encoding.encode(filler)) < target_tokens:
        filler += padding
    while len(encoding.encode(filler)) > target_tokens:
        filler = filler[: -len(padding)]
    return filler
