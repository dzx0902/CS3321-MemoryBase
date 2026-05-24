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
DEFAULT_RECALL_GOLD_PATH = PROJECT_ROOT / "data" / "eval" / "recall_gold.json"
DEFAULT_SEARCH_GOLD_PATH = PROJECT_ROOT / "data" / "eval" / "search_adversarial_gold.json"

app = typer.Typer(help="Evaluation commands.", no_args_is_help=True)


@app.command("recall")
def eval_recall(
    gold: str = typer.Option(
        "recall",
        "--gold",
        help="recall, search, all, or a recall/search gold JSON path.",
    ),
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
        client = build_client(config)
        summary = evaluate_gold(gold, client, config, limit)
    except (MemoryBaseClientError, ValueError, OSError) as exc:
        error(str(exc))
        raise typer.Exit(EXIT_CLIENT_ERROR) from exc
    except MemoryBaseServerError as exc:
        error(str(exc))
        raise typer.Exit(EXIT_SERVER_ERROR) from exc

    write_result(summary, output_format=output_format)
    raise typer.Exit(EXIT_OK)


def evaluate_gold(gold: str, client, config, limit: int) -> dict[str, Any]:
    if gold == "recall":
        return evaluate_recall_gold(DEFAULT_RECALL_GOLD_PATH, client, config, limit)
    if gold == "search":
        return evaluate_search_gold(DEFAULT_SEARCH_GOLD_PATH, client, config, limit)
    if gold == "all":
        return {
            "recall": evaluate_recall_gold(DEFAULT_RECALL_GOLD_PATH, client, config, limit),
            "search": evaluate_search_gold(DEFAULT_SEARCH_GOLD_PATH, client, config, limit),
        }

    path = Path(gold)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if _looks_like_search_gold(raw):
        return evaluate_search_questions(
            [validate_search_gold_question(item) for item in raw],
            client,
            config,
            limit,
        )
    return evaluate_recall_gold(path, client, config, limit)


def evaluate_recall_gold(path: Path, client, config, limit: int) -> dict[str, Any]:
    questions = load_gold_set(path)
    results = [evaluate_question(question, client, config, limit) for question in questions]
    memory_hits = sum(1 for result in results if result["memory_hit"])
    source_hits = sum(1 for result in results if result["source_hit"])
    question_count = len(results)
    return {
        "question_count": question_count,
        "memory_hits": memory_hits,
        "source_hits": source_hits,
        "memory_hit_rate": memory_hits / question_count if question_count else 0,
        "source_hit_rate": source_hits / question_count if question_count else 0,
        "results": results,
    }


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


def evaluate_search_gold(path: Path, client, config, limit: int) -> dict[str, Any]:
    questions = load_search_gold_set(path)
    return evaluate_search_questions(questions, client, config, limit)


def load_search_gold_set(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Search gold set must contain a JSON array.")
    return [validate_search_gold_question(item) for item in raw]


def validate_search_gold_question(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("Each search gold item must be an object.")
    query = item.get("query")
    workspace = item.get("workspace")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search gold item requires a non-empty query.")
    if workspace is not None and (not isinstance(workspace, str) or not workspace.strip()):
        raise ValueError("Search gold workspace must be a non-empty string when provided.")
    return {
        "category": str(item.get("category", "uncategorized")),
        "query": query,
        "workspace": workspace,
        "scope": item.get("scope", "all"),
        "expected_text_substrings": list(item.get("expected_text_substrings", [])),
        "expected_source_titles": list(item.get("expected_source_titles", [])),
        "expected_strategy": str(item.get("expected_strategy", "")),
        "required_for_pr4_pass": bool(item.get("required_for_pr4_pass", True)),
    }


def evaluate_search_questions(
    questions: list[dict[str, Any]],
    client,
    config,
    limit: int,
) -> dict[str, Any]:
    results = [evaluate_search_question(question, client, config, limit) for question in questions]
    required_results = [result for result in results if result["required"]]
    result_hits = sum(1 for result in results if result["result_hit"])
    required_hits = sum(1 for result in required_results if result["result_hit"])
    strategy_hits = sum(1 for result in results if result["strategy_hit"])
    question_count = len(results)
    required_count = len(required_results)
    return {
        "question_count": question_count,
        "required_question_count": required_count,
        "result_hits": result_hits,
        "required_hits": required_hits,
        "strategy_hits": strategy_hits,
        "result_hit_rate": result_hits / question_count if question_count else 0,
        "required_hit_rate": required_hits / required_count if required_count else 0,
        "strategy_hit_rate": strategy_hits / question_count if question_count else 0,
        "results": results,
    }


def evaluate_search_question(
    question: dict[str, Any],
    client,
    config,
    limit: int,
) -> dict[str, Any]:
    question_config = config.with_overrides(workspace=question.get("workspace"))
    workspace_id, agent_id = resolve_workspace_and_agent(client, question_config)
    search = client.search(
        {
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "query_text": question["query"],
            "scope": question["scope"],
            "limit": limit,
        }
    )
    items = [item for item in search.get("items", []) if isinstance(item, dict)]
    combined_text = "\n".join(
        " ".join(
            str(item.get(key, ""))
            for key in ("snippet", "source_title", "source_path", "result_type")
        )
        for item in items
    )
    source_titles = {str(item.get("source_title", "")) for item in items}
    strategies = {
        str(strategy)
        for item in items
        for strategy in item.get("strategies", [])
        if isinstance(item.get("strategies", []), list)
    }
    expected_texts = question["expected_text_substrings"]
    expected_sources = question["expected_source_titles"]
    text_hit = (
        any(expected in combined_text for expected in expected_texts)
        if expected_texts
        else True
    )
    source_hit = (
        any(expected in source for expected in expected_sources for source in source_titles)
        if expected_sources
        else True
    )
    expected_strategy = question["expected_strategy"]
    strategy_hit = (
        expected_strategy in strategies
        if expected_strategy and expected_strategy != "needs_embedding_or_dict"
        else False
    )
    return {
        "category": question["category"],
        "query": question["query"],
        "required": question["required_for_pr4_pass"],
        "result_count": search.get("result_count", 0),
        "result_hit": text_hit and source_hit,
        "strategy_hit": strategy_hit,
        "expected_strategy": expected_strategy,
        "strategies": sorted(strategies),
    }


def _looks_like_search_gold(raw: Any) -> bool:
    return (
        isinstance(raw, list)
        and bool(raw)
        and isinstance(raw[0], dict)
        and (
            "expected_text_substrings" in raw[0]
            or "expected_strategy" in raw[0]
            or "required_for_pr4_pass" in raw[0]
        )
    )
