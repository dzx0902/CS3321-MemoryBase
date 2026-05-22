from __future__ import annotations

from pathlib import Path

import typer

from ..client import (
    MemoryBaseClientError,
    MemoryBaseServerError,
    build_client,
)
from ..config import default_write_config_path, load_config, write_config
from ..output import (
    EXIT_CLIENT_ERROR,
    EXIT_OK,
    EXIT_SERVER_ERROR,
    error,
    info,
    validate_format,
    write_result,
)


def configure(
    config_path: Path | None = typer.Option(None, "--config", help="Config file to write."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    actor_type: str | None = typer.Option(None, "--actor-type", help="Default actor type."),
    register_agent: str | None = typer.Option(
        None,
        "--register-agent",
        help="Register or reuse an agent name in the configured workspace.",
    ),
    agent_type: str = typer.Option("editor", "--type", help="Agent type when registering."),
    output_format: str = typer.Option(
        "table",
        "--format",
        help="Output format: json, markdown, or table.",
    ),
) -> None:
    validate_format(output_format)
    current = load_config(config_path)
    updated = current.with_overrides(
        api_base_url=api_base_url,
        workspace=workspace,
        agent=agent,
        actor_type=actor_type,
    )
    registered: dict[str, object] | None = None

    if register_agent:
        if not updated.workspace:
            error("--register-agent requires --workspace or an existing workspace config.")
            raise typer.Exit(EXIT_CLIENT_ERROR)
        try:
            client = build_client(updated)
            registered = client.register_agent(
                workspace=updated.workspace,
                name=register_agent,
                agent_type=agent_type,
            )
        except MemoryBaseClientError as exc:
            error(str(exc))
            raise typer.Exit(EXIT_CLIENT_ERROR) from exc
        except MemoryBaseServerError as exc:
            error(str(exc))
            raise typer.Exit(EXIT_SERVER_ERROR) from exc
        updated = updated.with_overrides(agent=register_agent)
        info(f"Registered agent {register_agent}: {registered['agent_id']}")

    target = default_write_config_path(config_path)
    write_config(updated, target)
    info(f"Wrote MemoryBase config: {target}")
    if output_format != "table":
        write_result(
            {
                "config_path": str(target),
                "api_base_url": updated.api_base_url,
                "workspace": updated.workspace,
                "agent": updated.agent,
                "actor_type": updated.actor_type,
                "registered_agent": registered,
            },
            output_format=output_format,
        )
    raise typer.Exit(EXIT_OK)
