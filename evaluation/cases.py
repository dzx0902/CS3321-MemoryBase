from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class EvaluationCaseError(ValueError):
    pass


@dataclass(slots=True)
class EvaluationTurn:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationSession:
    session_id: str
    turns: list[EvaluationTurn]


@dataclass(slots=True)
class EvaluationCase:
    case_id: str
    source: str
    category: str
    sessions: list[EvaluationSession]
    query: str
    expected_answer: str | None = None
    expected_answer_contains: list[str] = field(default_factory=list)
    forbidden_answers: list[str] = field(default_factory=list)
    forbidden_patterns: list[str] = field(default_factory=list)
    gold_memory_ids: list[str] = field(default_factory=list)
    expected_behavior: str = "answer"
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None


def load_cases(
    path: Path,
    *,
    category: str | None = None,
    limit: int | None = None,
) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise EvaluationCaseError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
            case = parse_case(raw, path=path, line_no=line_no)
            if category and case.category != category:
                continue
            cases.append(case)
            if limit is not None and len(cases) >= limit:
                break
    return cases


def parse_case(raw: Any, *, path: Path | None = None, line_no: int | None = None) -> EvaluationCase:
    if not isinstance(raw, dict):
        raise _case_error("case must be an object", path, line_no)
    case_id = _required_str(raw, "case_id", path, line_no)
    category = _required_str(raw, "category", path, line_no, case_id)
    query = _required_str(raw, "query", path, line_no, case_id)
    sessions_raw = raw.get("sessions", [])
    if not isinstance(sessions_raw, list):
        raise _case_error("sessions must be a list", path, line_no, case_id)

    sessions = [_parse_session(item, path, line_no, case_id) for item in sessions_raw]
    return EvaluationCase(
        case_id=case_id,
        source=str(raw.get("source") or "synthetic"),
        category=category,
        sessions=sessions,
        query=query,
        expected_answer=_optional_str(
            raw.get("expected_answer"),
            "expected_answer",
            path,
            line_no,
            case_id,
        ),
        expected_answer_contains=_str_list(
            raw.get("expected_answer_contains", []),
            "expected_answer_contains",
            path,
            line_no,
            case_id,
        ),
        forbidden_answers=_str_list(
            raw.get("forbidden_answers", []),
            "forbidden_answers",
            path,
            line_no,
            case_id,
        ),
        forbidden_patterns=_str_list(
            raw.get("forbidden_patterns", []),
            "forbidden_patterns",
            path,
            line_no,
            case_id,
        ),
        gold_memory_ids=_str_list(
            raw.get("gold_memory_ids", []),
            "gold_memory_ids",
            path,
            line_no,
            case_id,
        ),
        expected_behavior=str(raw.get("expected_behavior") or "answer"),
        metadata=_dict(raw.get("metadata", {}), "metadata", path, line_no, case_id),
        notes=_optional_str(raw.get("notes"), "notes", path, line_no, case_id),
    )


def case_to_dict(case: EvaluationCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "source": case.source,
        "category": case.category,
        "sessions": [
            {
                "session_id": session.session_id,
                "turns": [
                    {
                        "role": turn.role,
                        "content": turn.content,
                        "metadata": turn.metadata,
                    }
                    for turn in session.turns
                ],
            }
            for session in case.sessions
        ],
        "query": case.query,
        "expected_answer": case.expected_answer,
        "expected_answer_contains": case.expected_answer_contains,
        "forbidden_answers": case.forbidden_answers,
        "forbidden_patterns": case.forbidden_patterns,
        "gold_memory_ids": case.gold_memory_ids,
        "expected_behavior": case.expected_behavior,
        "metadata": case.metadata,
        "notes": case.notes,
    }


def _parse_session(
    raw: Any,
    path: Path | None,
    line_no: int | None,
    case_id: str,
) -> EvaluationSession:
    if not isinstance(raw, dict):
        raise _case_error("session must be an object", path, line_no, case_id)
    session_id = _required_str(raw, "session_id", path, line_no, case_id)
    turns_raw = raw.get("turns", [])
    if not isinstance(turns_raw, list):
        raise _case_error("turns must be a list", path, line_no, case_id)
    turns: list[EvaluationTurn] = []
    for turn_raw in turns_raw:
        if not isinstance(turn_raw, dict):
            raise _case_error("turn must be an object", path, line_no, case_id)
        turns.append(
            EvaluationTurn(
                role=_required_str(turn_raw, "role", path, line_no, case_id),
                content=_required_str(turn_raw, "content", path, line_no, case_id),
                metadata=_dict(turn_raw.get("metadata", {}), "metadata", path, line_no, case_id),
            )
        )
    return EvaluationSession(session_id=session_id, turns=turns)


def _required_str(
    raw: dict[str, Any],
    key: str,
    path: Path | None,
    line_no: int | None,
    case_id: str | None = None,
) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _case_error(f"{key} must be a non-empty string", path, line_no, case_id)
    return value.strip()


def _optional_str(
    value: Any,
    key: str,
    path: Path | None,
    line_no: int | None,
    case_id: str | None,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _case_error(f"{key} must be a string or null", path, line_no, case_id)
    return value


def _str_list(
    value: Any,
    key: str,
    path: Path | None,
    line_no: int | None,
    case_id: str | None,
) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _case_error(f"{key} must be a list of strings", path, line_no, case_id)
    return list(value)


def _dict(
    value: Any,
    key: str,
    path: Path | None,
    line_no: int | None,
    case_id: str | None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _case_error(f"{key} must be an object", path, line_no, case_id)
    return value


def _case_error(
    message: str,
    path: Path | None,
    line_no: int | None,
    case_id: str | None = None,
) -> EvaluationCaseError:
    location = ""
    if path is not None and line_no is not None:
        location = f"{path}:{line_no}: "
    case_label = f"case {case_id}: " if case_id else ""
    return EvaluationCaseError(f"{location}{case_label}{message}")
