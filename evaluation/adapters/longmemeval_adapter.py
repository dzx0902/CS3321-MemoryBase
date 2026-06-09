from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from .common import (
    case_id,
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
    seen_case_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        resolved_case_id = case_id(record, source="longmemeval", index=index)
        if resolved_case_id in seen_case_ids:
            raise ValueError(
                f"duplicate LongMemEval case id {resolved_case_id}; "
                "convert one dataset variant at a time"
            )
        seen_case_ids.add(resolved_case_id)
        sessions = _normalize_longmemeval_sessions(record)
        question = normalize_query(record)
        question_date = _optional_text(record.get("question_date"))
        answer_session_ids = _string_list(record.get("answer_session_ids"))
        metadata = metadata_without_heavy_fields(record)
        metadata.update(
            {
                "answer_session_ids": answer_session_ids,
                "question_date": question_date,
                "haystack_session_count": len(sessions),
                "longmemeval_format": "official-v1",
            }
        )
        cases.append(
            {
                "case_id": resolved_case_id,
                "source": "longmemeval",
                "category": _category(record),
                "sessions": sessions,
                "query": _with_date(question, question_date, label="Question date"),
                "expected_answer": normalize_expected_answer(record),
                "expected_answer_contains": [],
                "forbidden_answers": [],
                "forbidden_patterns": [],
                "gold_memory_ids": [],
                "expected_behavior": _expected_behavior(record),
                "metadata": metadata,
            }
        )
    return write_cases(processed_dir, "longmemeval_cases.jsonl", cases)


def _normalize_longmemeval_sessions(record: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sessions = record.get("haystack_sessions")
    if not _is_official_session_list(raw_sessions):
        return normalize_sessions(
            raw_sessions
            or record.get("sessions")
            or record.get("conversation")
            or record.get("messages")
        )

    session_count = len(raw_sessions)
    session_ids = _parallel_values(
        record,
        "haystack_session_ids",
        expected_length=session_count,
        fallback=lambda index: f"s{index + 1}",
    )
    session_dates = _parallel_values(
        record,
        "haystack_dates",
        expected_length=session_count,
        fallback=lambda _index: "",
    )
    sessions: list[dict[str, Any]] = []
    for index, turns_raw in enumerate(raw_sessions):
        normalized = normalize_sessions(turns_raw)
        turns = normalized[0]["turns"] if normalized else []
        session_date = session_dates[index]
        for turn in turns:
            metadata = turn.setdefault("metadata", {})
            metadata["longmemeval_session_id"] = session_ids[index]
            if session_date:
                metadata["session_date"] = session_date
                turn["content"] = _with_date(
                    str(turn["content"]),
                    session_date,
                    label="Session date",
                )
        sessions.append({"session_id": session_ids[index], "turns": turns})
    return sessions


def _is_official_session_list(raw: object) -> bool:
    return isinstance(raw, list) and all(isinstance(session, list) for session in raw)


def _parallel_values(
    record: dict[str, Any],
    key: str,
    *,
    expected_length: int,
    fallback: Callable[[int], object],
) -> list[str]:
    raw = record.get(key)
    if raw is None:
        return [str(fallback(index)) for index in range(expected_length)]
    if not isinstance(raw, list) or len(raw) != expected_length:
        raise ValueError(
            f"LongMemEval {key} must contain {expected_length} values " "to match haystack_sessions"
        )
    return [str(value) for value in raw]


def _category(record: dict[str, Any]) -> str:
    question_id = str(record.get("question_id") or record.get("id") or "").lower()
    if question_id.endswith("_abs"):
        return "abstention"
    question_type = _normalized_question_type(record)
    mapping = {
        "single_session_user": "single_fact",
        "single_session_assistant": "single_fact",
        "single_session_preference": "preference_following",
        "knowledge_update": "temporal_update",
    }
    return mapping.get(question_type, question_type or "multi_session")


def _expected_behavior(record: dict[str, Any]) -> str:
    question_id = str(record.get("question_id") or record.get("id") or "").lower()
    if question_id.endswith("_abs"):
        return "refuse_or_unknown"
    question_type = _normalized_question_type(record)
    if question_type == "knowledge_update":
        return "answer_latest"
    if question_type == "single_session_preference":
        return "follow_preference"
    return "answer"


def _normalized_question_type(record: dict[str, Any]) -> str:
    value = str(record.get("question_type") or record.get("category") or "")
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_text(value: object) -> str:
    return str(value) if value is not None else ""


def _with_date(text: str, date: str, *, label: str) -> str:
    if not date:
        return text
    return f"[{label}: {date}] {text}"
