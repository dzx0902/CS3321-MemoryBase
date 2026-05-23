from __future__ import annotations

import subprocess
from pathlib import Path

from app.cli.repo_context import collect_repo_context


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


def test_collect_repo_context_returns_git_metadata_and_changed_files(tmp_path: Path) -> None:
    init_repo(tmp_path)
    source = tmp_path / "app.py"
    source.write_text("print('hello')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)
    source.write_text("print('hello')\nprint('memorybase context')\n", encoding="utf-8")

    context = collect_repo_context("memorybase context", repo_root=tmp_path, snippet_limit=4)

    assert context.metadata.git_root == tmp_path
    assert context.metadata.branch
    assert "app.py" in context.metadata.changed_files
    assert "app.py" in context.metadata.diff_stat
    assert context.metadata.recent_commits
    assert any(snippet.path == "app.py" for snippet in context.snippets)
    assert any("memorybase context" in snippet.text for snippet in context.snippets)


def test_collect_repo_context_excludes_generated_and_binary_like_files(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "uv.lock").write_text("context should not appear\n", encoding="utf-8")
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "pkg.js").write_text("context should not appear\n", encoding="utf-8")
    binary_file = tmp_path / "image.png"
    binary_file.write_bytes(b"\x00\x01\x02context\x00")
    source = tmp_path / "notes.md"
    source.write_text("MemoryBase context belongs here.\n", encoding="utf-8")

    context = collect_repo_context("context", repo_root=tmp_path, snippet_limit=10)

    paths = {snippet.path for snippet in context.snippets}
    assert "notes.md" in paths
    assert "uv.lock" not in paths
    assert "node_modules/pkg.js" not in paths
    assert "image.png" not in paths


def test_collect_repo_context_outside_git_repo_returns_warning(tmp_path: Path) -> None:
    context = collect_repo_context("anything", repo_root=tmp_path)

    assert context.metadata.git_root is None
    assert context.snippets == []
    assert context.warnings
