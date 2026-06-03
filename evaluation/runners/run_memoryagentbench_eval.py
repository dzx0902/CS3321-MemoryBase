from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.runners.run_external_eval import (  # noqa: E402
    EXTERNAL_ROOT,
    memoryagentbench_adapter,
)


def main() -> None:
    try:
        output = memoryagentbench_adapter.convert(
            EXTERNAL_ROOT / "memoryagentbench" / "raw",
            EXTERNAL_ROOT / "memoryagentbench" / "processed",
        )
    except NotImplementedError as exc:
        print(str(exc))
        raise SystemExit(2) from exc
    print(f"wrote converted MemoryAgentBench cases to {output}")


if __name__ == "__main__":
    main()
