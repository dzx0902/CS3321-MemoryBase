from __future__ import annotations

from pathlib import Path

import typer

from ..client import MemoryBaseClientError, MemoryBaseServerError, build_client
from ..config import load_config
from ..output import (
    EXIT_CLIENT_ERROR,
    EXIT_NO_RESULT,
    EXIT_OK,
    EXIT_SERVER_ERROR,
    error,
    info,
    validate_format,
    write_result,
)
from ..runtime import resolve_workspace_and_agent


def search(
    query: str = typer.Argument(..., help="Search query text."),
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    scope: str = typer.Option("all", "--scope", help="all, chunks, memories, or sources."),
    limit: int = typer.Option(10, "--limit", min=1, max=50, help="Maximum search items."),
    output_format: str = typer.Option("json", "--format", help="json, markdown, or table."),
    show_lines: bool = typer.Option(
        False,
        "--show-lines",
        help="Render grep-like source_path:start-end snippets.",
    ),
) -> None:
    validate_format(output_format)
    if scope not in {"all", "chunks", "memories", "sources"}:
        error("Unsupported scope. Use all, chunks, memories, or sources.")
        raise typer.Exit(EXIT_CLIENT_ERROR)

    config = load_config(config_path).with_overrides(
        api_base_url=api_base_url,
        workspace=workspace,
        agent=agent,
    )
    try:
        client = build_client(config)
        workspace_id, agent_id = resolve_workspace_and_agent(client, config)
        payload = {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "query_text": query,
            "scope": scope,
            "limit": limit,
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        result = client.search(payload)
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    if int(result.get("result_count", 0)) == 0:
        info(
            f'no results matched query: "{query}" '
            f"(scope={scope}, strategies tried: chunk_fts, memory_fts, "
            "trigram_fuzzy, title_boost)"
        )
        raise typer.Exit(EXIT_NO_RESULT)

    if show_lines:
        typer.echo(format_show_lines(result))
    else:
        write_result(result, output_format=output_format)
    raise typer.Exit(EXIT_OK)


def format_show_lines(result: dict[str, object]) -> str:
    rows = []
    for item in result.get("items", []):
        if not isinstance(item, dict):
            continue
        source = item.get("source_path") or item.get("source_title") or item.get("result_id")
        start_line = item.get("start_line")
        end_line = item.get("end_line")
        if start_line is not None and end_line is not None:
            location = f"{source}:{start_line}-{end_line}"
        else:
            location = str(source)
        snippet = " ".join(str(item.get("snippet") or "").split())
        rows.append(f"{location}: {snippet}")
    return "\n".join(rows)
