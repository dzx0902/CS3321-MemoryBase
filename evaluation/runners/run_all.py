# ruff: noqa: E402,I001

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.reports.generate_report import generate_report  # noqa: E402
from evaluation.runners.common import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUTS,
    new_run_id,
    print_summary,
    run_eval,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all MemoryBase evaluations.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--mode",
        default="no_memory",
        choices=["no_memory", "recency_only", "naive_vector_rag", "summary_memory", "db_memory"],
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--outputs-dir", type=Path, default=DEFAULT_OUTPUTS)
    parser.add_argument("--run-id")
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--agent", default=None)
    args = parser.parse_args()

    run_id = args.run_id or new_run_id()
    jobs = [
        ("qa_results.csv", None),
        ("retrieval_results.csv", None),
        ("conflict_results.csv", "temporal_update"),
        ("deletion_results.csv", "deletion"),
        ("preference_results.csv", "preference_following"),
        ("forgetting_results.csv", "long_context_retention"),
        ("performance_results.csv", "performance"),
    ]
    for filename, result_filter in jobs:
        output = args.outputs_dir / filename
        results = run_eval(
            dataset=args.dataset,
            output=output,
            mode=args.mode,
            category=args.category,
            limit=args.limit,
            dry_run=args.dry_run,
            run_id=run_id,
            result_filter=result_filter,
            api_base_url=args.api_base,
            workspace=args.workspace,
            agent=args.agent,
        )
        print_summary(results, output)
    report_path = generate_report(outputs_dir=args.outputs_dir)
    print(f"wrote benchmark report to {report_path}")


if __name__ == "__main__":
    main()
