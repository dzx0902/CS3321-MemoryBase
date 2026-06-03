from __future__ import annotations

from pathlib import Path

from .common import (
    case_id,
    category,
    load_raw_records,
    metadata_without_heavy_fields,
    normalize_expected_answer,
    normalize_query,
    normalize_sessions,
    write_cases,
)


def convert(raw_dir: Path, processed_dir: Path) -> Path:
    records = load_raw_records(raw_dir)
    cases: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        sessions = normalize_sessions(
            record.get("haystack_sessions")
            or record.get("sessions")
            or record.get("conversation")
            or record.get("messages")
        )
        cases.append(
            {
                "case_id": case_id(record, source="longmemeval", index=index),
                "source": "longmemeval",
                "category": category(record),
                "sessions": sessions,
                "query": normalize_query(record),
                "expected_answer": normalize_expected_answer(record),
                "expected_answer_contains": [],
                "forbidden_answers": [],
                "forbidden_patterns": [],
                "gold_memory_ids": [],
                "expected_behavior": "answer",
                "metadata": metadata_without_heavy_fields(record),
            }
        )
    return write_cases(processed_dir, "longmemeval_cases.jsonl", cases)
