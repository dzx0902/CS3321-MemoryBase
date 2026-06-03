from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.runners.run_external_eval import EXTERNAL_ROOT, locomo_adapter  # noqa: E402


def main() -> None:
    try:
        output = locomo_adapter.convert(
            EXTERNAL_ROOT / "locomo" / "raw",
            EXTERNAL_ROOT / "locomo" / "processed",
        )
    except NotImplementedError as exc:
        print(str(exc))
        raise SystemExit(2) from exc
    print(f"wrote converted LoCoMo cases to {output}")


if __name__ == "__main__":
    main()
