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
        cases.append(
            {
                "case_id": case_id(record, source="memoryagentbench", index=index),
                "source": "memoryagentbench",
                "category": category(record),
                "sessions": normalize_sessions(
                    record.get("interactions")
                    or record.get("sessions")
                    or record.get("conversation")
                    or record.get("messages")
                ),
                "query": normalize_query(record),
                "expected_answer": normalize_expected_answer(record),
                "expected_answer_contains": [],
                "forbidden_answers": [],
                "forbidden_patterns": [],
                "gold_memory_ids": [],
                "expected_behavior": _expected_behavior(record),
                "metadata": metadata_without_heavy_fields(record),
            }
        )
    return write_cases(processed_dir, "memoryagentbench_cases.jsonl", cases)


def _expected_behavior(record: dict[str, object]) -> str:
    task_type = str(record.get("task_type") or record.get("category") or "").lower()
    if "conflict" in task_type:
        return "answer_latest"
    if "preference" in task_type:
        return "follow_preference"
    return "answer"
