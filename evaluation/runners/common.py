from __future__ import annotations

import argparse
import secrets
from datetime import UTC, datetime
from pathlib import Path

from evaluation.baselines import EvaluationResult, build_baseline_with_config
from evaluation.cases import EvaluationCase, load_cases
from evaluation.io import write_results_csv
from evaluation.metrics.qa_metrics import score_qa
from evaluation.metrics.retrieval_metrics import score_retrieval

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_ROOT / "evaluation" / "datasets" / "synthetic_memory_cases.jsonl"
DEFAULT_OUTPUTS = PROJECT_ROOT / "evaluation" / "outputs"


def build_parser(description: str, *, default_output: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--mode",
        default="no_memory",
        choices=["no_memory", "recency_only", "naive_vector_rag", "summary_memory", "db_memory"],
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUTS / default_output)
    parser.add_argument("--run-id")
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--agent", default=None)
    return parser


def new_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"eval_{timestamp}_{secrets.token_hex(3)}"


def run_eval(
    *,
    dataset: Path,
    output: Path,
    mode: str,
    category: str | None,
    limit: int | None,
    dry_run: bool,
    run_id: str | None,
    result_filter: str | None = None,
    api_base_url: str | None = None,
    workspace: str | None = None,
    agent: str | None = None,
) -> list[EvaluationResult]:
    resolved_run_id = run_id or new_run_id()
    cases = load_cases(dataset, category=category, limit=limit)
    if result_filter is not None:
        cases = [case for case in cases if case.category == result_filter]
    baseline = build_baseline_with_config(
        mode=mode,
        run_id=resolved_run_id,
        dry_run=dry_run,
        api_base_url=api_base_url,
        workspace=workspace,
        agent=agent,
    )
    results = [_score_result(case, baseline.run_case(case)) for case in cases]
    write_results_csv(output, results)
    return results


def print_summary(results: list[EvaluationResult], output: Path) -> None:
    passed = sum(1 for result in results if result.passed)
    errored = sum(1 for result in results if result.error)
    print(
        f"wrote {len(results)} results to {output} "
        f"(pass={passed}, fail={len(results) - passed}, errors={errored})"
    )


def _score_result(case: EvaluationCase, result: EvaluationResult) -> EvaluationResult:
    qa = score_qa(case, result.generated_answer)
    retrieval = score_retrieval(case.gold_memory_ids, result.retrieved_memory_ids)
    result.score = float(qa["score"])
    result.passed = bool(qa["pass"]) and not result.error
    metrics = {
        **qa,
        **retrieval,
        "deletion_success": _deletion_success(case, qa),
        "privacy_leakage": bool(qa["forbidden_answer_violation"]),
        "stale_memory_error": _stale_memory_error(case, qa),
        "preference_following": _preference_following(case, qa),
    }
    result.metadata = {**result.metadata, "qa": qa, "retrieval": retrieval, "metrics": metrics}
    return result


def _deletion_success(case: EvaluationCase, qa: dict[str, float | bool]) -> bool | None:
    if case.category != "deletion" and case.expected_behavior != "refuse_or_unknown":
        return None
    return not bool(qa["forbidden_answer_violation"])


def _stale_memory_error(case: EvaluationCase, qa: dict[str, float | bool]) -> bool | None:
    if case.category not in {"temporal_update", "conflict"}:
        return None
    return bool(qa["forbidden_answer_violation"])


def _preference_following(case: EvaluationCase, qa: dict[str, float | bool]) -> bool | None:
    if case.category != "preference_following" and case.expected_behavior != "follow_preference":
        return None
    return bool(qa["pass"])
