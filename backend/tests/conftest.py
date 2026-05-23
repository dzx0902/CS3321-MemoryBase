from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from app.main import create_app
from fastapi.testclient import TestClient

from scripts.backfill_search_terms import backfill_search_terms

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TEST_TMP_ROOT.mkdir(exist_ok=True)
tempfile.tempdir = str(TEST_TMP_ROOT)
os.environ.setdefault("TMP", str(TEST_TMP_ROOT))
os.environ.setdefault("TEMP", str(TEST_TMP_ROOT))

SQL_FILES = [
    PROJECT_ROOT / "database" / "00_init.sql",
    PROJECT_ROOT / "database" / "01_schema_core.sql",
    PROJECT_ROOT / "database" / "02_schema_memory.sql",
    PROJECT_ROOT / "database" / "03_schema_governance.sql",
    PROJECT_ROOT / "database" / "04_indexes.sql",
    PROJECT_ROOT / "database" / "05_views.sql",
    PROJECT_ROOT / "database" / "06_triggers.sql",
    PROJECT_ROOT / "database" / "07_seed.sql",
]


@pytest.fixture()
def tmp_path(request: pytest.FixtureRequest) -> Path:
    path = TEST_TMP_ROOT / f"test-{uuid4()}"
    path.mkdir(parents=True, exist_ok=False)
    if "outside_git_repo" in request.node.name:
        (path / ".git").write_text("gitdir: ./missing-git-dir\n", encoding="utf-8")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://memorybase:memorybase@localhost:5432/memorybase_db",
    )


@pytest.fixture()
def integration_db(postgres_dsn: str) -> str:
    try:
        with psycopg.connect(postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
                cur.execute("CREATE SCHEMA public")
                cur.execute("GRANT ALL ON SCHEMA public TO public")
                for sql_file in SQL_FILES:
                    cur.execute(sql_file.read_text(encoding="utf-8"))
            conn.commit()
        backfill_search_terms(
            postgres_dsn,
            full=True,
            missing_only=False,
            workspace_slug=None,
        )
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")
    return postgres_dsn


@pytest.fixture()
def integration_client(integration_db: str) -> TestClient:
    app = create_app()
    return TestClient(app)
