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
    assert len(cases[1].sessions[1].turns[0].content) > len(cases[0].sessions[1].turns[0].content)
