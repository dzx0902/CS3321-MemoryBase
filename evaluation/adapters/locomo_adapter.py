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
        qa_items = record.get("qa") or record.get("qas") or record.get("questions")
        conversation = (
            record.get("conversation")
            or record.get("conversations")
            or record.get("sessions")
            or record.get("messages")
        )
        if isinstance(qa_items, list):
            for qa_index, qa in enumerate(qa_items, start=1):
                if not isinstance(qa, dict):
                    continue
                merged = {**record, **qa}
                cases.append(_case_from_record(merged, conversation, index, qa_index))
        else:
            cases.append(_case_from_record(record, conversation, index, None))
    return write_cases(processed_dir, "locomo_cases.jsonl", cases)


def _case_from_record(
    record: dict[str, object],
    conversation: object,
    index: int,
    qa_index: int | None,
) -> dict[str, object]:
    base_id = case_id(record, source="locomo", index=index)
    if qa_index is not None:
        base_id = f"{base_id}_qa{qa_index:03d}"
    return {
        "case_id": base_id,
        "source": "locomo",
        "category": category(record),
        "sessions": normalize_sessions(conversation),
        "query": normalize_query(record),
        "expected_answer": normalize_expected_answer(record),
        "expected_answer_contains": [],
        "forbidden_answers": [],
        "forbidden_patterns": [],
        "gold_memory_ids": [],
        "expected_behavior": "answer",
        "metadata": metadata_without_heavy_fields(record),
    }
