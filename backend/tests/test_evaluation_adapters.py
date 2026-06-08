from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from evaluation.adapters import locomo_adapter, longmemeval_adapter, memoryagentbench_adapter


def test_longmemeval_adapter_converts_jsonl(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "longmemeval_oracle").write_text(
        json.dumps(
            {
                "question_id": "q1",
                "question": "Where does the user live now?",
                "answer": "Beijing",
                "question_type": "knowledge_update",
                "haystack_sessions": [
                    [
                        {
                            "role": "user",
                            "content": "I live in Shanghai.",
                            "has_answer": False,
                        }
                    ],
                    [
                        {
                            "role": "user",
                            "content": "I moved to Beijing.",
                            "has_answer": True,
                        }
                    ],
                ],
                "haystack_session_ids": ["session-1", "session-2"],
                "haystack_dates": ["2024-01-02", "2024-02-03"],
                "answer_session_ids": ["session-2"],
                "question_date": "2024-03-04",
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
    assert row["expected_behavior"] == "answer_latest"
    assert row["query"].startswith("[Question date: 2024-03-04]")
    assert len(row["sessions"]) == 2
    assert row["sessions"][0]["session_id"] == "session-1"
    assert row["sessions"][1]["turns"][0]["content"].startswith("[Session date: 2024-02-03]")
    assert row["sessions"][1]["turns"][0]["metadata"]["has_answer"] is True
    assert row["metadata"]["answer_session_ids"] == ["session-2"]
    assert row["metadata"]["longmemeval_format"] == "official-v1"


def test_longmemeval_adapter_marks_abstention_and_scalar_answer(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "sample.json").write_text(
        json.dumps(
            [
                {
                    "question_id": "q2_abs",
                    "question": "How many siblings does the user have?",
                    "answer": 2,
                    "question_type": "multi-session",
                    "haystack_sessions": [[{"role": "user", "content": "No sibling facts."}]],
                }
            ]
        ),
        encoding="utf-8",
    )

    output = longmemeval_adapter.convert(raw_dir, processed_dir)

    row = json.loads(output.read_text(encoding="utf-8").strip())
    assert row["category"] == "abstention"
    assert row["expected_behavior"] == "refuse_or_unknown"
    assert row["expected_answer"] == "2"


def test_longmemeval_adapter_rejects_misaligned_session_metadata(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "sample.json").write_text(
        json.dumps(
            [
                {
                    "question_id": "q3",
                    "question": "Where does the user live?",
                    "answer": "Beijing",
                    "haystack_sessions": [
                        [{"role": "user", "content": "I live in Beijing."}],
                        [{"role": "assistant", "content": "Understood."}],
                    ],
                    "haystack_dates": ["2024-01-01"],
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="haystack_dates must contain 2 values"):
        longmemeval_adapter.convert(raw_dir, processed_dir)


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


def test_locomo_adapter_converts_official_sessions_and_adversarial_qa(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "locomo10.json").write_text(
        json.dumps(
            [
                {
                    "sample_id": "conv-1",
                    "conversation": {
                        "speaker_a": "Caroline",
                        "speaker_b": "Melanie",
                        "session_1_date_time": "1:56 pm on 8 May, 2023",
                        "session_1": [
                            {
                                "speaker": "Caroline",
                                "dia_id": "D1:1",
                                "text": "I joined a support group yesterday.",
                            },
                            {
                                "speaker": "Melanie",
                                "dia_id": "D1:2",
                                "text": "That sounds meaningful.",
                                "blip_caption": "a colorful mural",
                            },
                        ],
                    },
                    "qa": [
                        {
                            "question": "When did Caroline join the support group?",
                            "answer": "7 May 2023",
                            "evidence": ["D1:1"],
                            "category": 2,
                        },
                        {
                            "question": "What did Melanie buy?",
                            "evidence": ["D1:01 D:1:2"],
                            "category": 5,
                            "adversarial_answer": "a painting",
                        },
                        {
                            "question": "Did Caroline buy the painting?",
                            "answer": "No",
                            "evidence": ["D1:1"],
                            "category": 5,
                            "adversarial_answer": "Yes",
                        },
                    ],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output = locomo_adapter.convert(raw_dir, processed_dir)

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["case_id"] == "locomo_conv-1_qa001"
    assert rows[0]["category"] == "multi_hop"
    assert rows[0]["gold_memory_ids"] == ["D1:1"]
    assert rows[0]["sessions"][0]["turns"][0]["role"] == "user"
    assert rows[0]["sessions"][0]["turns"][1]["role"] == "assistant"
    assert rows[0]["sessions"][0]["turns"][0]["content"].startswith(
        "[Session date: 1:56 pm on 8 May, 2023] Caroline:"
    )
    assert rows[0]["sessions"][0]["turns"][1]["metadata"]["blip_caption"] == ("a colorful mural")
    assert rows[1]["category"] == "adversarial"
    assert rows[1]["expected_behavior"] == "refuse_or_unknown"
    assert rows[1]["expected_answer"] is None
    assert rows[1]["forbidden_answers"] == ["a painting"]
    assert rows[1]["gold_memory_ids"] == ["D1:1", "D1:2"]
    assert rows[2]["expected_behavior"] == "answer"
    assert rows[2]["expected_answer"] == "No"
    assert rows[2]["forbidden_answers"] == ["Yes"]


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


def test_memoryagentbench_adapter_converts_official_conflict_parquet(
    tmp_path: Path,
) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    table = pa.Table.from_pylist(
        [
            {
                "context": (
                    "Here is a list of facts:\n"
                    "0. The chairperson is Alice.\n"
                    "1. The chairperson is Bob.\n"
                ),
                "questions": ["Who is the chairperson?", "Who holds the role now?"],
                "answers": [["Bob"], ["Bob", "Robert"]],
                "metadata": {
                    "source": "factconsolidation_sh_6k",
                    "qa_pair_ids": ["pair-1", "pair-2"],
                },
            }
        ]
    )
    pq.write_table(table, raw_dir / "Conflict_Resolution.parquet")

    output = memoryagentbench_adapter.convert(raw_dir, processed_dir)

    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["case_id"] == "memoryagentbench_pair-1"
    assert rows[0]["category"] == "conflict_single_hop_6k"
    assert rows[0]["expected_behavior"] == "answer_latest"
    assert rows[0]["expected_answer"] == "Bob"
    assert rows[0]["metadata"]["context_group_id"] == "factconsolidation_sh_6k"
    assert rows[1]["metadata"]["accepted_answers"] == ["Bob", "Robert"]
    assert rows[0]["sessions"][0]["turns"][0]["content"].startswith("[Memory sequence 0001]")
