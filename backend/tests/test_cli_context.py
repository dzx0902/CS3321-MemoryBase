from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.cli.main import app
from typer.testing import CliRunner


class FakeContextClient:
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

    def context_pack(self, payload):
        return {
            "recall_id": str(uuid4()),
            "result_count": 1,
            "token_count": 42,
            "markdown": "# MemoryBase Context\n\n## Relevant Memories\n- [M1] decision",
            "citation_map": {"memories": {"M1": {"memory_type": "decision"}}},
        }

    def get_session_messages(self, *, session_id: str, workspace_id: str | None, limit: int):
        return {
            "items": [
                {
                    "message_id": str(uuid4()),
                    "session_id": session_id,
                    "sender_type": "user",
                    "sender_id": None,
                    "role": "user",
                    "content": "Implement repo-aware context.",
                    "created_at": "2026-05-23T00:00:00Z",
                    "reply_to_message_id": None,
                }
            ],
            "total": 1,
            "limit": limit,
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


def test_cli_context_outputs_markdown_to_stdout(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cli.commands.context.build_client",
        lambda *args, **kwargs: FakeContextClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "context",
            "为什么放弃食堂",
            "--workspace",
            "cs3321-demo",
            "--no-repo",
            "--max-tokens",
            "500",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.startswith("# MemoryBase Context")
    assert "recall_id=" in result.stderr
    assert "token_count=" in result.stderr


def test_cli_context_can_render_repo_and_session_when_memory_is_empty(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class EmptyContextClient(FakeContextClient):
        def context_pack(self, payload):
            return {
                "recall_id": str(uuid4()),
                "result_count": 0,
                "token_count": 16,
                "markdown": "",
                "citation_map": {},
            }

    source = tmp_path / "feature.py"
    source.write_text(
        "def repo_context():\n    return 'MemoryBase repo context'\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "app.cli.commands.context.build_client",
        lambda *args, **kwargs: EmptyContextClient(),
    )
    monkeypatch.setattr(
        "app.cli.commands.context.collect_repo_context",
        lambda *args, **kwargs: type(
            "FakeRepoContext",
            (),
            {
                "metadata": type(
                    "FakeMetadata",
                    (),
                    {
                        "git_root": tmp_path,
                        "branch": "jflin",
                        "status_short": " M feature.py",
                        "changed_files": ["feature.py"],
                        "diff_stat": " feature.py | 2 +",
                        "recent_commits": ["abc123 test"],
                    },
                )(),
                "snippets": [
                    type(
                        "FakeSnippet",
                        (),
                        {
                            "path": "feature.py",
                            "start_line": 1,
                            "end_line": 2,
                            "reason": "changed_file",
                            "text": source.read_text(encoding="utf-8"),
                        },
                    )()
                ],
                "warnings": [],
            },
        )(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "context",
            "repo context",
            "--workspace",
            "cs3321-demo",
            "--session",
            str(uuid4()),
            "--repo-root",
            str(tmp_path),
            "--max-tokens",
            "1000",
        ],
    )

    assert result.exit_code == 0
    assert "## Repository State" in result.stdout
    assert "feature.py" in result.stdout
    assert "## Session Notes" in result.stdout
    assert "Implement repo-aware context." in result.stdout
    assert "source_counts" in result.stderr


def test_cli_context_falls_back_to_search_when_recall_is_empty(monkeypatch) -> None:
    class EmptyContextClient(FakeContextClient):
        def context_pack(self, payload):
            return {
                "recall_id": str(uuid4()),
                "result_count": 0,
                "token_count": 16,
                "markdown": "",
                "citation_map": {},
            }

    monkeypatch.setattr(
        "app.cli.commands.context.build_client",
        lambda *args, **kwargs: EmptyContextClient(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "context",
            "cafeteria system",
            "--workspace",
            "cs3321-demo",
            "--no-repo",
            "--max-tokens",
            "1000",
        ],
    )

    assert result.exit_code == 0
    assert "## Search Results" in result.stdout
    assert "The cafeteria system was too CRUD-heavy" in result.stdout


def test_cli_context_repo_only_does_not_require_backend(monkeypatch, tmp_path: Path) -> None:
    def fail_build_client(*args, **kwargs):
        raise AssertionError("repo-only context should not build an API client")

    monkeypatch.setattr("app.cli.commands.context.build_client", fail_build_client)
    monkeypatch.setattr(
        "app.cli.commands.context.collect_repo_context",
        lambda *args, **kwargs: type(
            "FakeRepoContext",
            (),
            {
                "metadata": type(
                    "FakeMetadata",
                    (),
                    {
                        "git_root": tmp_path,
                        "branch": "jflin",
                        "status_short": "",
                        "changed_files": [],
                        "diff_stat": "",
                        "recent_commits": [],
                    },
                )(),
                "snippets": [],
                "warnings": [],
            },
        )(),
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "context",
            "repo only",
            "--repo-only",
            "--repo-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "## Repository State" in result.stdout
