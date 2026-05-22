from __future__ import annotations

from pathlib import Path

import typer

from ..client import MemoryBaseClientError, MemoryBaseServerError, build_client
from ..config import load_config
from ..output import (
    EXIT_CLIENT_ERROR,
    EXIT_OK,
    EXIT_SERVER_ERROR,
    error,
    info,
    validate_format,
    write_result,
)


def health(
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    output_format: str = typer.Option("table", "--format", help="json, markdown, or table."),
    local: bool = typer.Option(False, "--local", help="Use local service imports instead of HTTP."),
) -> None:
    validate_format(output_format)
    config = load_config(config_path).with_overrides(
        api_base_url=api_base_url,
        workspace=workspace,
        agent=agent,
    )

    try:
        client = build_client(config, local=local)
        payload = client.health_detail(workspace=config.workspace, agent=config.agent)
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    status = str(payload.get("status", "degraded"))
    info(f"MemoryBase health: {status}")
    if status != "ok":
        raise typer.Exit(EXIT_SERVER_ERROR)

    resolution_error = unresolved_target_error(payload, "workspace") or unresolved_target_error(
        payload, "agent"
    )
    if resolution_error is not None:
        error(resolution_error)
        raise typer.Exit(EXIT_CLIENT_ERROR)

    write_result(payload, output_format=output_format)
    raise typer.Exit(EXIT_OK)


def unresolved_target_error(payload: dict[str, object], key: str) -> str | None:
    target = payload.get(key)
    if not isinstance(target, dict):
        return None
    if target.get("found", True):
        return None
    return str(target.get("error") or f"{key} not found")
