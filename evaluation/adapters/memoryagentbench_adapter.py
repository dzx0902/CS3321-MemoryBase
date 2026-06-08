from __future__ import annotations

import re
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

# Context packs retain at most 600 characters per selected memory. Keep benchmark
# facts below that boundary so retrieval does not silently discard the answer.
CONTEXT_CHUNK_CHARS = 500


def convert(raw_dir: Path, processed_dir: Path) -> Path:
    records = load_raw_records(raw_dir)
    cases: list[dict[str, object]] = []
    for index, record in enumerate(records, start=1):
        if _is_conflict_resolution_record(record):
            cases.extend(_conflict_resolution_cases(record, index))
            continue
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


def _is_conflict_resolution_record(record: dict[str, object]) -> bool:
    metadata = record.get("metadata")
    return (
        isinstance(record.get("context"), str)
        and isinstance(record.get("questions"), list)
        and isinstance(record.get("answers"), list)
        and isinstance(metadata, dict)
        and str(metadata.get("source") or "").startswith("factconsolidation_")
    )


def _conflict_resolution_cases(
    record: dict[str, object],
    row_index: int,
) -> list[dict[str, object]]:
    context = str(record["context"])
    questions = record["questions"]
    answers = record["answers"]
    metadata = record["metadata"]
    if not isinstance(questions, list) or not isinstance(answers, list):
        return []
    if len(questions) != len(answers):
        raise ValueError("MemoryAgentBench Conflict Resolution questions and answers must align")
    if not isinstance(metadata, dict):
        raise ValueError("MemoryAgentBench Conflict Resolution metadata must be an object")
    source = str(metadata.get("source") or f"conflict_row_{row_index}")
    qa_pair_ids = metadata.get("qa_pair_ids")
    if not isinstance(qa_pair_ids, list) or len(qa_pair_ids) != len(questions):
        raise ValueError(
            "MemoryAgentBench Conflict Resolution qa_pair_ids must align with questions"
        )
    sessions = _context_sessions(context)
    cases: list[dict[str, object]] = []
    for qa_index, (question, raw_answers, qa_pair_id) in enumerate(
        zip(questions, answers, qa_pair_ids, strict=True),
        start=1,
    ):
        accepted_answers = _accepted_answers(raw_answers)
        cases.append(
            {
                "case_id": f"memoryagentbench_{qa_pair_id}",
                "source": "memoryagentbench",
                "category": _conflict_category(source),
                "sessions": sessions,
                "query": str(question),
                "expected_answer": accepted_answers[0] if accepted_answers else None,
                "expected_answer_contains": [],
                "forbidden_answers": [],
                "forbidden_patterns": [],
                "gold_memory_ids": [],
                "expected_behavior": "answer_latest",
                "metadata": {
                    "context_group_id": source,
                    "context_chars": len(context),
                    "context_chunk_count": len(sessions),
                    "qa_index": qa_index,
                    "qa_pair_id": str(qa_pair_id),
                    "accepted_answers": accepted_answers,
                    "memoryagentbench_competency": "conflict_resolution",
                    "memoryagentbench_format": "official-v1",
                    "source_subset": source,
                },
            }
        )
    return cases


def _context_sessions(context: str) -> list[dict[str, object]]:
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0
    for line in lines:
        added_chars = len(line) + (1 if current else 0)
        if current and current_chars + added_chars > CONTEXT_CHUNK_CHARS:
            chunks.append("\n".join(current))
            current = []
            current_chars = 0
        current.append(line)
        current_chars += len(line) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append("\n".join(current))
    return [
        {
            "session_id": f"context_{index:04d}",
            "turns": [
                {
                    "role": "user",
                    "content": (
                        f"[Memory sequence {index:04d}] Higher sequence numbers are "
                        "later and supersede earlier conflicting facts.\n"
                        f"{chunk}"
                    ),
                    "metadata": {"context_chunk": index},
                }
            ],
        }
        for index, chunk in enumerate(chunks, start=1)
    ]


def _accepted_answers(raw_answers: object) -> list[str]:
    if isinstance(raw_answers, list):
        return [str(answer) for answer in raw_answers if str(answer)]
    if raw_answers is None:
        return []
    return [str(raw_answers)]


def _conflict_category(source: str) -> str:
    reasoning = "multi_hop" if "_mh_" in source else "single_hop"
    match = re.search(r"_(6k|32k|64k|262k)$", source)
    length = match.group(1) if match else "unknown"
    return f"conflict_{reasoning}_{length}"


def _expected_behavior(record: dict[str, object]) -> str:
    task_type = str(record.get("task_type") or record.get("category") or "").lower()
    if "conflict" in task_type:
        return "answer_latest"
    if "preference" in task_type:
        return "follow_preference"
    return "answer"
