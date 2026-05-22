from __future__ import annotations

import json
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
from ..runtime import resolve_workspace_and_agent

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_GOLD_PATH = PROJECT_ROOT / "data" / "eval" / "recall_gold.json"

app = typer.Typer(help="Evaluation commands.", no_args_is_help=True)


@app.command("recall")
def eval_recall(
    gold_path: Path = typer.Option(DEFAULT_GOLD_PATH, "--gold", help="Recall gold set JSON."),
    config_path: Path | None = typer.Option(None, "--config", help="Config file to read."),
    api_base_url: str | None = typer.Option(None, "--api-base", help="MemoryBase API base URL."),
    workspace: str | None = typer.Option(
        None, "--workspace", help="Default workspace slug or UUID."
    ),
    agent: str | None = typer.Option(None, "--agent", help="Default agent name or UUID."),
    limit: int = typer.Option(5, "--limit", min=1, max=50, help="Recall limit per question."),
    output_format: str = typer.Option("table", "--format", help="json, markdown, or table."),
) -> None:
    validate_format(output_format)
    config = load_config(config_path).with_overrides(
        api_base_url=api_base_url,
        workspace=workspace,
        agent=agent,
    )
    try:
        questions = load_gold_set(gold_path)
        client = build_client(config)
        results = [evaluate_question(question, client, config, limit) for question in questions]
    except (MemoryBaseClientError, ValueError, OSError) as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    memory_hits = sum(1 for result in results if result["memory_hit"])
    source_hits = sum(1 for result in results if result["source_hit"])
    question_count = len(results)
    summary = {
        "question_count": question_count,
        "memory_hits": memory_hits,
        "source_hits": source_hits,
        "memory_hit_rate": memory_hits / question_count if question_count else 0,
        "source_hit_rate": source_hits / question_count if question_count else 0,
        "results": results,
    }
    write_result(summary, output_format=output_format)
    raise typer.Exit(EXIT_OK)


def load_gold_set(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Recall gold set must contain a JSON array.")
    return [validate_gold_question(item) for item in raw]


def validate_gold_question(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Each recall gold item must be an object.")
    query = item.get("query")
    workspace = item.get("workspace")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Recall gold item requires a non-empty query.")
    if workspace is not None and (not isinstance(workspace, str) or not workspace.strip()):
        raise ValueError("Recall gold workspace must be a non-empty string when provided.")
    return {
        "query": query,
        "workspace": workspace,
        "expected_canonical_text_substrings": list(
            item.get("expected_canonical_text_substrings", [])
        ),
        "expected_source_titles": list(item.get("expected_source_titles", [])),
    }


def evaluate_question(
    question: dict[str, Any],
    client,
    config,
    limit: int,
) -> dict[str, Any]:
    question_config = config.with_overrides(workspace=question.get("workspace"))
    workspace_id, agent_id = resolve_workspace_and_agent(client, question_config)
    recall = client.recall(
        {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "query_text": question["query"],
            "limit": limit,
        }
    )
    memory_text = "\n".join(
        str(memory.get("canonical_text", "")) for memory in recall.get("memories", [])
    )
    source_titles = {
        str(evidence.get("source_title", ""))
        for memory in recall.get("memories", [])
        for evidence in memory.get("evidence", [])
        if isinstance(evidence, dict)
    }
    expected_memory = question["expected_canonical_text_substrings"]
    expected_sources = question["expected_source_titles"]
    return {
        "query": question["query"],
        "result_count": recall.get("result_count", 0),
        "memory_hit": any(expected in memory_text for expected in expected_memory)
        if expected_memory
        else False,
        "source_hit": any(
            expected in source
            for expected in expected_sources
            for source in source_titles
        )
        if expected_sources
        else False,
    }
