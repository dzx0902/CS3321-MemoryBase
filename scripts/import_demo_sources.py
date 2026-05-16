"""Inspect demo source files used by database/07_seed.sql.

The P0 seed currently inserts SourceDocument and SourceChunk rows directly so
schema initialization does not depend on Python database packages. This helper
keeps the source-material side auditable for demos and reports.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DEMO_PATH = Path("data/raw_sources/demo_workspace")
EXPECTED_SOURCE_COUNT = 6


@dataclass(frozen=True)
class DemoSource:
    path: Path
    line_count: int
    sha256: str


def inspect_demo_sources(root: Path) -> list[DemoSource]:
    if not root.exists():
        return []

    sources: list[DemoSource] = []
    for path in sorted(root.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        sources.append(
            DemoSource(
                path=path,
                line_count=len(content.splitlines()),
                sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            )
        )
    return sources


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_DEMO_PATH,
        help=f"Demo source directory. Default: {DEFAULT_DEMO_PATH}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=f"Fail unless exactly {EXPECTED_SOURCE_COUNT} Markdown files exist.",
    )
    args = parser.parse_args()

    sources = inspect_demo_sources(args.root)
    for source in sources:
        print(f"{source.path}\tlines={source.line_count}\tsha256={source.sha256}")

    if args.check and len(sources) != EXPECTED_SOURCE_COUNT:
        print(
            f"Expected {EXPECTED_SOURCE_COUNT} demo sources under {args.root}, "
            f"found {len(sources)}."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
