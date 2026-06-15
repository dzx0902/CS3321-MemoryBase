from __future__ import annotations

from pathlib import Path

from evaluation.cases import load_cases
from evaluation.generators.long_context import generate_long_context_cases


def test_long_context_generator_measures_actual_tokens(tmp_path: Path) -> None:
    output = generate_long_context_cases(
        tmp_path / "long_context.jsonl",
        token_lengths=[1000, 2000],
    )

    cases = load_cases(output)

    assert [case.metadata["actual_history_tokens"] for case in cases] == [1000, 2000]
    assert all(case.expected_answer == "Aurora" for case in cases)
    assert [case.metadata["memory_turn_count"] for case in cases] == [2, 3]
    assert len(cases[0].sessions) == 3
    assert len(cases[1].sessions) == 4
    assert all(
        "durable project code" not in session.turns[0].content
        for case in cases
        for session in case.sessions[1:-1]
    )


def test_long_context_generator_splits_100k_history_into_bounded_memories(
    tmp_path: Path,
) -> None:
    output = generate_long_context_cases(
        tmp_path / "long_context_100k.jsonl",
        token_lengths=[100000],
    )

    case = load_cases(output)[0]

    assert case.metadata["actual_history_tokens"] == 100000
    assert case.metadata["memory_turn_count"] == 101
    assert len(case.sessions) == 102
