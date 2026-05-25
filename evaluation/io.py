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
        "error": result.error,
        "mode": result.mode,
        "run_id": result.run_id,
    }
