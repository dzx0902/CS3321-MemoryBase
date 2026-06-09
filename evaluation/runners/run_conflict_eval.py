from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.runners.common import build_parser, print_summary, run_eval  # noqa: E402


def main() -> None:
    parser = build_parser("Run conflict evaluation.", default_output="conflict_results.csv")
    args = parser.parse_args()
    results = run_eval(
        dataset=args.dataset,
        output=args.output,
        mode=args.mode,
        category=args.category,
        limit=args.limit,
        dry_run=args.dry_run,
        run_id=args.run_id,
        result_filter=None if args.category else "temporal_update",
        api_base_url=args.api_base,
        workspace=args.workspace,
        agent=args.agent,
        cleanup=not args.preserve_eval_data,
        isolate=not args.shared_workspace,
    )
    print_summary(results, args.output)


if __name__ == "__main__":
    main()
