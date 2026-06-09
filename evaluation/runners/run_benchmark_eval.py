from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.runners.common import new_run_id, print_summary, run_eval  # noqa: E402
from evaluation.runners.run_external_eval import ADAPTERS, EXTERNAL_ROOT  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert an external benchmark and run it through MemoryBase."
    )
    parser.add_argument("--benchmark", required=True, choices=sorted(ADAPTERS))
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--processed-dir", type=Path)
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
    parser.add_argument("--limit", type=int)
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--agent", default=None)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preserve-eval-data", action="store_true")
    parser.add_argument("--shared-workspace", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep existing results and skip case IDs already present in the output CSV.",
    )
    args = parser.parse_args()

    raw_dir = args.raw_dir or EXTERNAL_ROOT / args.benchmark / "raw"
    processed_dir = args.processed_dir or EXTERNAL_ROOT / args.benchmark / "processed"
    dataset = ADAPTERS[args.benchmark](raw_dir, processed_dir)
    output = args.output or (
        Path("evaluation/outputs/external")
        / args.benchmark
        / args.mode
        / f"{args.benchmark}_results.csv"
    )
    results = run_eval(
        dataset=dataset,
        output=output,
        mode=args.mode,
        category=None,
        limit=args.limit,
        dry_run=False,
        run_id=new_run_id(),
        api_base_url=args.api_base,
        workspace=args.workspace,
        agent=args.agent,
        cleanup=not args.preserve_eval_data,
        isolate=not args.shared_workspace,
        resume=args.resume,
    )
    print_summary(results, output)


if __name__ == "__main__":
    main()
