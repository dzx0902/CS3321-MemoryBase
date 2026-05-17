from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseModel):
    app_name: str = "MemoryBase API"
    app_version: str = "0.1.0"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://memorybase:memorybase@localhost:5432/memorybase_db",
    )
    backend_host: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    chunk_max_chars: int = 800
    chunk_overlap_lines: int = 1


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
