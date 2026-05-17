from __future__ import annotations

import os
from pathlib import Path

import psycopg
import pytest
from app.main import create_app
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")
    return postgres_dsn


@pytest.fixture()
def integration_client(integration_db: str) -> TestClient:
    app = create_app()
    return TestClient(app)
