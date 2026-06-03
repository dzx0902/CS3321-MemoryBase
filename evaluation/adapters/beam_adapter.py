from __future__ import annotations

from pathlib import Path


def convert(raw_dir: Path, processed_dir: Path) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    raise NotImplementedError(
        "BEAM adapter is reserved for a later phase. "
        f"Place raw files under {raw_dir} before conversion."
    )
