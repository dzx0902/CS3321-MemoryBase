from __future__ import annotations

import re
from pathlib import Path

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
    for index, record in enumerate(records, start=1):
        if _is_official_locomo_record(record):
            cases.extend(_official_cases(record, index))
            continue
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
        "category": _category(record),
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


def _is_official_locomo_record(record: dict[str, object]) -> bool:
    conversation = record.get("conversation")
    return (
        isinstance(conversation, dict)
        and isinstance(record.get("qa"), list)
        and any(re.fullmatch(r"session_\d+", key) for key in conversation)
    )


def _official_cases(record: dict[str, object], index: int) -> list[dict[str, object]]:
    sessions, dialog_index = _official_sessions(record)
    sample_id = str(record.get("sample_id") or f"{index:06d}")
    cases: list[dict[str, object]] = []
    qa_items = record.get("qa")
    if not isinstance(qa_items, list):
        return cases
    for qa_index, qa in enumerate(qa_items, start=1):
        if not isinstance(qa, dict):
            continue
        evidence_ids = _evidence_ids(qa.get("evidence"))
        cases.append(
            {
                "case_id": f"locomo_{sample_id}_qa{qa_index:03d}",
                "source": "locomo",
                "category": _category(qa),
                "sessions": sessions,
                "query": normalize_query(qa),
                "expected_answer": normalize_expected_answer(qa),
                "expected_answer_contains": [],
                "forbidden_answers": _forbidden_answers(qa),
                "forbidden_patterns": [],
                "gold_memory_ids": evidence_ids,
                "expected_behavior": _expected_behavior(qa),
                "metadata": {
                    **metadata_without_heavy_fields(qa),
                    "sample_id": sample_id,
                    "qa_index": qa_index,
                    "evidence": evidence_ids,
                    "missing_evidence": [
                        evidence_id
                        for evidence_id in evidence_ids
                        if evidence_id not in dialog_index
                    ],
                    "locomo_format": "official-v1",
                },
            }
        )
    return cases


def _official_sessions(
    record: dict[str, object],
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    conversation = record["conversation"]
    if not isinstance(conversation, dict):
        return [], {}
    speaker_a = str(conversation.get("speaker_a") or "speaker_a")
    speaker_b = str(conversation.get("speaker_b") or "speaker_b")
    dialog_index: dict[str, dict[str, object]] = {}
    sessions: list[dict[str, object]] = []
    for session_key in sorted(
        (key for key in conversation if re.fullmatch(r"session_\d+", key)),
        key=lambda value: int(value.split("_")[1]),
    ):
        raw_turns = conversation.get(session_key)
        if not isinstance(raw_turns, list):
            continue
        session_date = str(conversation.get(f"{session_key}_date_time") or "")
        turns: list[dict[str, object]] = []
        for raw_turn in raw_turns:
            if not isinstance(raw_turn, dict):
                continue
            speaker = str(raw_turn.get("speaker") or "")
            dia_id = str(raw_turn.get("dia_id") or "")
            metadata = metadata_without_heavy_fields(raw_turn)
            metadata.update(
                {
                    "dia_id": dia_id,
                    "speaker": speaker,
                    "session_date": session_date,
                    "speaker_a": speaker_a,
                    "speaker_b": speaker_b,
                }
            )
            if raw_turn.get("img_url"):
                metadata["img_url"] = raw_turn.get("img_url")
            if raw_turn.get("blip_caption"):
                metadata["blip_caption"] = raw_turn.get("blip_caption")
            content = _turn_content(raw_turn, session_date=session_date)
            turn = {
                "role": _role_for_speaker(speaker, speaker_a=speaker_a),
                "content": content,
                "metadata": metadata,
            }
            turns.append(turn)
            if dia_id:
                dialog_index[dia_id] = turn
        sessions.append({"session_id": session_key, "turns": turns})
    return sessions, dialog_index


def _turn_content(raw_turn: dict[str, object], *, session_date: str) -> str:
    parts: list[str] = []
    if session_date:
        parts.append(f"[Session date: {session_date}]")
    speaker = str(raw_turn.get("speaker") or "").strip()
    text = str(raw_turn.get("text") or "").strip()
    if speaker:
        text = f"{speaker}: {text}"
    parts.append(text)
    caption = str(raw_turn.get("blip_caption") or "").strip()
    if caption:
        parts.append(f"[Image caption: {caption}]")
    return " ".join(part for part in parts if part)


def _role_for_speaker(speaker: str, *, speaker_a: str) -> str:
    return "user" if speaker == speaker_a else "assistant"


def _category(record: dict[str, object]) -> str:
    raw = record.get("category") or record.get("question_type") or record.get("type")
    if isinstance(raw, int):
        return {
            1: "single_hop",
            2: "multi_hop",
            3: "temporal_reasoning",
            4: "open_domain",
            5: "adversarial",
        }.get(raw, f"category_{raw}")
    if isinstance(raw, str) and raw.strip():
        normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
        return {
            "single_hop": "single_hop",
            "temporal": "temporal_reasoning",
            "temporal_reasoning": "temporal_reasoning",
            "multi_hop": "multi_hop",
            "adversarial": "adversarial",
        }.get(normalized, normalized)
    return "multi_session"


def _expected_behavior(record: dict[str, object]) -> str:
    if _category(record) == "adversarial" and normalize_expected_answer(record) is None:
        return "refuse_or_unknown"
    return "answer"


def _forbidden_answers(record: dict[str, object]) -> list[str]:
    value = record.get("adversarial_answer")
    return [str(value)] if value is not None else []


def _evidence_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    evidence_ids: list[str] = []
    for item in value:
        for session_no, turn_no in re.findall(r"D:?(\d+):(\d+)", str(item)):
            evidence_ids.append(f"D{int(session_no)}:{int(turn_no)}")
    return evidence_ids
