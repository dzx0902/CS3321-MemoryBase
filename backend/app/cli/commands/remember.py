from __future__ import annotations

from pathlib import Path
from uuid import UUID

import typer

from ..client import MemoryBaseClientError, MemoryBaseServerError, build_client
from ..config import load_config
from ..output import (
    EXIT_CLIENT_ERROR,
    EXIT_OK,
    EXIT_SERVER_ERROR,
    error,
    validate_format,
    write_result,
)
from ..runtime import resolve_workspace_and_agent


def remember(
    text: str = typer.Argument(..., help="Memory canonical text."),
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    memory_type: str = typer.Option("semantic", "--type", help="Memory type."),
    summary: str | None = typer.Option(None, "--summary", help="Memory summary."),
    confidence: float = typer.Option(0.7, "--confidence", min=0, max=1),
    importance: int = typer.Option(3, "--importance", min=1, max=5),
    access_level: str = typer.Option("project", "--access-level", help="Memory access level."),
    evidence_chunks: list[UUID] | None = typer.Option(
        None,
        "--evidence",
        help="Existing source chunk UUID. Repeat for multiple chunks.",
    ),
    reason: str | None = typer.Option(None, "--reason", help="Revision reason. Required."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview payload without writing."),
    commit: bool = typer.Option(False, "--commit", help="Persist the memory. Default is dry run."),
    output_format: str = typer.Option("json", "--format", help="json, markdown, or table."),
) -> None:
    validate_format(output_format)
    if not reason:
        error("--reason is required for mb remember.")
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
            "memory_type": memory_type,
            "canonical_text": text,
            "summary": summary,
            "confidence": confidence,
            "importance": importance,
            "access_level": access_level,
            "owner_agent_id": agent_id,
            "evidence": [
                {
                    "chunk_id": str(chunk_id),
                    "evidence_role": "supports",
                    "weight": 1.0,
                    "note": "Provided through mb remember --evidence.",
                }
                for chunk_id in (evidence_chunks or [])
            ],
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        if dry_run and commit:
            error("--dry-run and --commit cannot be used together.")
            raise typer.Exit(EXIT_CLIENT_ERROR)
        if not commit:
            write_result({"dry_run": True, "payload": payload}, output_format=output_format)
            raise typer.Exit(EXIT_OK)
        result = client.create_memory(
            payload,
            actor_type="agent",
            actor_id=agent_id,
            reason=reason,
        )
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    write_result(result, output_format=output_format)
    raise typer.Exit(EXIT_OK)
