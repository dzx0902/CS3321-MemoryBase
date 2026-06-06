from __future__ import annotations

import json
from pathlib import Path

import tiktoken

FACT = "Remember this durable project code: Aurora."
QUERY = "What is the durable project code?"
FILLER = (
    "The team discussed routine implementation details, reviewed unrelated modules, "
    "and recorded ordinary progress notes that do not change the durable project code. "
)


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
    filler_tokens = encoding.encode(FILLER)
    remaining = max(target_tokens - len(fact_tokens), 0)
    filler = FILLER * (remaining // len(filler_tokens))
    padding = " x"
    padding_tokens = encoding.encode(padding)
    if len(padding_tokens) != 1:
        raise ValueError(f"tokenizer {encoding_name!r} does not encode padding as one token")
    while len(encoding.encode(filler)) < remaining:
        filler += padding
    while len(encoding.encode(filler)) > remaining:
        filler = filler[: -len(padding)]
    actual_tokens = len(fact_tokens) + len(encoding.encode(filler))
    return {
        "case_id": f"long_context_{target_tokens}",
        "source": "synthetic_long_context",
        "category": "long_context_retention",
        "sessions": [
            {
                "session_id": "s1",
                "turns": [{"role": "user", "content": FACT}],
            },
            {
                "session_id": "s50",
                "turns": [{"role": "user", "content": filler}],
            },
            {
                "session_id": "s100",
                "turns": [{"role": "user", "content": QUERY}],
            },
        ],
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
            "tokenizer": encoding_name,
        },
        "notes": "Generated long-context retention case with measured filler tokens.",
    }
