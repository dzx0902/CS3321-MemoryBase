from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            yield conn

    def ping(self) -> tuple[bool, str | None]:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 AS ok")
                    cur.fetchone()
            return True, None
        except Exception as exc:  # pragma: no cover - defensive path
            return False, str(exc)

    def health_detail(
        self,
        *,
        workspace: str | None = None,
        agent: str | None = None,
    ) -> dict[str, object]:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) AS workspace_count FROM workspace")
                schema_row = cur.fetchone() or {"workspace_count": 0}
                workspace_payload = self._resolve_workspace(cur, workspace)
                agent_payload = self._resolve_agent(
                    cur,
                    agent=agent,
                    workspace_id=workspace_payload.get("workspace_id")
                    if isinstance(workspace_payload, dict)
                    else None,
                )
        return {
            "schema": {"workspace_count": schema_row["workspace_count"]},
            "workspace": workspace_payload,
            "agent": agent_payload,
        }

    def _resolve_workspace(
        self,
        cur: psycopg.Cursor,
        workspace: str | None,
    ) -> dict[str, object] | None:
        if workspace is None:
            return None
        workspace_id = parse_uuid(workspace)
        if workspace_id is not None:
            cur.execute(
                """
                SELECT workspace_id, slug, name, scope_type
                FROM workspace
                WHERE workspace_id = %(workspace_id)s
                """,
                {"workspace_id": workspace_id},
            )
        else:
            cur.execute(
                """
                SELECT workspace_id, slug, name, scope_type
                FROM workspace
                WHERE slug = %(workspace)s
                """,
                {"workspace": workspace},
            )
        row = cur.fetchone()
        if row is None:
            return {"input": workspace, "found": False, "error": "workspace not found"}
        return {"input": workspace, "found": True, **row}

    def _resolve_agent(
        self,
        cur: psycopg.Cursor,
        *,
        agent: str | None,
        workspace_id: object,
    ) -> dict[str, object] | None:
        if agent is None:
            return None
        agent_id = parse_uuid(agent)
        params: dict[str, object] = {"agent": agent, "agent_id": agent_id}
        workspace_clause = ""
        if workspace_id:
            workspace_clause = "AND workspace_id = %(workspace_id)s"
            params["workspace_id"] = workspace_id

        if agent_id is not None:
            cur.execute(
                f"""
                SELECT agent_id, workspace_id, name, agent_type, status
                FROM agent
                WHERE agent_id = %(agent_id)s
                {workspace_clause}
                """,
                params,
            )
        else:
            cur.execute(
                f"""
                SELECT agent_id, workspace_id, name, agent_type, status
                FROM agent
                WHERE name = %(agent)s
                {workspace_clause}
                ORDER BY created_at DESC
                LIMIT 2
                """,
                params,
            )
        rows = cur.fetchall()
        if not rows:
            return {"input": agent, "found": False, "error": "agent not found"}
        if len(rows) > 1:
            return {"input": agent, "found": False, "error": "agent name is ambiguous"}
        return {"input": agent, "found": True, **rows[0]}


def parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
