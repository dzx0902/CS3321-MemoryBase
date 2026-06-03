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
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "local")
    siliconflow_api_key: str = os.getenv("SILICONFLOW_API_KEY", "")
    siliconflow_base_url: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    siliconflow_embedding_model: str = os.getenv(
        "SILICONFLOW_EMBEDDING_MODEL",
        "Qwen/Qwen3-Embedding-0.6B",
    )
    siliconflow_embedding_dimensions: int = int(
        os.getenv("SILICONFLOW_EMBEDDING_DIMENSIONS", "1024")
    )
    llm_provider: str = os.getenv("LLM_PROVIDER", "")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "800"))
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_chat_model: str = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
    siliconflow_chat_model: str = os.getenv("SILICONFLOW_CHAT_MODEL", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
