from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.cli.main import app
from typer.testing import CliRunner


class FakeWritebackClient:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.agent_id = uuid4()
        self.created_memories: list[dict[str, object]] = []
        self.observed_batches: list[list[dict[str, object]]] = []

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

    def observe_message(self, payload):
        return {
            "message_id": str(uuid4()),
            **payload,
            "created_at": "2026-05-22T00:00:00Z",
            "reply_to_message_id": payload.get("reply_to_message_id"),
        }

    def observe_batch(self, payload):
        self.observed_batches.append(payload["messages"])
        return {"items": [self.observe_message(item) for item in payload["messages"]], "total": 2}

    def create_memory(self, payload, *, actor_type: str, actor_id: str | None, reason: str):
        self.created_memories.append(payload)
        return {
            "memory_id": str(uuid4()),
            "workspace_id": payload["workspace_id"],
            "created_from_doc_id": None,
            "memory_type": payload["memory_type"],
            "canonical_text": payload["canonical_text"],
            "summary": payload.get("summary"),
            "confidence": payload["confidence"],
            "importance": payload["importance"],
            "status": "active",
            "access_level": payload["access_level"],
            "current_revision_no": 1,
            "created_at": "2026-05-22T00:00:00Z",
            "updated_at": "2026-05-22T00:00:00Z",
            "evidence_count": len(payload["evidence"]) or 1,
        }


def test_cli_observe_single_and_batch(monkeypatch, tmp_path: Path) -> None:
    fake = FakeWritebackClient()
    monkeypatch.setattr("app.cli.commands.observe.build_client", lambda *args, **kwargs: fake)
    runner = CliRunner()
    session_id = str(uuid4())

    single = runner.invoke(
        app,
        [
            "observe",
            "--session",
            session_id,
            "--role",
            "assistant",
            "--content",
            "remember this",
        ],
    )
    assert single.exit_code == 0
    payload = json.loads(single.stdout)
    assert payload["content"] == "remember this"
    assert payload["sender_type"] == "agent"

    batch_path = tmp_path / "messages.jsonl"
    batch_path.write_text(
        "\n".join(
            [
                json.dumps({"role": "user", "content": "hello"}),
                json.dumps({"role": "assistant", "content": "world", "sender_type": "agent"}),
            ]
        ),
        encoding="utf-8",
    )
    batch = runner.invoke(app, ["observe", "--session", session_id, "--batch", str(batch_path)])

    assert batch.exit_code == 0
    assert len(fake.observed_batches[0]) == 2
    assert all(item["session_id"] == session_id for item in fake.observed_batches[0])


def test_cli_observe_quiet_outputs_only_message_id(monkeypatch) -> None:
    fake = FakeWritebackClient()
    monkeypatch.setattr("app.cli.commands.observe.build_client", lambda *args, **kwargs: fake)
    runner = CliRunner()
    session_id = str(uuid4())

    result = runner.invoke(
        app,
        [
            "observe",
            "--session",
            session_id,
            "--role",
            "assistant",
            "--content",
            "quiet please",
            "--quiet",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.strip()
    assert "\n" not in result.stdout.strip()


def test_cli_remember_defaults_to_dry_run_and_requires_reason(monkeypatch) -> None:
    fake = FakeWritebackClient()
    monkeypatch.setattr("app.cli.commands.remember.build_client", lambda *args, **kwargs: fake)
    runner = CliRunner()

    missing_reason = runner.invoke(
        app,
        ["remember", "MemoryBase prefers CLI runtime.", "--workspace", "cs3321-demo"],
    )
    assert missing_reason.exit_code == 2
    assert "reason is required" in missing_reason.stderr

    dry_run = runner.invoke(
        app,
        [
            "remember",
            "MemoryBase prefers CLI runtime.",
            "--workspace",
            "cs3321-demo",
            "--agent",
            "codex",
            "--type",
            "decision",
            "--reason",
            "test",
            "--dry-run",
        ],
    )
    assert dry_run.exit_code == 0
    assert json.loads(dry_run.stdout)["dry_run"] is True
    assert "Dry run only" in dry_run.stderr
    assert fake.created_memories == []


def test_cli_remember_rejects_unknown_memory_type_before_api_call(monkeypatch) -> None:
    fake = FakeWritebackClient()
    monkeypatch.setattr("app.cli.commands.remember.build_client", lambda *args, **kwargs: fake)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "remember",
            "MemoryBase prefers explicit memory types.",
            "--workspace",
            "cs3321-demo",
            "--agent",
            "codex",
            "--type",
            "rule",
            "--reason",
            "test",
            "--commit",
        ],
    )

    assert result.exit_code == 2
    assert "Unsupported memory type: rule" in result.stderr
    assert "decision" in result.stderr
    assert fake.created_memories == []


def test_cli_remember_help_lists_supported_memory_types() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["remember", "--help"])

    assert result.exit_code == 0
    for memory_type in (
        "episodic",
        "semantic",
        "fact",
        "profile",
        "procedural",
        "decision",
        "preference",
        "task",
        "risk",
        "constraint",
        "policy",
        "summary",
    ):
        assert memory_type in result.stdout


def test_cli_remember_commit_writes_memory(monkeypatch) -> None:
    fake = FakeWritebackClient()
    monkeypatch.setattr("app.cli.commands.remember.build_client", lambda *args, **kwargs: fake)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "remember",
            "MemoryBase prefers CLI runtime.",
            "--workspace",
            "cs3321-demo",
            "--agent",
            "codex",
            "--type",
            "decision",
            "--reason",
            "test",
            "--commit",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["memory_type"] == "decision"
    assert fake.created_memories[0]["owner_agent_id"] == str(fake.agent_id)
