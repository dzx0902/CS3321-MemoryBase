from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.performance import (  # noqa: E402
    run_api_performance_suite,
    write_performance_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark live MemoryBase API operations.")
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--workspace", default=os.getenv("MEMORYBASE_WORKSPACE"))
    parser.add_argument("--agent", default=os.getenv("MEMORYBASE_AGENT"))
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--include-qa", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/outputs/performance/api_operation_results.csv"),
    )
    args = parser.parse_args()
    if not args.workspace:
        raise SystemExit("--workspace or MEMORYBASE_WORKSPACE is required")

    samples = run_api_performance_suite(
        api_base_url=args.api_base,
        workspace=args.workspace,
        agent=args.agent,
        iterations=args.iterations,
        include_qa=args.include_qa,
    )
    csv_path, summary_path = write_performance_outputs(output_csv=args.output, samples=samples)
    print(f"wrote operation samples to {csv_path}")
    print(f"wrote operation summary to {summary_path}")
    print(summary_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
