from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def load_raw_records(raw_dir: Path) -> list[dict[str, Any]]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"raw benchmark directory does not exist: {raw_dir}")
    records: list[dict[str, Any]] = []
    for path in sorted(raw_dir.iterdir()):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() == ".jsonl":
            records.extend(_load_jsonl(path))
        elif path.suffix.lower() == ".json":
            records.extend(_load_json(path))
    if not records:
        raise FileNotFoundError(f"no .json or .jsonl benchmark files found in {raw_dir}")
    return records


def write_cases(processed_dir: Path, filename: str, cases: Iterable[dict[str, Any]]) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / filename
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return output_path


def normalize_sessions(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        if "sessions" in raw:
            return normalize_sessions(raw["sessions"])
        if "messages" in raw or "turns" in raw:
            return [_normalize_session(raw, fallback_id="s1")]
        sessions: list[dict[str, Any]] = []
        for key, value in raw.items():
            if isinstance(value, (list, dict)):
                sessions.extend(normalize_sessions(value))
            elif isinstance(value, str):
                sessions.append(_text_session(str(key), value))
        return sessions
    if isinstance(raw, list):
        if not raw:
            return []
        if all(isinstance(item, dict) and ("turns" in item or "messages" in item) for item in raw):
            return [
                _normalize_session(item, fallback_id=f"s{index}")
                for index, item in enumerate(raw, 1)
            ]
        if all(isinstance(item, dict) and ("role" in item or "speaker" in item) for item in raw):
            return [_normalize_session({"session_id": "s1", "turns": raw}, fallback_id="s1")]
        sessions: list[dict[str, Any]] = []
        for index, item in enumerate(raw, start=1):
            if isinstance(item, str):
                sessions.append(_text_session(f"s{index}", item))
            elif isinstance(item, dict):
                sessions.extend(normalize_sessions(item))
        return sessions
    if isinstance(raw, str):
        return [_text_session("s1", raw)]
    return []


def normalize_expected_answer(raw: dict[str, Any]) -> str | None:
    for key in ("answer", "expected_answer", "target", "gold_answer", "reference_answer"):
        value = raw.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list) and value:
            return ", ".join(str(item) for item in value)
    return None


def normalize_query(raw: dict[str, Any]) -> str:
    for key in ("question", "query", "prompt", "input"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("external benchmark record requires a question/query field")


def case_id(raw: dict[str, Any], *, source: str, index: int) -> str:
    for key in ("case_id", "question_id", "id", "qid", "sample_id"):
        value = raw.get(key)
        if value is not None and str(value).strip():
            return f"{source}_{str(value).strip()}"
    return f"{source}_{index:06d}"


def category(raw: dict[str, Any], default: str = "multi_session") -> str:
    for key in ("category", "question_type", "type", "task_type"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_category(value)
    return default


def metadata_without_heavy_fields(raw: dict[str, Any]) -> dict[str, Any]:
    heavy = {
        "sessions",
        "haystack_sessions",
        "conversation",
        "conversations",
        "messages",
        "turns",
        "qa",
        "qas",
    }
    metadata: dict[str, Any] = {}
    for key, value in raw.items():
        if key in heavy:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            metadata[key] = value
        elif isinstance(value, list) and len(value) <= 20:
            metadata[key] = value
    return metadata


def _load_json(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("data", "examples", "items", "questions"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [raw]
    return []


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            if not isinstance(raw, dict):
                raise ValueError(f"{path}:{line_no}: JSONL row must be an object")
            records.append(raw)
    return records


def _normalize_session(raw: dict[str, Any], *, fallback_id: str) -> dict[str, Any]:
    session_id = str(raw.get("session_id") or raw.get("id") or fallback_id)
    turns_raw = raw.get("turns") or raw.get("messages") or []
    turns = [_normalize_turn(turn) for turn in turns_raw if isinstance(turn, dict)]
    return {"session_id": session_id, "turns": turns}


def _normalize_turn(raw: dict[str, Any]) -> dict[str, Any]:
    role = str(raw.get("role") or raw.get("speaker") or raw.get("sender") or "user").lower()
    if role in {"human", "person", "speaker1", "speaker_1"}:
        role = "user"
    elif role in {"ai", "bot", "assistant", "speaker2", "speaker_2"}:
        role = "assistant"
    elif role not in {"user", "assistant", "system", "tool"}:
        role = "user"
    content = raw.get("content") or raw.get("text") or raw.get("message") or raw.get("utterance")
    return {
        "role": role,
        "content": str(content or ""),
        "metadata": metadata_without_heavy_fields(raw),
    }


def _text_session(session_id: str, text: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "turns": [{"role": "user", "content": text, "metadata": {}}],
    }


def _normalize_category(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "knowledge_update": "temporal_update",
        "temporal_reasoning": "temporal_update",
        "single_session_preference": "preference",
        "preference_following": "preference",
        "conflict_resolution": "conflict",
    }
    return mapping.get(normalized, normalized)
