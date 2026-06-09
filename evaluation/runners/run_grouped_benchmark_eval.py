from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.baselines import LiveMemoryBaseline, build_baseline_with_config  # noqa: E402
from evaluation.cases import load_cases  # noqa: E402
from evaluation.io import write_results_csv  # noqa: E402
from evaluation.runners.common import _score_result, new_run_id, print_summary  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run inject-once/query-many grouped live evaluation."
    )
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--group-field", default="context_group_id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--workspace")
    parser.add_argument("--agent")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preserve-eval-data", action="store_true")
    parser.add_argument("--shared-workspace", action="store_true")
    args = parser.parse_args()

    cases = [
        case
        for case in load_cases(args.dataset)
        if str(case.metadata.get(args.group_field)) == args.group
        and (not args.case_id or case.case_id in args.case_id)
    ]
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit(f"no cases found for {args.group_field}={args.group!r}")

    baseline = build_baseline_with_config(
        mode="db_qa",
        run_id=new_run_id(),
        api_base_url=args.api_base,
        workspace=args.workspace,
        agent=args.agent,
        cleanup=not args.preserve_eval_data,
        isolate=not args.shared_workspace,
    )
    if not isinstance(baseline, LiveMemoryBaseline):
        raise SystemExit("grouped evaluation requires a live MemoryBase baseline")
    results = [
        _score_result(case, result)
        for case, result in zip(cases, baseline.run_group(cases), strict=True)
    ]
    write_results_csv(args.output, results)
    print_summary(results, args.output)


if __name__ == "__main__":
    main()
