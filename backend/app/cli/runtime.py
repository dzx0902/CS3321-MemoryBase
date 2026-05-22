from __future__ import annotations

from typing import Any

import typer

from .client import MemoryBaseClient
from .config import CliConfig
from .output import EXIT_CLIENT_ERROR, error


def resolve_workspace_and_agent(
    client: MemoryBaseClient,
    config: CliConfig,
) -> tuple[str, str | None]:
    if not config.workspace:
        error("Workspace is required. Use --workspace or run mb configure.")
        raise typer.Exit(EXIT_CLIENT_ERROR)

    health = client.health_detail(workspace=config.workspace, agent=config.agent)
    workspace = checked_target(health, "workspace")
    agent = checked_target(health, "agent") if config.agent else None
    return str(workspace["workspace_id"]), str(agent["agent_id"]) if agent else None


def checked_target(payload: dict[str, Any], key: str) -> dict[str, Any]:
    target = payload.get(key)
    if not isinstance(target, dict) or not target.get("found", False):
        reason = target.get("error") if isinstance(target, dict) else f"{key} not found"
        error(str(reason))
        raise typer.Exit(EXIT_CLIENT_ERROR)
    return target
