from __future__ import annotations

from typing import Any

from ..services.context_pack_service import count_tokens, trim_to_token_budget
from .repo_context import RepoContext


def render_unified_context(
    *,
    query: str,
    workspace: str | None,
    agent: str | None,
    memory_markdown: str,
    session_messages: list[dict[str, Any]],
    search_items: list[dict[str, Any]],
    repo_context: RepoContext | None,
    max_tokens: int,
) -> tuple[str, dict[str, int]]:
    source_counts = {
        "memory": 1 if memory_markdown.strip() else 0,
        "session": len(session_messages),
        "search": len(search_items),
        "repo": len(repo_context.snippets)
        if repo_context and repo_context.snippets
        else int(bool(repo_context and repo_context.metadata.git_root)),
    }
    lines: list[str] = [
        "# MemoryBase Context",
        "",
        "## Current Task",
        f"- query: {query}",
    ]
    if workspace:
        lines.append(f"- workspace: {workspace}")
    if agent:
        lines.append(f"- agent: {agent}")
    if repo_context and repo_context.metadata.branch:
        lines.append(f"- branch: {repo_context.metadata.branch}")

    lines.extend(["", "## Repository State"])
    if repo_context and repo_context.metadata.git_root is not None:
        lines.append(f"- git_root: {repo_context.metadata.git_root}")
        lines.append(f"- branch: {repo_context.metadata.branch or 'unknown'}")
        if repo_context.metadata.changed_files:
            lines.append("- changed files:")
            lines.extend(f"  - {path}" for path in repo_context.metadata.changed_files[:20])
        else:
            lines.append("- changed files: none")
        if repo_context.metadata.diff_stat:
            lines.extend(
                ["- diff stat:", "```text", repo_context.metadata.diff_stat.rstrip(), "```"]
            )
        if repo_context.metadata.recent_commits:
            lines.append("- recent commits:")
            lines.extend(f"  - {commit}" for commit in repo_context.metadata.recent_commits[:5])
    else:
        lines.append("- No git repository context available.")
    if repo_context and repo_context.warnings:
        lines.append("- warnings:")
        lines.extend(f"  - {warning}" for warning in repo_context.warnings)

    lines.extend(["", "## Session Notes"])
    if session_messages:
        for index, message in enumerate(session_messages, start=1):
            role = message.get("role", "unknown")
            content = compact(str(message.get("content", "")), 500)
            lines.append(f"- [S{index}] {role}: {content}")
    else:
        lines.append("- None provided.")

    if memory_markdown.strip():
        memory_body = strip_memorybase_title(memory_markdown)
        lines.extend(["", "## Long-Term Memory"])
        lines.append(memory_body.rstrip())
    else:
        lines.extend(["", "## Long-Term Memory", "- None returned."])

    lines.extend(["", "## Search Results"])
    if search_items:
        for index, item in enumerate(search_items, start=1):
            source = item.get("source_path") or item.get("source_title") or item.get("result_id")
            start_line = item.get("start_line")
            end_line = item.get("end_line")
            line_ref = f":{start_line}-{end_line}" if start_line and end_line else ""
            snippet = compact(str(item.get("snippet") or ""), 500)
            strategies = ", ".join(str(value) for value in item.get("strategies", []))
            lines.append(f"- [Q{index}] {source}{line_ref} ({strategies}) {snippet}")
    else:
        lines.append("- None returned.")

    lines.extend(["", "## Repo Snippets"])
    if repo_context and repo_context.snippets:
        for index, snippet in enumerate(repo_context.snippets, start=1):
            lines.append(
                f"- [R{index}] {snippet.path}:{snippet.start_line}-{snippet.end_line} "
                f"({snippet.reason})"
            )
            lines.extend(["```text", snippet.text.rstrip(), "```"])
    else:
        lines.append("- None selected.")

    lines.extend(
        [
            "",
            "## Metadata",
            (
                "- source_counts: "
                f"memory={source_counts['memory']}, "
                f"session={source_counts['session']}, repo={source_counts['repo']}"
                f", search={source_counts['search']}"
            ),
        ]
    )
    markdown = "\n".join(lines).rstrip() + "\n"
    if count_tokens(markdown) > max_tokens:
        markdown = trim_to_token_budget(markdown, max_tokens)
    return markdown, source_counts


def strip_memorybase_title(markdown: str) -> str:
    lines = markdown.splitlines()
    if lines and lines[0].strip() == "# MemoryBase Context":
        return "\n".join(lines[1:]).lstrip()
    return markdown


def compact(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"
