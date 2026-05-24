from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ..core.database import Database, parse_uuid
from ..models.agent import AgentRegisterRequest, AgentRegisterResponse


class AgentWorkspaceNotFoundError(Exception):
    pass


class AgentRepository(Protocol):
    def register_agent(self, payload: AgentRegisterRequest) -> AgentRegisterResponse:
        ...


@dataclass(slots=True)
class AgentService:
    repository: AgentRepository

    def register_agent(self, payload: AgentRegisterRequest) -> AgentRegisterResponse:
        return self.repository.register_agent(payload)


class PostgresAgentRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def register_agent(self, payload: AgentRegisterRequest) -> AgentRegisterResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                workspace_id = resolve_workspace_id(cur, payload.workspace)
                if workspace_id is None:
                    raise AgentWorkspaceNotFoundError(
                        f"Workspace not found for {payload.workspace!r}."
                    )
                cur.execute(
                    """
                    INSERT INTO agent(workspace_id, name, agent_type, status)
                    VALUES (%(workspace_id)s, %(name)s, %(agent_type)s, 'active')
                    ON CONFLICT (workspace_id, name)
                    DO UPDATE SET
                      agent_type = EXCLUDED.agent_type,
                      status = 'active'
                    RETURNING agent_id, workspace_id, name, agent_type, status
                    """,
                    {
                        "workspace_id": workspace_id,
                        "name": payload.name,
                        "agent_type": payload.agent_type,
                    },
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:  # pragma: no cover - INSERT RETURNING should always return one row.
            raise RuntimeError("Agent registration did not return an agent row.")
        return AgentRegisterResponse(**row)


def resolve_workspace_id(cur, workspace: str) -> UUID | None:
    workspace_id = parse_uuid(workspace)
    if workspace_id is not None:
        cur.execute(
            "SELECT workspace_id FROM workspace WHERE workspace_id = %(workspace_id)s",
            {"workspace_id": workspace_id},
        )
    else:
        cur.execute(
            "SELECT workspace_id FROM workspace WHERE slug = %(workspace)s",
            {"workspace": workspace},
        )
    row = cur.fetchone()
    if row is None:
        return None
    return row["workspace_id"]
