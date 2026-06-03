# ruff: noqa: E402,I001

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.adapters import (
    beam_adapter,
    beir_adapter,
    locomo_adapter,
    longmemeval_adapter,
    memoryagentbench_adapter,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_ROOT = PROJECT_ROOT / "evaluation" / "external"

ADAPTERS = {
    "longmemeval": longmemeval_adapter.convert,
    "locomo": locomo_adapter.convert,
    "memoryagentbench": memoryagentbench_adapter.convert,
    "beam": beam_adapter.convert,
    "beir": beir_adapter.convert,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert external benchmark data.")
    parser.add_argument(
        "--benchmark",
        required=True,
        choices=sorted(ADAPTERS),
    )
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--processed-dir", type=Path)
    args = parser.parse_args()

    raw_dir = args.raw_dir or EXTERNAL_ROOT / args.benchmark / "raw"
    processed_dir = args.processed_dir or EXTERNAL_ROOT / args.benchmark / "processed"
    try:
        output = ADAPTERS[args.benchmark](raw_dir, processed_dir)
    except NotImplementedError as exc:
        print(str(exc))
        raise SystemExit(2) from exc
    print(f"wrote converted cases to {output}")


if __name__ == "__main__":
    main()
