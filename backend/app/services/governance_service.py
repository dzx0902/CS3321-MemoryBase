from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.governance import (
    AuditEntryResponse,
    AuditQueryResponse,
    ConflictListResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    ForgetRequestCreateRequest,
    ForgetRequestListResponse,
    ForgetRequestResponse,
    ForgetRequestUpdateRequest,
    PolicyCreateRequest,
    PolicyListResponse,
    PolicyResponse,
    TimelineCreateRequest,
    TimelineEntryResponse,
    TimelineListResponse,
)


class WorkspaceNotFoundError(Exception):
    pass


class ConflictNotFoundError(Exception):
    pass


class ForgetRequestNotFoundError(Exception):
    pass


class ReviewerRequiredError(Exception):
    pass


class TargetNotFoundError(Exception):
    pass


class UnsupportedForgetTargetError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class GovernanceRepository(Protocol):
    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        ...

    def list_policies(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> PolicyListResponse:
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

    def list_conflicts(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> ConflictListResponse:
        ...

    def update_conflict(
        self, conflict_id: UUID, workspace_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse | None:
        ...

    def create_forget_request(self, payload: ForgetRequestCreateRequest) -> ForgetRequestResponse:
        ...

    def list_forget_requests(
        self,
        *,
        workspace_id: UUID | None,
        status: str | None,
        target_type: str | None,
        page: int,
        page_size: int,
    ) -> ForgetRequestListResponse:
        ...

    def update_forget_request(
        self, request_id: UUID, workspace_id: UUID, payload: ForgetRequestUpdateRequest
    ) -> ForgetRequestResponse | None:
        ...

    def list_timeline(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> TimelineListResponse:
        ...

    def create_timeline_entry(self, payload: TimelineCreateRequest) -> TimelineEntryResponse:
        ...


@dataclass(slots=True)
class GovernanceService:
    repository: GovernanceRepository

    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        return self.repository.create_policy(payload)

    def list_policies(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> PolicyListResponse:
        return self.repository.list_policies(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
        )

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

    def list_conflicts(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> ConflictListResponse:
        return self.repository.list_conflicts(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
        )

    def update_conflict(
        self, conflict_id: UUID, workspace_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse:
        conflict = self.repository.update_conflict(conflict_id, workspace_id, payload)
        if conflict is None:
            raise ConflictNotFoundError(f"conflict {conflict_id} not found")
        return conflict

    def create_forget_request(self, payload: ForgetRequestCreateRequest) -> ForgetRequestResponse:
        return self.repository.create_forget_request(payload)

    def list_forget_requests(
        self,
        *,
        workspace_id: UUID | None,
        status: str | None,
        target_type: str | None,
        page: int,
        page_size: int,
    ) -> ForgetRequestListResponse:
        return self.repository.list_forget_requests(
            workspace_id=workspace_id,
            status=status,
            target_type=target_type,
            page=page,
            page_size=page_size,
        )

    def update_forget_request(
        self, request_id: UUID, workspace_id: UUID, payload: ForgetRequestUpdateRequest
    ) -> ForgetRequestResponse:
        forget_request = self.repository.update_forget_request(request_id, workspace_id, payload)
        if forget_request is None:
            raise ForgetRequestNotFoundError(f"forget request {request_id} not found")
        return forget_request

    def list_timeline(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> TimelineListResponse:
        return self.repository.list_timeline(
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
        )

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

    def list_policies(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> PolicyListResponse:
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
        count_query = "SELECT COUNT(*) AS total FROM access_policy"
        params: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if workspace_id is not None:
            query += " WHERE workspace_id = %(workspace_id)s"
            count_query += " WHERE workspace_id = %(workspace_id)s"
            params["workspace_id"] = workspace_id
        query += " ORDER BY created_at DESC LIMIT %(limit)s OFFSET %(offset)s"

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                cur.execute(query, params)
                rows = cur.fetchall()
        return PolicyListResponse(
            items=[PolicyResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

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

    def list_conflicts(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> ConflictListResponse:
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
        count_query = "SELECT COUNT(*) AS total FROM v_conflict_memory"
        params: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if workspace_id is not None:
            query += " WHERE workspace_id = %(workspace_id)s"
            count_query += " WHERE workspace_id = %(workspace_id)s"
            params["workspace_id"] = workspace_id
        query += " ORDER BY updated_at DESC, created_at DESC LIMIT %(limit)s OFFSET %(offset)s"
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                cur.execute(query, params)
                rows = cur.fetchall()
        return ConflictListResponse(
            items=[ConflictResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def update_conflict(
        self, conflict_id: UUID, workspace_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse | None:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM conflict_record
                    WHERE conflict_id = %(conflict_id)s
                      AND workspace_id = %(workspace_id)s
                    """,
                    {"conflict_id": conflict_id, "workspace_id": workspace_id},
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
                      AND workspace_id = %(workspace_id)s
                    RETURNING *
                    """,
                    {
                        "conflict_id": conflict_id,
                        "workspace_id": workspace_id,
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
        return self._get_conflict(conflict_id, workspace_id)

    def create_forget_request(self, payload: ForgetRequestCreateRequest) -> ForgetRequestResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                self._require_workspace(cur, payload.workspace_id)
                if payload.requester_user_id is not None:
                    self._require_user(cur, payload.requester_user_id)
                self._require_forget_target(
                    cur,
                    payload.workspace_id,
                    payload.target_type,
                    payload.target_id,
                )

                cur.execute(
                    """
                    INSERT INTO forget_request (
                        workspace_id,
                        target_type,
                        target_id,
                        requester_user_id,
                        reason
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(target_type)s,
                        %(target_id)s,
                        %(requester_user_id)s,
                        %(reason)s
                    )
                    RETURNING
                        request_id,
                        workspace_id,
                        target_type,
                        target_id,
                        requester_user_id,
                        reviewed_by_user_id,
                        reason,
                        status,
                        requested_at,
                        resolved_at
                    """,
                    payload.model_dump(),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("failed to create forget request")

                cur.execute(
                    """
                    INSERT INTO audit_log (
                        workspace_id,
                        actor_type,
                        actor_id,
                        action_type,
                        target_type,
                        target_id,
                        after_json
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(actor_type)s,
                        %(actor_id)s,
                        'forget_request.create',
                        'forget_request',
                        %(target_id)s,
                        %(after_json)s::jsonb
                    )
                    """,
                    {
                        "workspace_id": row["workspace_id"],
                        "actor_type": "user" if row["requester_user_id"] is not None else "system",
                        "actor_id": row["requester_user_id"],
                        "target_id": row["request_id"],
                        "after_json": _json_dumps(row),
                    },
                )
            conn.commit()
        return ForgetRequestResponse(**row)

    def list_forget_requests(
        self,
        *,
        workspace_id: UUID | None,
        status: str | None,
        target_type: str | None,
        page: int,
        page_size: int,
    ) -> ForgetRequestListResponse:
        query = """
            SELECT
                request_id,
                workspace_id,
                target_type,
                target_id,
                requester_user_id,
                reviewed_by_user_id,
                reason,
                status,
                requested_at,
                resolved_at
            FROM forget_request
        """
        count_query = "SELECT COUNT(*) AS total FROM forget_request"
        filters: list[str] = []
        params: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if workspace_id is not None:
            filters.append("workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        if status is not None:
            filters.append("status = %(status)s")
            params["status"] = status
        if target_type is not None:
            filters.append("target_type = %(target_type)s")
            params["target_type"] = target_type
        if filters:
            where_clause = f" WHERE {' AND '.join(filters)}"
            query += where_clause
            count_query += where_clause
        query += " ORDER BY requested_at DESC, request_id DESC LIMIT %(limit)s OFFSET %(offset)s"

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                cur.execute(query, params)
                rows = cur.fetchall()
        return ForgetRequestListResponse(
            items=[ForgetRequestResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def update_forget_request(
        self, request_id: UUID, workspace_id: UUID, payload: ForgetRequestUpdateRequest
    ) -> ForgetRequestResponse | None:
        if payload.status != "pending" and payload.reviewed_by_user_id is None:
            raise ReviewerRequiredError("reviewed_by_user_id is required for reviewed requests")

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM forget_request
                    WHERE request_id = %(request_id)s
                      AND workspace_id = %(workspace_id)s
                    FOR UPDATE
                    """,
                    {"request_id": request_id, "workspace_id": workspace_id},
                )
                before_row = cur.fetchone()
                if before_row is None:
                    return None
                if payload.reviewed_by_user_id is not None:
                    self._require_user(cur, payload.reviewed_by_user_id)

                actor_type = "user" if payload.reviewed_by_user_id is not None else "system"
                actor_id = str(payload.reviewed_by_user_id) if payload.reviewed_by_user_id else ""
                cur.execute(
                    "SELECT set_config('app.actor_type', %(actor_type)s, true)",
                    {"actor_type": actor_type},
                )
                cur.execute(
                    "SELECT set_config('app.actor_id', %(actor_id)s, true)",
                    {"actor_id": actor_id},
                )
                cur.execute(
                    "SELECT set_config('app.revision_reason', %(reason)s, true)",
                    {"reason": f"forget request {payload.status}"},
                )

                if (
                    before_row["target_type"] == "memory_item"
                    and payload.status in {"approved", "done"}
                ):
                    self._require_forget_target(
                        cur,
                        workspace_id,
                        before_row["target_type"],
                        before_row["target_id"],
                    )
                    cur.execute(
                        """
                        UPDATE memory_item
                        SET status = 'forgotten',
                            valid_to = coalesce(valid_to, now())
                        WHERE memory_id = %(memory_id)s
                          AND workspace_id = %(workspace_id)s
                          AND status <> 'forgotten'
                        """,
                        {
                            "memory_id": before_row["target_id"],
                            "workspace_id": workspace_id,
                        },
                    )

                cur.execute(
                    """
                    UPDATE forget_request
                    SET
                        status = %(status)s::varchar,
                        reviewed_by_user_id = %(reviewed_by_user_id)s,
                        resolved_at = CASE
                            WHEN %(status)s::varchar IN ('approved', 'rejected', 'done') THEN now()
                            ELSE NULL
                        END
                    WHERE request_id = %(request_id)s
                      AND workspace_id = %(workspace_id)s
                    RETURNING
                        request_id,
                        workspace_id,
                        target_type,
                        target_id,
                        requester_user_id,
                        reviewed_by_user_id,
                        reason,
                        status,
                        requested_at,
                        resolved_at
                    """,
                    {
                        "request_id": request_id,
                        "workspace_id": workspace_id,
                        "status": payload.status,
                        "reviewed_by_user_id": payload.reviewed_by_user_id,
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
                        'forget_request.update',
                        'forget_request',
                        %(target_id)s,
                        %(before_json)s::jsonb,
                        %(after_json)s::jsonb
                    )
                    """,
                    {
                        "workspace_id": after_row["workspace_id"],
                        "actor_type": actor_type,
                        "actor_id": payload.reviewed_by_user_id,
                        "target_id": request_id,
                        "before_json": _json_dumps(before_row),
                        "after_json": _json_dumps(after_row),
                    },
                )
            conn.commit()
        return ForgetRequestResponse(**after_row)

    def list_timeline(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> TimelineListResponse:
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
        count_query = "SELECT COUNT(*) AS total FROM v_project_timeline"
        params: dict[str, object] = {
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if workspace_id is not None:
            query += " WHERE workspace_id = %(workspace_id)s"
            count_query += " WHERE workspace_id = %(workspace_id)s"
            params["workspace_id"] = workspace_id
        query += " ORDER BY event_time DESC, importance DESC LIMIT %(limit)s OFFSET %(offset)s"
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(count_query, params)
                total = cur.fetchone()["total"]
                cur.execute(query, params)
                rows = cur.fetchall()
        return TimelineListResponse(
            items=[TimelineEntryResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

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

    def _get_conflict(
        self, conflict_id: UUID, workspace_id: UUID | None = None
    ) -> ConflictResponse | None:
        workspace_filter = "AND workspace_id = %(workspace_id)s" if workspace_id else ""
        params: dict[str, object] = {"conflict_id": conflict_id}
        if workspace_id:
            params["workspace_id"] = workspace_id
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
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
                    {workspace_filter}
                    """,
                    params,
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

    def _require_workspace(self, cur, workspace_id: UUID) -> None:
        cur.execute(
            "SELECT 1 AS ok FROM workspace WHERE workspace_id = %(workspace_id)s",
            {"workspace_id": workspace_id},
        )
        if cur.fetchone() is None:
            raise WorkspaceNotFoundError(f"workspace {workspace_id} not found")

    def _require_user(self, cur, user_id: UUID) -> None:
        cur.execute(
            "SELECT 1 AS ok FROM user_account WHERE user_id = %(user_id)s",
            {"user_id": user_id},
        )
        if cur.fetchone() is None:
            raise UserNotFoundError(f"user {user_id} not found")

    def _require_forget_target(
        self,
        cur,
        workspace_id: UUID,
        target_type: str,
        target_id: UUID,
    ) -> None:
        target_columns = {
            "memory_item": ("memory_item", "memory_id"),
            "source_document": ("source_document", "doc_id"),
            "wiki_page": ("wiki_page", "page_id"),
        }
        if target_type == "entity":
            if not self._table_exists(cur, "entity"):
                raise UnsupportedForgetTargetError(
                    "entity forget requests require the entity schema extension"
                )
            target_columns["entity"] = ("entity", "entity_id")

        if target_type not in target_columns:
            raise UnsupportedForgetTargetError(f"unsupported forget target type: {target_type}")

        table_name, id_column = target_columns[target_type]
        cur.execute(
            f"""
            SELECT 1 AS ok
            FROM {table_name}
            WHERE {id_column} = %(target_id)s
              AND workspace_id = %(workspace_id)s
            """,
            {"target_id": target_id, "workspace_id": workspace_id},
        )
        if cur.fetchone() is None:
            raise TargetNotFoundError(f"{target_type} {target_id} not found")

    def _table_exists(self, cur, table_name: str) -> bool:
        cur.execute("SELECT to_regclass(%(table_name)s) AS table_name", {"table_name": table_name})
        row = cur.fetchone()
        return row is not None and row["table_name"] is not None

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
