from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from scripts import db_cli


class FakePsqlProcess:
    calls: list[dict[str, Any]] = []

    def __init__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        stdout: int,
        stderr: int,
        text: bool,
        encoding: str,
        errors: str,
    ) -> None:
        self.stdout = io.StringIO("psql: 注意: 关系不存在，跳过\nDROP TRIGGER ━\n")
        self.returncode = 0
        self.calls.append(
            {
                "command": command,
                "cwd": cwd,
                "env": env,
                "stdout": stdout,
                "stderr": stderr,
                "text": text,
                "encoding": encoding,
                "errors": errors,
            }
        )

    def wait(self) -> int:
        return self.returncode


def test_run_subprocess_decodes_psql_output_as_utf8(monkeypatch, capsys) -> None:
    FakePsqlProcess.calls.clear()
    monkeypatch.delenv("PGCLIENTENCODING", raising=False)
    monkeypatch.setattr(db_cli.subprocess, "Popen", FakePsqlProcess)
    monkeypatch.setattr(db_cli, "resolve_client_encoding", lambda env: "UTF8")

    db_cli.run_subprocess(["psql", "postgresql://example", "-c", "SELECT 1"])

    output = capsys.readouterr().out
    assert "注意" in output
    assert "关系不存在，跳过" in output
    assert FakePsqlProcess.calls[0]["env"]["PGCLIENTENCODING"] == "UTF8"
    assert FakePsqlProcess.calls[0]["encoding"] == "utf-8"
    assert FakePsqlProcess.calls[0]["errors"] == "replace"


def test_run_subprocess_uses_gbk_for_windows_chinese_terminal(monkeypatch, capsys) -> None:
    FakePsqlProcess.calls.clear()
    monkeypatch.delenv("PGCLIENTENCODING", raising=False)
    monkeypatch.setattr(db_cli.subprocess, "Popen", FakePsqlProcess)
    monkeypatch.setattr(db_cli, "resolve_client_encoding", lambda env: "GBK")

    db_cli.run_subprocess(["psql", "postgresql://example", "-c", "SELECT 1"])

    assert "注意" in capsys.readouterr().out
    assert FakePsqlProcess.calls[0]["env"]["PGCLIENTENCODING"] == "GBK"
    assert FakePsqlProcess.calls[0]["encoding"] == "gbk"


def test_run_subprocess_respects_existing_pgclientencoding(monkeypatch) -> None:
    FakePsqlProcess.calls.clear()
    monkeypatch.setenv("PGCLIENTENCODING", "UTF8")
    monkeypatch.setattr(db_cli.subprocess, "Popen", FakePsqlProcess)

    db_cli.run_subprocess(["psql", "postgresql://example", "-c", "SELECT 1"])

    assert FakePsqlProcess.calls[0]["env"]["PGCLIENTENCODING"] == "UTF8"
    assert FakePsqlProcess.calls[0]["encoding"] == "utf-8"


def test_resolve_client_encoding_uses_gbk_for_cp936_stdout(monkeypatch) -> None:
    class Stdout:
        encoding = "cp936"

    monkeypatch.setattr(db_cli.sys, "stdout", Stdout())

    assert db_cli.resolve_client_encoding({}) == "GBK"


def test_write_terminal_line_replaces_chars_not_supported_by_terminal(monkeypatch, capsys) -> None:
    class GbkOnlyStdout:
        encoding = "gbk"

        def __init__(self) -> None:
            self.value = ""

        def write(self, line: str) -> int:
            line.encode(self.encoding)
            self.value += line
            return len(line)

    stdout = GbkOnlyStdout()
    monkeypatch.setattr(db_cli.sys, "stdout", stdout)

    db_cli.write_terminal_line("注意 ۹\n")

    assert stdout.value == "注意 ?\n"
    assert capsys.readouterr().out == ""
