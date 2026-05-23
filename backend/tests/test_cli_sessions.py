from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.cli.main import app
from typer.testing import CliRunner


class FakeSessionsClient:
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

    def create_session(self, payload):
        return {
            "session_id": str(uuid4()),
            "workspace_id": payload["workspace_id"],
            "agent_id": payload.get("agent_id"),
            "started_by_user_id": None,
            "title": payload["title"],
            "channel": payload["channel"],
            "started_at": "2026-05-22T00:00:00Z",
            "ended_at": None,
        }


def test_cli_sessions_create_outputs_session_id(monkeypatch, tmp_path: Path) -> None:
    fake = FakeSessionsClient()
    monkeypatch.setattr("app.cli.commands.sessions.build_client", lambda *args, **kwargs: fake)
    runner = CliRunner()
    config_path = tmp_path / "config.toml"

    result = runner.invoke(
        app,
        [
            "sessions",
            "create",
            "--config",
            str(config_path),
            "--workspace",
            "cs3321-demo",
            "--agent",
            "codex",
            "--title",
            "PR3",
            "--no-set-active",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["channel"] == "cli"
    assert payload["agent_id"] == str(fake.agent_id)


def test_cli_sessions_create_can_print_plain_session_id_and_set_active(
    monkeypatch, tmp_path: Path
) -> None:
    fake = FakeSessionsClient()
    monkeypatch.setattr("app.cli.commands.sessions.build_client", lambda *args, **kwargs: fake)
    runner = CliRunner()
    config_path = tmp_path / "config.toml"

    result = runner.invoke(
        app,
        [
            "sessions",
            "create",
            "--config",
            str(config_path),
            "--workspace",
            "cs3321-demo",
            "--agent",
            "codex",
            "--title",
            "PR5",
            "--print",
            "session_id",
        ],
    )

    assert result.exit_code == 0
    session_id = result.stdout.strip()
    assert session_id
    assert "\n" not in session_id
    assert f'active_session = "{session_id}"' in config_path.read_text(encoding="utf-8")
