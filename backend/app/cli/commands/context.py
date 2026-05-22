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
)
from ..runtime import resolve_workspace_and_agent


def context(
    query: str = typer.Argument(..., help="Recall query text."),
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    as_of: str | None = typer.Option(None, "--as-of", help="Temporal recall timestamp."),
    limit: int = typer.Option(10, "--limit", min=1, max=50, help="Maximum memories."),
    max_tokens: int = typer.Option(3000, "--max-tokens", min=100, help="Context token budget."),
) -> None:
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
            "as_of": as_of,
            "limit": limit,
            "max_tokens": max_tokens,
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        result = client.context_pack(payload)
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    if int(result.get("result_count", 0)) == 0:
        info("No context results.")
        raise typer.Exit(EXIT_NO_RESULT)

    typer.echo(str(result["markdown"]), nl=False)
    info(f"recall_id={result.get('recall_id')}")
    info(f"token_count={result.get('token_count')}")
    raise typer.Exit(EXIT_OK)
