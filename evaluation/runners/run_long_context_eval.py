from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.generators.long_context import generate_long_context_cases  # noqa: E402
from evaluation.reports.generate_report import generate_report  # noqa: E402
from evaluation.runners.common import new_run_id, print_summary, run_eval  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run measured long-context retention cases.")
    parser.add_argument(
        "--token-lengths",
        default="1000,10000,50000,100000",
        help="Comma-separated target history token lengths.",
    )
    parser.add_argument(
        "--mode",
        default="db_qa",
        choices=[
            "recency_only",
            "summary_memory",
            "db_memory",
            "db_qa",
            "vector_qa",
            "db_extraction_qa",
        ],
    )
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--agent", default=None)
    parser.add_argument("--outputs-dir", type=Path, default=Path("evaluation/outputs/long_context"))
    parser.add_argument("--dataset-output", type=Path)
    parser.add_argument("--preserve-eval-data", action="store_true")
    parser.add_argument("--shared-workspace", action="store_true")
    args = parser.parse_args()

    lengths = _parse_lengths(args.token_lengths)
    dataset = args.dataset_output or args.outputs_dir / "_generated" / "long_context_cases.jsonl"
    generate_long_context_cases(dataset, token_lengths=lengths)
    output = args.outputs_dir / args.mode / "long_context_results.csv"
    results = run_eval(
        dataset=dataset,
        output=output,
        mode=args.mode,
        category=None,
        limit=None,
        dry_run=False,
        run_id=new_run_id(),
        api_base_url=args.api_base,
        workspace=args.workspace,
        agent=args.agent,
        cleanup=not args.preserve_eval_data,
        isolate=not args.shared_workspace,
    )
    print_summary(results, output)
    print(f"wrote benchmark report to {generate_report(outputs_dir=args.outputs_dir)}")


def _parse_lengths(raw: str) -> list[int]:
    lengths = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not lengths:
        raise SystemExit("--token-lengths must include at least one integer")
    if any(length < 128 for length in lengths):
        raise SystemExit("all token lengths must be at least 128")
    return lengths


if __name__ == "__main__":
    main()
