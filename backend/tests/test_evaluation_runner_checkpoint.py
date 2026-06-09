from __future__ import annotations

import csv
from pathlib import Path

from evaluation.baselines import EvaluationResult
from evaluation.io import append_result_csv, completed_case_ids, write_results_csv


def _result(case_id: str) -> EvaluationResult:
    return EvaluationResult(
        case_id=case_id,
        source="synthetic",
        category="single_fact",
        query="question",
        expected_answer="answer",
        generated_answer="answer",
        mode="db_qa",
        run_id="test",
    )


def test_append_result_csv_checkpoints_each_case(tmp_path: Path) -> None:
    output = tmp_path / "results.csv"

    write_results_csv(output, [])
    append_result_csv(output, _result("case-1"))
    append_result_csv(output, _result("case-2"))

    with output.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["case_id"] for row in rows] == ["case-1", "case-2"]
    assert completed_case_ids(output) == {"case-1", "case-2"}


def test_completed_case_ids_handles_missing_output(tmp_path: Path) -> None:
    assert completed_case_ids(tmp_path / "missing.csv") == set()
