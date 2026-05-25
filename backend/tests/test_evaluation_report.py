from __future__ import annotations

import csv
from pathlib import Path

from evaluation.reports.generate_report import generate_report


def test_generate_report_includes_baseline_and_category_metrics(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    with (output_dir / "qa_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "source",
                "category",
                "query",
                "expected_answer",
                "generated_answer",
                "retrieved_memory_ids",
                "retrieved_memory_texts",
                "retrieved_scores",
                "latency_ms",
                "token_usage",
                "score",
                "pass",
                "exact_match",
                "contains_match",
                "simple_f1",
                "forbidden_answer_violation",
                "recall_at_1",
                "recall_at_3",
                "recall_at_5",
                "recall_at_10",
                "mrr",
                "ndcg_at_10",
                "deletion_success",
                "privacy_leakage",
                "stale_memory_error",
                "preference_following",
                "error",
                "mode",
                "run_id",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "case_1",
                "source": "synthetic",
                "category": "deletion",
                "query": "secret?",
                "expected_answer": "",
                "generated_answer": "I do not know.",
                "latency_ms": "2.0",
                "score": "1.0",
                "pass": "true",
                "simple_f1": "1.0",
                "privacy_leakage": "false",
                "mode": "summary_memory",
                "run_id": "test",
            }
        )

    report_path = generate_report(outputs_dir=output_dir)

    report = report_path.read_text(encoding="utf-8")
    assert "## Baseline Metrics" in report
    assert "summary_memory" in report
    assert "## Category Detail Metrics" in report
    assert "deletion" in report
