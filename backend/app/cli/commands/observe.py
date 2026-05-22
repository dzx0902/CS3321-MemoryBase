from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

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


def observe(
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    session_id: str | None = typer.Option(None, "--session", help="Session UUID."),
    role: str = typer.Option("user", "--role", help="Message role."),
    content: str | None = typer.Option(None, "--content", help="Message content."),
    sender_type: str = typer.Option("user", "--sender-type", help="user, agent, or system."),
    sender_id: str | None = typer.Option(None, "--sender-id", help="Sender UUID."),
    batch_path: Path | None = typer.Option(
        None, "--batch", help="JSONL batch file, or '-' for stdin."
    ),
    output_format: str = typer.Option("json", "--format", help="json, markdown, or table."),
) -> None:
    validate_format(output_format)
    if not session_id:
        error("--session is required.")
        raise typer.Exit(EXIT_CLIENT_ERROR)

    config = load_config(config_path).with_overrides(api_base_url=api_base_url)
    try:
        client = build_client(config)
        if batch_path is not None:
            messages = read_jsonl_messages(batch_path, default_session_id=session_id)
            result = client.observe_batch({"messages": messages})
        else:
            if not content:
                error("--content is required unless --batch is used.")
                raise typer.Exit(EXIT_CLIENT_ERROR)
            result = client.observe_message(
                {
                    "session_id": session_id,
                    "sender_type": sender_type,
                    "sender_id": sender_id,
                    "role": role,
                    "content": content,
                }
            )
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc
    except (OSError, ValueError) as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc

    write_result(result, output_format=output_format)
    raise typer.Exit(EXIT_OK)


def read_jsonl_messages(path: Path, *, default_session_id: str) -> list[dict[str, Any]]:
    raw_lines = sys.stdin.read().splitlines() if str(path) == "-" else path.read_text().splitlines()
    messages: list[dict[str, Any]] = []
    for line_no, line in enumerate(raw_lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_no}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL line {line_no} must be an object")
        payload.setdefault("session_id", default_session_id)
        payload.setdefault("sender_type", "user")
        messages.append(payload)
    if not messages:
        raise ValueError("batch file did not contain any messages")
    return messages
