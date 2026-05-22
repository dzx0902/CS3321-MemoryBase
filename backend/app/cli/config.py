from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

DEFAULT_API_BASE_URL = "http://localhost:8000"
DEFAULT_ACTOR_TYPE = "agent"


@dataclass(frozen=True, slots=True)
class CliConfig:
    api_base_url: str = DEFAULT_API_BASE_URL
    workspace: str | None = None
    agent: str | None = None
    actor_type: str = DEFAULT_ACTOR_TYPE
    actor_id: str | None = None
    database_url: str | None = None

    def with_overrides(
        self,
        *,
        api_base_url: str | None = None,
        workspace: str | None = None,
        agent: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        database_url: str | None = None,
    ) -> CliConfig:
        updates = {
            "api_base_url": api_base_url,
            "workspace": workspace,
            "agent": agent,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "database_url": database_url,
        }
        return replace(self, **{key: value for key, value in updates.items() if value is not None})


def load_config(config_path: Path | None = None) -> CliConfig:
    config = CliConfig()

    user_path = config_path or configured_user_config_path()
    project_path = Path.cwd() / ".memorybase.toml"

    if user_path.exists():
        config = merge_mapping(config, read_toml(user_path))
    if config_path is None and project_path.exists():
        config = merge_mapping(config, read_toml(project_path))
    config = merge_mapping(config, env_config())
    return config


def default_write_config_path(config_path: Path | None = None) -> Path:
    return config_path or configured_user_config_path()


def configured_user_config_path() -> Path:
    explicit_path = os.getenv("MEMORYBASE_CONFIG_PATH")
    if explicit_path:
        return Path(explicit_path).expanduser()

    config_home = os.getenv("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home).expanduser() / "memorybase" / "config.toml"
    return Path.home() / ".config" / "memorybase" / "config.toml"


def read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    if not isinstance(raw, dict):
        return {}
    return raw


def env_config() -> dict[str, str]:
    mapping = {
        "api_base_url": os.getenv("MEMORYBASE_API_BASE_URL"),
        "workspace": os.getenv("MEMORYBASE_WORKSPACE"),
        "agent": os.getenv("MEMORYBASE_AGENT"),
        "actor_type": os.getenv("MEMORYBASE_ACTOR_TYPE"),
        "actor_id": os.getenv("MEMORYBASE_ACTOR_ID"),
        "database_url": os.getenv("DATABASE_URL") or os.getenv("MEMORYBASE_DATABASE_URL"),
    }
    return {key: value for key, value in mapping.items() if value}


def merge_mapping(config: CliConfig, values: dict[str, Any]) -> CliConfig:
    allowed = {
        "api_base_url",
        "workspace",
        "agent",
        "actor_type",
        "actor_id",
        "database_url",
    }
    normalized = {key: str(value) for key, value in values.items() if key in allowed and value}
    return config.with_overrides(**normalized)


def write_config(config: CliConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    for key in (
        "api_base_url",
        "workspace",
        "agent",
        "actor_type",
        "actor_id",
        "database_url",
    ):
        value = getattr(config, key)
        if value is None:
            continue
        rows.append(f'{key} = "{escape_toml_string(value)}"')
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
