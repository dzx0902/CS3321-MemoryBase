from __future__ import annotations

import os
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

EXTRACTION_METHODS = {"rule_based", "llm"}


def extract(
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or UUID."),
    agent: str | None = typer.Option(None, "--agent", help="Agent name or UUID."),
    chunk_ids: list[UUID] | None = typer.Option(
        None,
        "--chunk",
        help="Source chunk UUID. Repeat for multiple chunks.",
    ),
    max_candidates: int = typer.Option(10, "--max-candidates", min=1, max=50),
    method: str = typer.Option("rule_based", "--method", help="rule_based or llm."),
    llm_api_key: str | None = typer.Option(
        None,
        "--llm-api-key",
        help="LLM API key. Defaults to LLM_ANALYSIS_API_KEY or OPENAI_API_KEY.",
    ),
    llm_base_url: str | None = typer.Option(
        None,
        "--llm-base-url",
        help="OpenAI-compatible base URL.",
    ),
    llm_model: str | None = typer.Option(None, "--llm-model", help="LLM model name."),
    llm_provider: str | None = typer.Option(
        None,
        "--llm-provider",
        help="Provider label stored in run audit metadata.",
    ),
    output_format: str = typer.Option("json", "--format", help="json, markdown, or table."),
) -> None:
    validate_format(output_format)
    if method not in EXTRACTION_METHODS:
        error("Unsupported extraction method. Use rule_based or llm.")
        raise typer.Exit(EXIT_CLIENT_ERROR)
    if not chunk_ids:
        error("At least one --chunk is required.")
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
            "chunk_ids": [str(chunk_id) for chunk_id in chunk_ids],
            "max_candidates": max_candidates,
            "method": method,
        }
        if method == "llm":
            payload["llm"] = {
                "api_key": llm_api_key
                or os.getenv("LLM_ANALYSIS_API_KEY")
                or os.getenv("OPENAI_API_KEY"),
                "base_url": llm_base_url,
                "model": llm_model,
                "provider": llm_provider,
            }
            payload["llm"] = {
                key: value for key, value in payload["llm"].items() if value is not None
            }
        result = client.extract_candidates(
            payload,
            actor_type=config.actor_type,
            actor_id=config.actor_id or agent_id,
        )
    except MemoryBaseClientError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    write_result(result, output_format=output_format)
    raise typer.Exit(EXIT_OK)
