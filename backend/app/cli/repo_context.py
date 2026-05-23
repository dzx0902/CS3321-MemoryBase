from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
    ".js",
    ".ts",
    ".tsx",
    ".css",
    ".html",
}
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}
EXCLUDED_NAMES = {"uv.lock", "package-lock.json"}


@dataclass(frozen=True, slots=True)
class RepoMetadata:
    git_root: Path | None
    branch: str | None = None
    status_short: str = ""
    changed_files: list[str] = field(default_factory=list)
    diff_stat: str = ""
    recent_commits: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RepoSnippet:
    path: str
    start_line: int
    end_line: int
    reason: str
    text: str


@dataclass(frozen=True, slots=True)
class RepoContext:
    metadata: RepoMetadata
    snippets: list[RepoSnippet]
    warnings: list[str]


def collect_repo_context(
    query: str,
    *,
    repo_root: Path | None = None,
    snippet_limit: int = 8,
    max_file_bytes: int = 80_000,
) -> RepoContext:
    warnings: list[str] = []
    root = resolve_git_root(repo_root or Path.cwd())
    if root is None:
        return RepoContext(
            metadata=RepoMetadata(git_root=None),
            snippets=[],
            warnings=["not inside a git repository"],
        )

    metadata = RepoMetadata(
        git_root=root,
        branch=run_git(root, "branch", "--show-current").strip() or None,
        status_short=run_git(root, "status", "--short"),
        changed_files=parse_changed_files(run_git(root, "status", "--short")),
        diff_stat=run_git(root, "diff", "--stat"),
        recent_commits=run_git(root, "log", "--oneline", "-5").splitlines(),
    )
    snippets = select_snippets(
        root,
        query,
        changed_files=metadata.changed_files,
        limit=snippet_limit,
        max_file_bytes=max_file_bytes,
        warnings=warnings,
    )
    return RepoContext(metadata=metadata, snippets=snippets, warnings=warnings)


def resolve_git_root(path: Path) -> Path | None:
    result = run_command(["git", "rev-parse", "--show-toplevel"], cwd=path)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def run_git(root: Path, *args: str) -> str:
    result = run_command(["git", *args], cwd=root)
    return result.stdout if result.returncode == 0 else ""


def run_command(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(args=args, returncode=127, stdout="", stderr=str(exc))


def parse_changed_files(status_short: str) -> list[str]:
    paths: list[str] = []
    for line in status_short.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and not is_excluded_path(Path(path)):
            paths.append(path)
    return paths


def select_snippets(
    root: Path,
    query: str,
    *,
    changed_files: list[str],
    limit: int,
    max_file_bytes: int,
    warnings: list[str],
) -> list[RepoSnippet]:
    snippets: list[RepoSnippet] = []
    seen: set[str] = set()
    for path in changed_files:
        add_file_snippet(
            root,
            path,
            reason="changed_file",
            snippets=snippets,
            seen=seen,
            max_file_bytes=max_file_bytes,
        )
        if len(snippets) >= limit:
            return snippets

    for path, line_no in rg_hits(root, query, warnings=warnings):
        add_file_snippet(
            root,
            path,
            reason="query_hit",
            snippets=snippets,
            seen=seen,
            max_file_bytes=max_file_bytes,
            center_line=line_no,
        )
        if len(snippets) >= limit:
            return snippets
    return snippets


def rg_hits(root: Path, query: str, *, warnings: list[str]) -> list[tuple[str, int]]:
    terms = [term for term in query.split() if term]
    if not terms:
        return []
    result = run_command(["rg", "-n", "--fixed-strings", terms[0]], cwd=root)
    if result.returncode not in {0, 1}:
        warnings.append("rg unavailable; falling back to Python file scan")
        return python_scan_hits(root, terms[0])
    hits: list[tuple[str, int]] = []
    for line in result.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path = parts[0]
        if is_excluded_path(Path(path)):
            continue
        try:
            line_no = int(parts[1])
        except ValueError:
            line_no = 1
        hits.append((path, line_no))
    return hits


def python_scan_hits(root: Path, term: str) -> list[tuple[str, int]]:
    hits: list[tuple[str, int]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_excluded_path(rel) or not is_text_candidate(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            if term in line:
                hits.append((str(rel), index))
                break
    return hits


def add_file_snippet(
    root: Path,
    path: str,
    *,
    reason: str,
    snippets: list[RepoSnippet],
    seen: set[str],
    max_file_bytes: int,
    center_line: int | None = None,
) -> None:
    rel = Path(path)
    if str(rel) in seen or is_excluded_path(rel):
        return
    full_path = root / rel
    if not full_path.exists() or not is_text_candidate(full_path, max_file_bytes=max_file_bytes):
        return
    try:
        lines = full_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return
    if not lines:
        return
    if center_line is None:
        start = 1
        end = min(len(lines), 80)
    else:
        start = max(1, center_line - 4)
        end = min(len(lines), center_line + 12)
    text = "\n".join(lines[start - 1 : end])
    snippets.append(
        RepoSnippet(
            path=str(rel),
            start_line=start,
            end_line=end,
            reason=reason,
            text=text,
        )
    )
    seen.add(str(rel))


def is_excluded_path(path: Path) -> bool:
    if path.name in EXCLUDED_NAMES or path.name.endswith(".egg-info"):
        return True
    return any(part in EXCLUDED_PARTS for part in path.parts)


def is_text_candidate(path: Path, *, max_file_bytes: int = 80_000) -> bool:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > max_file_bytes:
            return False
        sample = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\x00" not in sample
