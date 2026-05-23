from __future__ import annotations

from pathlib import Path

import typer

from ..client import MemoryBaseClientError, MemoryBaseServerError, build_client
from ..config import default_write_config_path, load_config, write_config
from ..output import (
    EXIT_CLIENT_ERROR,
    EXIT_OK,
    EXIT_SERVER_ERROR,
    error,
    validate_format,
    write_result,
)
from ..runtime import resolve_workspace_and_agent

app = typer.Typer(help="Agent session commands.", no_args_is_help=True)


@app.command("create")
def create_session(
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    title: str = typer.Option(..., "--title", help="Session title."),
    channel: str = typer.Option("cli", "--channel", help="Session channel."),
    print_field: str | None = typer.Option(
        None,
        "--print",
        help="Print one response field only, for example session_id.",
    ),
    set_active: bool = typer.Option(
        True,
        "--set-active/--no-set-active",
        help="Write session_id to config.",
    ),
    output_format: str = typer.Option("json", "--format", help="json, markdown, or table."),
) -> None:
    validate_format(output_format)
    config = load_config(config_path).with_overrides(
        api_base_url=api_base_url,
        workspace=workspace,
        agent=agent,
    )
    try:
        client = build_client(config)
        workspace_id, agent_id = resolve_workspace_and_agent(client, config)
        result = client.create_session(
            {
                "workspace_id": workspace_id,
                "agent_id": agent_id,
                "title": title,
                "channel": channel,
            }
        )
        if set_active:
            target = default_write_config_path(config_path)
            write_config(config.with_overrides(active_session=str(result["session_id"])), target)
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    if print_field:
        if print_field not in result:
            error(f"Unknown response field for --print: {print_field}")
            raise typer.Exit(EXIT_CLIENT_ERROR)
        typer.echo(str(result[print_field]))
        raise typer.Exit(EXIT_OK)
    write_result(result, output_format=output_format)
    raise typer.Exit(EXIT_OK)
