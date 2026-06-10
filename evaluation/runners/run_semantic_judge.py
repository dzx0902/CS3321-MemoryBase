from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.judging import judge_results_csv  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(description="Judge QA results semantically.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--api-key", default=os.getenv("DEEPSEEK_API_KEY"))
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
    )
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("--api-key or DEEPSEEK_API_KEY is required")
    output = judge_results_csv(
        input_csv=args.input,
        dataset=args.dataset,
        output_csv=args.output,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        provider=args.provider,
    )
    print(f"wrote judged results to {output}")


if __name__ == "__main__":
    main()
