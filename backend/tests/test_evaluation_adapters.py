from __future__ import annotations

import json
from pathlib import Path

from evaluation.adapters import locomo_adapter, longmemeval_adapter, memoryagentbench_adapter


def test_longmemeval_adapter_converts_jsonl(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "sample.jsonl").write_text(
        json.dumps(
            {
                "question_id": "q1",
                "question": "Where does the user live now?",
                "answer": "Beijing",
                "question_type": "knowledge_update",
                "haystack_sessions": [
                    {
                        "session_id": "s1",
                        "messages": [{"role": "user", "content": "I live in Shanghai."}],
                    },
                    {
                        "session_id": "s2",
                        "messages": [{"role": "user", "content": "I moved to Beijing."}],
                    },
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    output = longmemeval_adapter.convert(raw_dir, processed_dir)

    row = json.loads(output.read_text(encoding="utf-8").strip())
    assert row["case_id"] == "longmemeval_q1"
    assert row["category"] == "temporal_update"
    assert row["expected_answer"] == "Beijing"
    assert len(row["sessions"]) == 2


def test_locomo_adapter_expands_qa_items(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "sample.json").write_text(
        json.dumps(
            {
                "id": "dialogue1",
                "conversation": [{"role": "user", "content": "My favorite language is Rust."}],
                "qa": [
                    {"id": "qa1", "question": "What language?", "answer": "Rust"},
                    {"id": "qa2", "question": "Who said that?", "answer": "user"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output = locomo_adapter.convert(raw_dir, processed_dir)

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert [row["query"] for row in rows] == ["What language?", "Who said that?"]
    assert all(row["source"] == "locomo" for row in rows)


def test_memoryagentbench_adapter_marks_conflict_behavior(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "sample.json").write_text(
        json.dumps(
            [
                {
                    "sample_id": "m1",
                    "task_type": "conflict_resolution",
                    "query": "Where does the user live?",
                    "target": "Beijing",
                    "interactions": [
                        {"role": "user", "content": "I live in Shanghai."},
                        {"role": "user", "content": "I moved to Beijing."},
                    ],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output = memoryagentbench_adapter.convert(raw_dir, processed_dir)

    row = json.loads(output.read_text(encoding="utf-8").strip())
    assert row["case_id"] == "memoryagentbench_m1"
    assert row["expected_behavior"] == "answer_latest"
    assert row["expected_answer"] == "Beijing"
