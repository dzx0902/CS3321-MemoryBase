from __future__ import annotations

from pathlib import Path

import typer

from ...services.context_pack_service import count_tokens
from ..client import MemoryBaseClientError, MemoryBaseServerError, build_client
from ..config import load_config
from ..context_renderer import render_unified_context
from ..output import (
    EXIT_CLIENT_ERROR,
    EXIT_NO_RESULT,
    EXIT_OK,
    EXIT_SERVER_ERROR,
    error,
    info,
)
from ..repo_context import collect_repo_context
from ..runtime import resolve_workspace_and_agent


def context(
    query: str = typer.Argument(..., help="Recall query text."),
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    session_id: str | None = typer.Option(None, "--session", help="Session UUID to include."),
    include_repo: bool = typer.Option(
        True,
        "--include-repo/--no-repo",
        help="Include repo context.",
    ),
    repo_only: bool = typer.Option(False, "--repo-only", help="Only render repo context."),
    no_memory: bool = typer.Option(False, "--no-memory", help="Skip MemoryBase recall."),
    repo_root: Path | None = typer.Option(None, "--repo-root", help="Repo root for local context."),
    repo_query: str | None = typer.Option(None, "--repo-query", help="Separate repo search query."),
    repo_limit: int = typer.Option(8, "--repo-limit", min=0, max=50),
    session_limit: int = typer.Option(20, "--session-limit", min=1, max=100),
    as_of: str | None = typer.Option(None, "--as-of", help="Temporal recall timestamp."),
    limit: int = typer.Option(10, "--limit", min=1, max=50, help="Maximum memories."),
    max_tokens: int = typer.Option(3000, "--max-tokens", min=100, help="Context token budget."),
) -> None:
    config = load_config(config_path).with_overrides(
        api_base_url=api_base_url,
        workspace=workspace,
        agent=agent,
    )
    memory_result: dict[str, object] = {
        "result_count": 0,
        "markdown": "",
        "recall_id": None,
        "token_count": 0,
    }
    session_messages: list[dict[str, object]] = []
    search_items: list[dict[str, object]] = []
    repo_context = None
    try:
        workspace_id: str | None = None
        agent_id: str | None = None
        active_session = session_id or config.active_session
        memory_enabled = not repo_only and not no_memory
        session_enabled = not repo_only and active_session is not None
        if memory_enabled or session_enabled:
            client = build_client(config)
            workspace_id, agent_id = resolve_workspace_and_agent(client, config)
            if memory_enabled:
                payload = {
                    "workspace_id": workspace_id,
                    "agent_id": agent_id,
                    "query_text": query,
                    "as_of": as_of,
                    "limit": limit,
                    "max_tokens": max_tokens,
                }
                payload = {key: value for key, value in payload.items() if value is not None}
                memory_result = client.context_pack(payload)
                if int(memory_result.get("result_count", 0)) == 0:
                    search_result = client.search(
                        {
                            "workspace_id": workspace_id,
                            "agent_id": agent_id,
                            "query_text": query,
                            "scope": "all",
                            "limit": min(limit, 10),
                        }
                    )
                    raw_search_items = search_result.get("items", [])
                    if isinstance(raw_search_items, list):
                        search_items = [
                            item for item in raw_search_items if isinstance(item, dict)
                        ]
            if session_enabled:
                messages_payload = client.get_session_messages(
                    session_id=active_session,
                    workspace_id=workspace_id,
                    limit=session_limit,
                )
                raw_messages = messages_payload.get("items", [])
                if isinstance(raw_messages, list):
                    session_messages = [item for item in raw_messages if isinstance(item, dict)]
        if include_repo:
            repo_context = collect_repo_context(
                repo_query or query,
                repo_root=repo_root,
                snippet_limit=repo_limit,
            )
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    markdown, source_counts = render_unified_context(
        query=query,
        workspace=config.workspace,
        agent=config.agent,
        memory_markdown=str(memory_result.get("markdown") or ""),
        session_messages=session_messages,
        search_items=search_items,
        repo_context=repo_context,
        max_tokens=max_tokens,
    )
    if not any(source_counts.values()):
        info("No context results.")
        raise typer.Exit(EXIT_NO_RESULT)

    typer.echo(markdown, nl=False)
    if memory_result.get("recall_id"):
        info(f"recall_id={memory_result.get('recall_id')}")
    info(
        "source_counts="
        f"memory={source_counts['memory']},"
        f"session={source_counts['session']},"
        f"repo={source_counts['repo']},"
        f"search={source_counts['search']}"
    )
    info(f"token_count={count_tokens(markdown)}")
    raise typer.Exit(EXIT_OK)
