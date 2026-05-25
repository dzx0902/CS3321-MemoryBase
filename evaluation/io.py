from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from evaluation.baselines import EvaluationResult

RESULT_FIELDS = [
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
]


def write_results_csv(path: Path, results: Iterable[EvaluationResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow(result_to_row(result))


def result_to_row(result: EvaluationResult) -> dict[str, object]:
    metrics = result.metadata.get("metrics", {})
    return {
        "case_id": result.case_id,
        "source": result.source,
        "category": result.category,
        "query": result.query,
        "expected_answer": result.expected_answer or "",
        "generated_answer": result.generated_answer,
        "retrieved_memory_ids": "|".join(result.retrieved_memory_ids),
        "retrieved_memory_texts": "|".join(result.retrieved_memory_texts),
        "retrieved_scores": "|".join(f"{score:.6f}" for score in result.retrieved_scores),
        "latency_ms": f"{result.latency_ms:.3f}",
        "token_usage": result.token_usage if result.token_usage is not None else "",
        "score": f"{result.score:.6f}",
        "pass": "true" if result.passed else "false",
        "exact_match": _metric(metrics, "exact_match"),
        "contains_match": _metric(metrics, "contains_match"),
        "simple_f1": _metric(metrics, "simple_f1"),
        "forbidden_answer_violation": _metric(metrics, "forbidden_answer_violation"),
        "recall_at_1": _metric(metrics, "recall_at_1"),
        "recall_at_3": _metric(metrics, "recall_at_3"),
        "recall_at_5": _metric(metrics, "recall_at_5"),
        "recall_at_10": _metric(metrics, "recall_at_10"),
        "mrr": _metric(metrics, "mrr"),
        "ndcg_at_10": _metric(metrics, "ndcg_at_10"),
        "deletion_success": _metric(metrics, "deletion_success"),
        "privacy_leakage": _metric(metrics, "privacy_leakage"),
        "stale_memory_error": _metric(metrics, "stale_memory_error"),
        "preference_following": _metric(metrics, "preference_following"),
        "error": result.error,
        "mode": result.mode,
        "run_id": result.run_id,
    }


def _metric(metrics: dict[str, object], key: str) -> str:
    value = metrics.get(key)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)
