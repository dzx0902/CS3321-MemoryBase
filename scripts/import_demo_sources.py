import os
from pathlib import Path


def list_demo_sources(root: str) -> list[str]:
    path = Path(root)
    if not path.exists():
        return []
    return sorted(str(file) for file in path.glob("*.md"))


def main() -> None:
    demo_path = os.environ.get("DEMO_SOURCES_PATH", "data/raw_sources/demo_workspace")
    for file_path in list_demo_sources(demo_path):
        print(file_path)


if __name__ == "__main__":
    main()
