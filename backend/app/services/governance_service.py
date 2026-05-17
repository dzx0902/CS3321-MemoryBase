from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.governance import (
    AuditEntryResponse,
    AuditQueryResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    PolicyCreateRequest,
    PolicyResponse,
    TimelineCreateRequest,
    TimelineEntryResponse,
)


class WorkspaceNotFoundError(Exception):
    pass


class ConflictNotFoundError(Exception):
    pass


class GovernanceRepository(Protocol):
    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        ...

    def list_policies(self, *, workspace_id: UUID | None) -> list[PolicyResponse]:
        ...

    def list_audit_logs(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str | None,
        action_type: str | None,
        target_type: str | None,
        target_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        ...

    def list_conflicts(self, *, workspace_id: UUID | None) -> list[ConflictResponse]:
        ...

    def update_conflict(
        self, conflict_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse | None:
        ...

    def list_timeline(self, *, workspace_id: UUID | None) -> list[TimelineEntryResponse]:
        ...

    def create_timeline_entry(self, payload: TimelineCreateRequest) -> TimelineEntryResponse:
        ...


@dataclass(slots=True)
class GovernanceService:
    repository: GovernanceRepository

    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        return self.repository.create_policy(payload)

    def list_policies(self, *, workspace_id: UUID | None) -> list[PolicyResponse]:
        return self.repository.list_policies(workspace_id=workspace_id)

    def list_audit_logs(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str | None,
        action_type: str | None,
        target_type: str | None,
        target_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        return self.repository.list_audit_logs(
            workspace_id=workspace_id,
            actor_type=actor_type,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )

    def list_conflicts(self, *, workspace_id: UUID | None) -> list[ConflictResponse]:
        return self.repository.list_conflicts(workspace_id=workspace_id)

    def update_conflict(
        self, conflict_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse:
        conflict = self.repository.update_conflict(conflict_id, payload)
        if conflict is None:
            raise ConflictNotFoundError(f"conflict {conflict_id} not found")
        return conflict

    def list_timeline(self, *, workspace_id: UUID | None) -> list[TimelineEntryResponse]:
        return self.repository.list_timeline(workspace_id=workspace_id)

    def create_timeline_entry(self, payload: TimelineCreateRequest) -> TimelineEntryResponse:
        return self.repository.create_timeline_entry(payload)


class PostgresGovernanceRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO access_policy (
                        workspace_id,
                        principal_type,
                        principal_id,
                        resource_type,
                        resource_scope,
                        effect,
                        predicate_json
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(principal_type)s,
                        %(principal_id)s,
                        %(resource_type)s,
                        %(resource_scope)s,
                        %(effect)s,
                        %(predicate_json)s::jsonb
                    )
                    RETURNING
                        policy_id,
                        workspace_id,
                        principal_type,
                        principal_id,
                        resource_type,
                        resource_scope,
                        effect,
                        predicate_json,
                        created_at
                    """,
                    {**payload.model_dump(), "predicate_json": _json_dumps(payload.predicate_json)},
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            raise RuntimeError("failed to create policy")
        return PolicyResponse(**row)

    def list_policies(self, *, workspace_id: UUID | None) -> list[PolicyResponse]:
        query = """
            SELECT
                policy_id,
                workspace_id,
                principal_type,
                principal_id,
                resource_type,
                resource_scope,
                effect,
                predicate_json,
                created_at
            FROM access_policy
        """
        params: dict[str, object] = {}
        if workspace_id is not None:
            query += " WHERE workspace_id = %(workspace_id)s"
            params["workspace_id"] = workspace_id
        query += " ORDER BY created_at DESC"

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [PolicyResponse(**row) for row in rows]

    def list_audit_logs(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str | None,
        action_type: str | None,
        target_type: str | None,
        target_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        if workspace_id is not None and not self._workspace_exists(workspace_id):
            raise WorkspaceNotFoundError(f"workspace {workspace_id} not found")

        filters: list[str] = []
        params: dict[str, object] = {"limit": page_size, "offset": (page - 1) * page_size}
        if workspace_id is not None:
            filters.append("workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        if actor_type is not None:
            filters.append("actor_type = %(actor_type)s")
            params["actor_type"] = actor_type
        if action_type is not None:
            filters.append("action_type = %(action_type)s")
            params["action_type"] = action_type
        if target_type is not None:
            filters.append("target_type = %(target_type)s")
            params["target_type"] = target_type
        if target_id is not None:
            filters.append("target_id = %(target_id)s")
            params["target_id"] = target_id
        if start_time is not None:
            filters.append("created_at >= %(start_time)s")
            params["start_time"] = start_time
        if end_time is not None:
            filters.append("created_at <= %(end_time)s")
            params["end_time"] = end_time
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) AS total FROM audit_log {where_clause}", params)
                total = cur.fetchone()["total"]
                cur.execute(
                    f"""
                    SELECT
                        audit_id,
                        workspace_id,
                        actor_type,
                        actor_id,
                        action_type,
                        target_type,
                        target_id,
                        before_json,
                        after_json,
                        created_at
                    FROM audit_log
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = cur.fetchall()
        return AuditQueryResponse(
            items=[AuditEntryResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def list_conflicts(self, *, workspace_id: UUID | None) -> list[ConflictResponse]:
        query = """
            SELECT
                conflict_id,
                workspace_id,
                conflict_type,
                status,
                resolution_note,
                resolved_by_actor_type,
                resolved_by_actor_id,
                resolved_at,
                created_at,
                updated_at
                ,
                left_memory_id,
                left_memory_type,
                left_memory_text,
                left_memory_summary,
                right_memory_id,
                right_memory_type,
                right_memory_text,
                right_memory_summary
            FROM v_conflict_memory
        """
        params: dict[str, object] = {}
        if workspace_id is not None:
            query += " WHERE workspace_id = %(workspace_id)s"
            params["workspace_id"] = workspace_id
        query += " ORDER BY updated_at DESC, created_at DESC"
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [ConflictResponse(**row) for row in rows]

    def update_conflict(
        self, conflict_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM conflict_record
                    WHERE conflict_id = %(conflict_id)s
                    """,
                    {"conflict_id": conflict_id},
                )
                before_row = cur.fetchone()
                if before_row is None:
                    return None

                cur.execute(
                    """
                    UPDATE conflict_record
                    SET
                        status = %(status)s::varchar,
                        resolution_note = %(resolution_note)s,
                        resolved_by_actor_type = %(actor_type)s::varchar,
                        resolved_by_actor_id = %(actor_id)s,
                        resolved_at = CASE
                            WHEN %(status)s::varchar IN ('resolved', 'ignored') THEN now()
                            ELSE NULL
                        END
                    WHERE conflict_id = %(conflict_id)s
                    RETURNING *
                    """,
                    {
                        "conflict_id": conflict_id,
                        "status": payload.status,
                        "resolution_note": payload.resolution_note,
                        "actor_type": payload.actor_type,
                        "actor_id": payload.actor_id,
                    },
                )
                after_row = cur.fetchone()
                if after_row is None:
                    return None

                cur.execute(
                    """
                    INSERT INTO audit_log (
                        workspace_id,
                        actor_type,
                        actor_id,
                        action_type,
                        target_type,
                        target_id,
                        before_json,
                        after_json
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(actor_type)s,
                        %(actor_id)s,
                        'conflict.update',
                        'conflict_record',
                        %(target_id)s,
                        %(before_json)s::jsonb,
                        %(after_json)s::jsonb
                    )
                    """,
                    {
                        "workspace_id": before_row["workspace_id"],
                        "actor_type": payload.actor_type,
                        "actor_id": payload.actor_id,
                        "target_id": conflict_id,
                        "before_json": _json_dumps(before_row),
                        "after_json": _json_dumps(after_row),
                    },
                )
            conn.commit()
        return self._get_conflict(conflict_id)

    def list_timeline(self, *, workspace_id: UUID | None) -> list[TimelineEntryResponse]:
        query = """
            SELECT
                timeline_id,
                workspace_id,
                event_time,
                event_type,
                title,
                description,
                importance,
                memory_id,
                doc_id,
                memory_type,
                memory_text,
                source_title
            FROM v_project_timeline
        """
        params: dict[str, object] = {}
        if workspace_id is not None:
            query += " WHERE workspace_id = %(workspace_id)s"
            params["workspace_id"] = workspace_id
        query += " ORDER BY event_time DESC, importance DESC"
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [TimelineEntryResponse(**row) for row in rows]

    def create_timeline_entry(self, payload: TimelineCreateRequest) -> TimelineEntryResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO timeline_entry (
                        workspace_id,
                        memory_id,
                        doc_id,
                        event_type,
                        title,
                        description,
                        event_time,
                        importance
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(memory_id)s,
                        %(doc_id)s,
                        %(event_type)s,
                        %(title)s,
                        %(description)s,
                        %(event_time)s,
                        %(importance)s
                    )
                    RETURNING timeline_id
                    """,
                    payload.model_dump(),
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            raise RuntimeError("failed to create timeline entry")
        timeline = self._get_timeline_entry(row["timeline_id"])
        if timeline is None:
            raise RuntimeError("created timeline entry cannot be loaded")
        return timeline

    def _get_conflict(self, conflict_id: UUID) -> ConflictResponse | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        conflict_id,
                        workspace_id,
                        conflict_type,
                        status,
                        resolution_note,
                        resolved_by_actor_type,
                        resolved_by_actor_id,
                        resolved_at,
                        created_at,
                        updated_at,
                        left_memory_id,
                        left_memory_type,
                        left_memory_text,
                        left_memory_summary,
                        right_memory_id,
                        right_memory_type,
                        right_memory_text,
                        right_memory_summary
                    FROM v_conflict_memory
                    WHERE conflict_id = %(conflict_id)s
                    """,
                    {"conflict_id": conflict_id},
                )
                row = cur.fetchone()
        return ConflictResponse(**row) if row is not None else None

    def _get_timeline_entry(self, timeline_id: UUID) -> TimelineEntryResponse | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        timeline_id,
                        workspace_id,
                        event_time,
                        event_type,
                        title,
                        description,
                        importance,
                        memory_id,
                        doc_id,
                        memory_type,
                        memory_text,
                        source_title
                    FROM v_project_timeline
                    WHERE timeline_id = %(timeline_id)s
                    """,
                    {"timeline_id": timeline_id},
                )
                row = cur.fetchone()
        return TimelineEntryResponse(**row) if row is not None else None

    def _workspace_exists(self, workspace_id: UUID) -> bool:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 AS ok FROM workspace WHERE workspace_id = %(workspace_id)s",
                    {"workspace_id": workspace_id},
                )
                return cur.fetchone() is not None


def _json_dumps(payload: object) -> str:
    import json

    return json.dumps(payload, default=str)
