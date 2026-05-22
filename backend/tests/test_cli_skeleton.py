from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.cli.main import app
from typer.testing import CliRunner


def test_configure_writes_config_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "configure",
            "--config",
            str(config_path),
            "--api-base",
            "http://localhost:8000",
            "--workspace",
            "cs3321-demo",
            "--agent",
            "codex",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout == ""
    assert "Wrote MemoryBase config" in result.stderr
    content = config_path.read_text(encoding="utf-8")
    assert 'api_base_url = "http://localhost:8000"' in content
    assert 'workspace = "cs3321-demo"' in content
    assert 'agent = "codex"' in content


def test_configure_register_agent_writes_returned_agent_id(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    agent_id = str(uuid4())

    class FakeClient:
        def register_agent(self, *, workspace: str, name: str, agent_type: str) -> dict[str, str]:
            return {
                "agent_id": agent_id,
                "workspace_id": str(uuid4()),
                "name": name,
                "agent_type": agent_type,
                "status": "active",
            }

    monkeypatch.setattr(
        "app.cli.commands.configure.build_client",
        lambda *args, **kwargs: FakeClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "configure",
            "--config",
            str(config_path),
            "--api-base",
            "http://localhost:8000",
            "--workspace",
            "cs3321-demo",
            "--register-agent",
            "codex",
            "--type",
            "editor",
        ],
    )

    assert result.exit_code == 0
    content = config_path.read_text(encoding="utf-8")
    assert f'agent = "{agent_id}"' in content
    assert "Registered agent codex" in result.stderr


def test_health_returns_zero_with_detail_ok(monkeypatch) -> None:
    class FakeClient:
        def health_detail(self, **kwargs) -> dict[str, object]:
            return {
                "status": "ok",
                "service": "MemoryBase API",
                "database": {"status": "up", "error": None},
                "workspace": {"input": "cs3321-demo", "workspace_id": str(uuid4())},
                "agent": {"input": "codex", "agent_id": str(uuid4())},
            }

    monkeypatch.setattr(
        "app.cli.commands.health.build_client",
        lambda *args, **kwargs: FakeClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["health", "--workspace", "cs3321-demo", "--agent", "codex", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"status": "ok"' in result.stdout
    assert "MemoryBase health: ok" in result.stderr


def test_health_maps_backend_error_to_exit_code_three(monkeypatch) -> None:
    class FakeClient:
        def health_detail(self, **kwargs) -> dict[str, object]:
            return {"status": "degraded", "database": {"status": "down", "error": "refused"}}

    monkeypatch.setattr(
        "app.cli.commands.health.build_client",
        lambda *args, **kwargs: FakeClient(),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["health"])

    assert result.exit_code == 3
    assert result.stdout == ""
    assert "MemoryBase health: degraded" in result.stderr


def test_health_returns_client_error_when_workspace_does_not_resolve(monkeypatch) -> None:
    class FakeClient:
        def health_detail(self, **kwargs) -> dict[str, object]:
            return {
                "status": "ok",
                "database": {"status": "up", "error": None},
                "workspace": {
                    "input": "missing",
                    "found": False,
                    "error": "workspace not found",
                },
                "agent": None,
            }

    monkeypatch.setattr(
        "app.cli.commands.health.build_client",
        lambda *args, **kwargs: FakeClient(),
    )
    runner = CliRunner()

    result = runner.invoke(app, ["health", "--workspace", "missing"])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "workspace not found" in result.stderr


def test_health_rejects_unknown_format() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["health", "--format", "xml"])

    assert result.exit_code == 2
