from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.runners.run_external_eval import EXTERNAL_ROOT, longmemeval_adapter  # noqa: E402


def main() -> None:
    try:
        output = longmemeval_adapter.convert(
            EXTERNAL_ROOT / "longmemeval" / "raw",
            EXTERNAL_ROOT / "longmemeval" / "processed",
        )
    except NotImplementedError as exc:
        print(str(exc))
        raise SystemExit(2) from exc
    print(f"wrote converted LongMemEval cases to {output}")


if __name__ == "__main__":
    main()
