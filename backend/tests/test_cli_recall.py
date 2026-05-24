from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.cli.main import app
from typer.testing import CliRunner


class FakeRecallClient:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.agent_id = uuid4()

    def health_detail(self, *, workspace: str | None = None, agent: str | None = None):
        return {
            "status": "ok",
            "workspace": {
                "found": True,
                "workspace_id": str(self.workspace_id),
                "slug": workspace,
            },
            "agent": {
                "found": True,
                "agent_id": str(self.agent_id),
                "name": agent,
            }
            if agent
            else None,
        }

    def recall(self, payload):
        return {
            "recall_id": str(uuid4()),
            "workspace_id": payload["workspace_id"],
            "query_text": payload["query_text"],
            "result_count": 1,
            "memories": [
                {
                    "memory_id": str(uuid4()),
                    "canonical_text": "The cafeteria system was too CRUD-heavy.",
                    "evidence": [
                        {
                            "source_title": "Discussion 01",
                            "chunk_text": "Cafeteria was too CRUD-heavy.",
                        }
                    ],
                }
            ],
            "context_pack": {},
        }

    def search(self, payload):
        return {
            "workspace_id": payload["workspace_id"],
            "query_text": payload["query_text"],
            "tokenized_query": "cafeteria system",
            "result_count": 1,
            "items": [
                {
                    "result_type": "chunk",
                    "result_id": str(uuid4()),
                    "doc_id": str(uuid4()),
                    "source_path": "data/raw_sources/demo_workspace/discussion_01_project_pivot.md",
                    "source_title": "Discussion 01: Project Pivot",
                    "start_line": 8,
                    "end_line": 12,
                    "snippet": "The cafeteria system was too CRUD-heavy.",
                    "score": 0.031,
                    "strategies": ["chunk_fts", "trigram_fuzzy"],
                }
            ],
        }


def test_cli_recall_defaults_to_json(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cli.commands.recall.build_client",
        lambda *args, **kwargs: FakeRecallClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["recall", "为什么放弃食堂", "--workspace", "cs3321-demo", "--agent", "codex"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["result_count"] == 1
    assert payload["memories"][0]["canonical_text"].endswith("CRUD-heavy.")


def test_cli_recall_returns_no_result_exit_code(monkeypatch) -> None:
    class EmptyClient(FakeRecallClient):
        def recall(self, payload):
            data = super().recall(payload)
            data["result_count"] = 0
            data["memories"] = []
            return data

    monkeypatch.setattr(
        "app.cli.commands.recall.build_client",
        lambda *args, **kwargs: EmptyClient(),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["recall", "missing", "--workspace", "cs3321-demo"])

    assert result.exit_code == 4
    payload = json.loads(result.stdout)
    assert payload["result_count"] == 0
    assert payload["memories"] == []
    assert "No recall results" in result.stderr


def test_cli_search_defaults_to_json(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cli.commands.search.build_client",
        lambda *args, **kwargs: FakeRecallClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["search", "cafeteria system", "--workspace", "cs3321-demo", "--agent", "codex"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["result_count"] == 1
    assert payload["items"][0]["strategies"] == ["chunk_fts", "trigram_fuzzy"]


def test_cli_search_show_lines_outputs_grep_like_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cli.commands.search.build_client",
        lambda *args, **kwargs: FakeRecallClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["search", "cafeteria system", "--workspace", "cs3321-demo", "--show-lines"],
    )

    assert result.exit_code == 0
    assert result.stdout.startswith(
        "data/raw_sources/demo_workspace/discussion_01_project_pivot.md:8-12:"
    )
    assert "CRUD-heavy" in result.stdout


def test_cli_search_returns_no_result_exit_code(monkeypatch) -> None:
    class EmptyClient(FakeRecallClient):
        def search(self, payload):
            data = super().search(payload)
            data["result_count"] = 0
            data["items"] = []
            return data

    monkeypatch.setattr(
        "app.cli.commands.search.build_client",
        lambda *args, **kwargs: EmptyClient(),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["search", "missing", "--workspace", "cs3321-demo"])

    assert result.exit_code == 4
    assert result.stdout == ""
    assert 'no results matched query: "missing"' in result.stderr


def test_cli_eval_recall_outputs_metrics(tmp_path: Path, monkeypatch) -> None:
    gold_path = tmp_path / "gold.json"
    gold_path.write_text(
        json.dumps(
            [
                {
                    "query": "why cafeteria",
                    "workspace": "cs3321-demo",
                    "expected_canonical_text_substrings": ["CRUD-heavy"],
                    "expected_source_titles": ["Discussion 01"],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.cli.commands.eval.build_client",
        lambda *args, **kwargs: FakeRecallClient(),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["eval", "recall", "--gold", str(gold_path), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["question_count"] == 1
    assert payload["memory_hit_rate"] == 1.0
    assert payload["source_hit_rate"] == 1.0


def test_cli_eval_recall_can_run_search_gold(tmp_path: Path, monkeypatch) -> None:
    gold_path = tmp_path / "search_gold.json"
    gold_path.write_text(
        json.dumps(
            [
                {
                    "category": "typo_fuzzy",
                    "query": "cafeteria systm",
                    "workspace": "cs3321-demo",
                    "expected_text_substrings": ["CRUD-heavy"],
                    "expected_source_titles": ["Discussion 01"],
                    "expected_strategy": "trigram_fuzzy",
                    "required_for_pr4_pass": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "app.cli.commands.eval.build_client",
        lambda *args, **kwargs: FakeRecallClient(),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["eval", "recall", "--gold", str(gold_path), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["question_count"] == 1
    assert payload["required_hit_rate"] == 1.0
    assert payload["strategy_hit_rate"] == 1.0
