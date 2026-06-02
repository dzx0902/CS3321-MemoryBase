from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
DATABASE_DIR = REPO_ROOT / "database"
INIT_SQL_FILES = [
    DATABASE_DIR / "00_init.sql",
    DATABASE_DIR / "01_schema_core.sql",
    DATABASE_DIR / "02_schema_memory.sql",
    DATABASE_DIR / "03_schema_governance.sql",
    DATABASE_DIR / "04_indexes.sql",
    DATABASE_DIR / "05_views.sql",
    DATABASE_DIR / "06_triggers.sql",
]
SEED_SQL_FILES = [
    DATABASE_DIR / "07_seed.sql",
]
GOVERNANCE_FIXTURE_SQL_FILES = [
    DATABASE_DIR / "10_governance_demo_fixture.sql",
]
DEMO_QUERY_SQL_FILES = [
    DATABASE_DIR / "08_demo_queries.sql",
]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        psql_path = resolve_psql()
        database_url = args.database_url or get_database_url()

        if args.command == "init":
            run_init(psql_path, database_url)
        elif args.command == "seed":
            run_seed(psql_path, database_url)
        elif args.command == "reset":
            run_reset(psql_path, database_url)
        elif args.command == "check":
            run_check(psql_path, database_url)
        elif args.command == "run":
            run_single_sql_file(psql_path, database_url, args.sql_file)
        else:
            parser.error(f"unsupported command: {args.command}")
    except Exception as exc:  # pragma: no cover - cli entrypoint
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform database helper for MemoryBase.")
    parser.add_argument(
        "command",
        choices=["init", "seed", "reset", "check", "run"],
        help="Database action to execute.",
    )
    parser.add_argument(
        "sql_file",
        nargs="?",
        help="SQL file to execute when command is `run`.",
    )
    parser.add_argument(
        "--database-url",
        help="Override DATABASE_URL from the environment or .env files.",
    )
    return parser


def resolve_psql() -> str:
    psql_path = shutil.which("psql")
    if psql_path:
        return psql_path
    raise RuntimeError("`psql` was not found in PATH. Install PostgreSQL client tools first.")


def get_database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    env_path = resolve_env_file()
    if env_path is None:
        raise RuntimeError(
            "No DATABASE_URL found. Set it in the environment or in .env/.env.example."
        )

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("DATABASE_URL="):
            value = stripped.split("=", 1)[1].strip()
            if not value:
                raise RuntimeError(f"DATABASE_URL in {env_path.name} is empty.")
            if env_path.name == ".env.example":
                print("Using .env.example because .env was not found.")
            return value

    raise RuntimeError(f"DATABASE_URL was not found in {env_path.name}.")


def resolve_env_file() -> Path | None:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        return env_path
    env_example_path = REPO_ROOT / ".env.example"
    if env_example_path.exists():
        return env_example_path
    return None


def run_init(psql_path: str, database_url: str) -> None:
    print(f"Using DATABASE_URL={database_url}")
    for sql_file in INIT_SQL_FILES:
        run_sql_file(psql_path, database_url, sql_file)
    print("Database schema initialization completed.")


def run_seed(psql_path: str, database_url: str) -> None:
    print(f"Using DATABASE_URL={database_url}")
    for sql_file in existing_seed_files():
        run_sql_file(psql_path, database_url, sql_file)
    run_search_backfill(database_url)
    for sql_file in existing_governance_fixture_files():
        run_sql_file(psql_path, database_url, sql_file)
    for sql_file in existing_demo_query_files():
        run_sql_file(psql_path, database_url, sql_file)
    print("Database seed and demo query scripts completed.")


def run_reset(psql_path: str, database_url: str) -> None:
    print(f"Using DATABASE_URL={database_url}")
    print("==> Recreating public schema")
    run_sql_command(psql_path, database_url, "DROP SCHEMA IF EXISTS public CASCADE;")
    run_sql_command(psql_path, database_url, "CREATE SCHEMA public;")
    run_sql_command(psql_path, database_url, "GRANT ALL ON SCHEMA public TO public;")
    run_init(psql_path, database_url)
    run_seed(psql_path, database_url)
    print("Database reset completed with schema initialization and seed data.")


def run_check(psql_path: str, database_url: str) -> None:
    print(f"Using DATABASE_URL={database_url}")
    print("==> Checking core tables")
    run_sql_command(psql_path, database_url, r"\dt")
    print("==> Checking workspace")
    run_sql_command(
        psql_path, database_url, "SELECT workspace_id, name, scope_type FROM workspace;"
    )
    print("==> Checking memory")
    run_sql_command(
        psql_path,
        database_url,
        "SELECT memory_id, summary, access_level, status FROM memory_item ORDER BY created_at;",
    )
    print("==> Checking conflict")
    run_sql_command(
        psql_path,
        database_url,
        "SELECT conflict_id, status, conflict_type FROM conflict_record ORDER BY created_at;",
    )
    print("==> Checking timeline")
    run_sql_command(
        psql_path,
        database_url,
        "SELECT title, event_type, event_time FROM timeline_entry ORDER BY event_time;",
    )
    print("Database check completed.")


def run_single_sql_file(psql_path: str, database_url: str, sql_file_arg: str | None) -> None:
    if not sql_file_arg:
        raise RuntimeError("`run` requires a SQL file path, for example: database/04_indexes.sql")
    sql_file = Path(sql_file_arg)
    if not sql_file.is_absolute():
        sql_file = REPO_ROOT / sql_file
    print(f"Using DATABASE_URL={database_url}")
    run_sql_file(psql_path, database_url, sql_file)
    print(f"SQL file completed: {sql_file}")


def existing_seed_files() -> list[Path]:
    return [path for path in SEED_SQL_FILES if path.exists()]


def existing_governance_fixture_files() -> list[Path]:
    return [path for path in GOVERNANCE_FIXTURE_SQL_FILES if path.exists()]


def existing_demo_query_files() -> list[Path]:
    return [path for path in DEMO_QUERY_SQL_FILES if path.exists()]


def run_search_backfill(database_url: str) -> None:
    print("==> Backfilling lexical search fields")
    run_subprocess(
        [
            resolve_backend_python(),
            str(BACKEND_DIR / "scripts" / "backfill_search_terms.py"),
            "--full",
            "--database-url",
            database_url,
        ],
        extra_env={"PYTHONPATH": str(BACKEND_DIR)},
    )


def resolve_backend_python() -> str:
    configured_python = os.getenv("MEMORYBASE_PYTHON")
    if configured_python:
        return configured_python

    unix_venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    if unix_venv_python.exists():
        return str(unix_venv_python)

    windows_venv_python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    if windows_venv_python.exists():
        return str(windows_venv_python)

    return sys.executable


def run_sql_file(psql_path: str, database_url: str, sql_file: Path) -> None:
    if not sql_file.exists():
        raise RuntimeError(f"SQL file not found: {sql_file}")
    print(f"==> Running {sql_file}")
    run_subprocess([psql_path, database_url, "-v", "ON_ERROR_STOP=1", "-f", str(sql_file)])


def run_sql_command(psql_path: str, database_url: str, sql: str) -> None:
    run_subprocess([psql_path, database_url, "-v", "ON_ERROR_STOP=1", "-c", sql])


def run_subprocess(command: list[str], *, extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    env.setdefault("PGCLIENTENCODING", "UTF8")
    if extra_env:
        env.update(extra_env)
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed with exit code {completed.returncode}: {' '.join(command)}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
