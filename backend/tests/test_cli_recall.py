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

    def context_pack(self, payload):
        return {
            "recall_id": str(uuid4()),
            "result_count": 1,
            "token_count": 42,
            "markdown": "# MemoryBase Context\n\n## Relevant Memories\n- [M1] decision",
            "citation_map": {"memories": {"M1": {"memory_type": "decision"}}},
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


def test_cli_context_outputs_markdown_to_stdout(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cli.commands.context.build_client",
        lambda *args, **kwargs: FakeRecallClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["context", "为什么放弃食堂", "--workspace", "cs3321-demo", "--max-tokens", "500"],
    )

    assert result.exit_code == 0
    assert result.stdout.startswith("# MemoryBase Context")
    assert "recall_id=" in result.stderr
    assert "token_count=42" in result.stderr


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
    assert result.stdout == ""
    assert "No recall results" in result.stderr


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
