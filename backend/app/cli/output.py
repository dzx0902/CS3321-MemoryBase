from __future__ import annotations

import json
from typing import Any

import typer

EXIT_OK = 0
EXIT_CLIENT_ERROR = 2
EXIT_SERVER_ERROR = 3
EXIT_NO_RESULT = 4

SUPPORTED_FORMATS = {"json", "markdown", "table"}


def validate_format(output_format: str) -> str:
    if output_format not in SUPPORTED_FORMATS:
        error(f"Unsupported format: {output_format}. Use json, markdown, or table.")
        raise typer.Exit(EXIT_CLIENT_ERROR)
    return output_format


def write_result(payload: Any, *, output_format: str) -> None:
    validate_format(output_format)
    if output_format == "json":
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if output_format == "markdown":
        typer.echo(format_markdown(payload))
        return
    typer.echo(format_table(payload))


def info(message: str) -> None:
    typer.echo(message, err=True)


def error(message: str) -> None:
    typer.echo(f"ERROR: {message}", err=True)


def format_markdown(payload: Any) -> str:
    if isinstance(payload, dict):
        lines = ["# MemoryBase Result", ""]
        for key, value in payload.items():
            lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)
    return str(payload)


def format_table(payload: Any) -> str:
    if not isinstance(payload, dict):
        return str(payload)
    return "\n".join(f"{key}\t{value}" for key, value in payload.items())
