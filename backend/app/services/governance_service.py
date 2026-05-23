from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..core.database import Database
from ..models.governance import (
    AgentVisibleMemoryListResponse,
    AgentVisibleMemoryResponse,
    AuditEntryResponse,
    AuditLifecycleResponse,
    AuditQueryResponse,
    AuditStatisticResponse,
    AuditStatisticsResponse,
    ConflictCreateRequest,
    ConflictListResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    ForgetRequestCreateRequest,
    ForgetRequestListResponse,
    ForgetRequestResponse,
    ForgetRequestUpdateRequest,
    PolicyCreateRequest,
    PolicyDeleteResponse,
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdateRequest,
    TimelineCreateRequest,
    TimelineEntryResponse,
    TimelineListResponse,
)


class WorkspaceNotFoundError(Exception):
    pass


class ConflictNotFoundError(Exception):
    pass


class ConflictAlreadyExistsError(Exception):
    pass


class ConflictValidationError(Exception):
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


class PolicyNotFoundError(Exception):
    pass


class GovernanceRepository(Protocol):
    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        ...

    def list_policies(
        self,
        *,
        workspace_id: UUID | None,
        principal_type: str | None,
        principal_id: UUID | None,
        resource_type: str | None,
        effect: str | None,
        page: int,
        page_size: int,
    ) -> PolicyListResponse:
        ...

    def update_policy(
        self, *, policy_id: UUID, workspace_id: UUID, payload: PolicyUpdateRequest
    ) -> PolicyResponse:
        ...

    def delete_policy(self, *, policy_id: UUID, workspace_id: UUID) -> PolicyDeleteResponse:
        ...

    def list_audit_logs(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str | None,
        actor_id: UUID | None,
        action_type: str | None,
        target_type: str | None,
        target_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
        sort: str,
        include_diff: bool,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        ...

    def list_audit_lifecycle(
        self, *, workspace_id: UUID, target_type: str, target_id: UUID
    ) -> AuditLifecycleResponse:
        ...

    def list_actor_timeline(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str,
        actor_id: UUID,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        ...

    def get_audit_statistics(
        self, *, workspace_id: UUID | None, group_by: str
    ) -> AuditStatisticsResponse:
        ...

    def list_conflicts(
        self, *, workspace_id: UUID | None, status: str | None, page: int, page_size: int
    ) -> ConflictListResponse:
        ...

    def create_conflict(self, payload: ConflictCreateRequest) -> ConflictResponse:
        ...

    def update_conflict(
        self, conflict_id: UUID, workspace_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse | None:
        ...

    def list_agent_visible_memories(
        self, *, agent_id: UUID, workspace_id: UUID, page: int, page_size: int
    ) -> AgentVisibleMemoryListResponse:
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
        self,
        *,
        workspace_id: UUID | None,
        principal_type: str | None,
        principal_id: UUID | None,
        resource_type: str | None,
        effect: str | None,
        page: int,
        page_size: int,
    ) -> PolicyListResponse:
        return self.repository.list_policies(
            workspace_id=workspace_id,
            principal_type=principal_type,
            principal_id=principal_id,
            resource_type=resource_type,
            effect=effect,
            page=page,
            page_size=page_size,
        )

    def update_policy(
        self, *, policy_id: UUID, workspace_id: UUID, payload: PolicyUpdateRequest
    ) -> PolicyResponse:
        return self.repository.update_policy(
            policy_id=policy_id, workspace_id=workspace_id, payload=payload
        )

    def delete_policy(self, *, policy_id: UUID, workspace_id: UUID) -> PolicyDeleteResponse:
        return self.repository.delete_policy(policy_id=policy_id, workspace_id=workspace_id)

    def list_audit_logs(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str | None,
        actor_id: UUID | None,
        action_type: str | None,
        target_type: str | None,
        target_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
        sort: str,
        include_diff: bool,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        return self.repository.list_audit_logs(
            workspace_id=workspace_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
            include_diff=include_diff,
            page=page,
            page_size=page_size,
        )

    def list_audit_lifecycle(
        self, *, workspace_id: UUID, target_type: str, target_id: UUID
    ) -> AuditLifecycleResponse:
        return self.repository.list_audit_lifecycle(
            workspace_id=workspace_id,
            target_type=target_type,
            target_id=target_id,
        )

    def list_actor_timeline(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str,
        actor_id: UUID,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        return self.repository.list_actor_timeline(
            workspace_id=workspace_id,
            actor_type=actor_type,
            actor_id=actor_id,
            page=page,
            page_size=page_size,
        )

    def get_audit_statistics(
        self, *, workspace_id: UUID | None, group_by: str
    ) -> AuditStatisticsResponse:
        return self.repository.get_audit_statistics(workspace_id=workspace_id, group_by=group_by)

    def list_conflicts(
        self, *, workspace_id: UUID | None, status: str | None, page: int, page_size: int
    ) -> ConflictListResponse:
        return self.repository.list_conflicts(
            workspace_id=workspace_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    def create_conflict(self, payload: ConflictCreateRequest) -> ConflictResponse:
        return self.repository.create_conflict(payload)

    def update_conflict(
        self, conflict_id: UUID, workspace_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse:
        conflict = self.repository.update_conflict(conflict_id, workspace_id, payload)
        if conflict is None:
            raise ConflictNotFoundError(f"conflict {conflict_id} not found")
        return conflict

    def list_agent_visible_memories(
        self, *, agent_id: UUID, workspace_id: UUID, page: int, page_size: int
    ) -> AgentVisibleMemoryListResponse:
        return self.repository.list_agent_visible_memories(
            agent_id=agent_id,
            workspace_id=workspace_id,
            page=page,
            page_size=page_size,
        )

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
        self,
        *,
        workspace_id: UUID | None,
        principal_type: str | None,
        principal_id: UUID | None,
        resource_type: str | None,
        effect: str | None,
        page: int,
        page_size: int,
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
        where_parts: list[str] = []
        if workspace_id is not None:
            where_parts.append("workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        if principal_type is not None:
            where_parts.append("principal_type = %(principal_type)s")
            params["principal_type"] = principal_type
        if principal_id is not None:
            where_parts.append("principal_id = %(principal_id)s")
            params["principal_id"] = principal_id
        if resource_type is not None:
            where_parts.append("resource_type = %(resource_type)s")
            params["resource_type"] = resource_type
        if effect is not None:
            where_parts.append("effect = %(effect)s")
            params["effect"] = effect
        if where_parts:
            where_clause = " WHERE " + " AND ".join(where_parts)
            query += where_clause
            count_query += where_clause
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

    def update_policy(
        self, *, policy_id: UUID, workspace_id: UUID, payload: PolicyUpdateRequest
    ) -> PolicyResponse:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            with self._database.connection() as conn:
                with conn.cursor() as cur:
                    row = self._fetch_policy(cur, policy_id=policy_id, workspace_id=workspace_id)
            if row is None:
                raise PolicyNotFoundError("policy not found")
            return PolicyResponse(**row)

        assignments: list[str] = []
        params: dict[str, object] = {"policy_id": policy_id, "workspace_id": workspace_id}
        for field, value in updates.items():
            if field == "predicate_json":
                assignments.append("predicate_json = %(predicate_json)s::jsonb")
                params["predicate_json"] = _json_dumps(value)
            else:
                assignments.append(f"{field} = %({field})s")
                params[field] = value

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                before = self._fetch_policy(cur, policy_id=policy_id, workspace_id=workspace_id)
                if before is None:
                    raise PolicyNotFoundError("policy not found")
                cur.execute(
                    f"""
                    UPDATE access_policy
                    SET {", ".join(assignments)}
                    WHERE policy_id = %(policy_id)s
                      AND workspace_id = %(workspace_id)s
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
                    params,
                )
                after = cur.fetchone()
                if after is None:
                    raise PolicyNotFoundError("policy not found")
                self._insert_audit(
                    cur,
                    workspace_id=workspace_id,
                    action_type="policy.update",
                    target_id=policy_id,
                    before_json=_policy_audit_payload(before),
                    after_json=_policy_audit_payload(after),
                )
            conn.commit()
        return PolicyResponse(**after)

    def delete_policy(self, *, policy_id: UUID, workspace_id: UUID) -> PolicyDeleteResponse:
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                before = self._fetch_policy(cur, policy_id=policy_id, workspace_id=workspace_id)
                if before is None:
                    raise PolicyNotFoundError("policy not found")
                cur.execute(
                    """
                    DELETE FROM access_policy
                    WHERE policy_id = %(policy_id)s
                      AND workspace_id = %(workspace_id)s
                    """,
                    {"policy_id": policy_id, "workspace_id": workspace_id},
                )
                self._insert_audit(
                    cur,
                    workspace_id=workspace_id,
                    action_type="policy.delete",
                    target_id=policy_id,
                    before_json=_policy_audit_payload(before),
                    after_json=None,
                )
            conn.commit()
        return PolicyDeleteResponse(policy_id=policy_id, workspace_id=workspace_id, deleted=True)

    def _fetch_policy(self, cur: object, *, policy_id: UUID, workspace_id: UUID) -> dict | None:
        cur.execute(
            """
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
            WHERE policy_id = %(policy_id)s
              AND workspace_id = %(workspace_id)s
            """,
            {"policy_id": policy_id, "workspace_id": workspace_id},
        )
        return cur.fetchone()

    def _insert_audit(
        self,
        cur: object,
        *,
        workspace_id: UUID,
        action_type: str,
        target_id: UUID,
        before_json: dict | None,
        after_json: dict | None,
    ) -> None:
        cur.execute(
            """
            INSERT INTO audit_log (
                workspace_id,
                actor_type,
                action_type,
                target_type,
                target_id,
                before_json,
                after_json
            )
            VALUES (
                %(workspace_id)s,
                'system',
                %(action_type)s,
                'access_policy',
                %(target_id)s,
                %(before_json)s::jsonb,
                %(after_json)s::jsonb
            )
            """,
            {
                "workspace_id": workspace_id,
                "action_type": action_type,
                "target_id": target_id,
                "before_json": _json_dumps(before_json) if before_json is not None else None,
                "after_json": _json_dumps(after_json) if after_json is not None else None,
            },
        )

    def list_audit_logs(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str | None,
        actor_id: UUID | None,
        action_type: str | None,
        target_type: str | None,
        target_id: UUID | None,
        start_time: datetime | None,
        end_time: datetime | None,
        sort: str,
        include_diff: bool,
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
        if actor_id is not None:
            filters.append("actor_id = %(actor_id)s")
            params["actor_id"] = actor_id
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
        order_direction = "ASC" if sort == "asc" else "DESC"
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
                    ORDER BY created_at {order_direction}
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = cur.fetchall()
        return AuditQueryResponse(
            items=[
                AuditEntryResponse(
                    **row,
                    diff_json=_json_diff(row["before_json"], row["after_json"])
                    if include_diff
                    else None,
                )
                for row in rows
            ],
            page=page,
            page_size=page_size,
            total=total,
        )

    def list_audit_lifecycle(
        self, *, workspace_id: UUID, target_type: str, target_id: UUID
    ) -> AuditLifecycleResponse:
        if not self._workspace_exists(workspace_id):
            raise WorkspaceNotFoundError(f"workspace {workspace_id} not found")

        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ts, kind, payload
                    FROM (
                      SELECT
                        created_at AS ts,
                        'audit' AS kind,
                        jsonb_build_object(
                          'audit_id', audit_id,
                          'actor_type', actor_type,
                          'actor_id', actor_id,
                          'action_type', action_type,
                          'target_type', target_type,
                          'target_id', target_id,
                          'before_json', before_json,
                          'after_json', after_json
                        ) AS payload
                      FROM audit_log
                      WHERE workspace_id = %(workspace_id)s
                        AND target_type = %(target_type)s
                        AND target_id = %(target_id)s

                      UNION ALL

                      SELECT
                        mr.created_at AS ts,
                        'revision' AS kind,
                        jsonb_build_object(
                          'memory_id', mr.memory_id,
                          'revision_no', mr.revision_no,
                          'revision_reason', mr.revision_reason,
                          'editor_type', mr.editor_type,
                          'editor_id', mr.editor_id,
                          'revision_summary', mr.revision_summary
                        ) AS payload
                      FROM memory_revision mr
                      JOIN memory_item mi ON mi.memory_id = mr.memory_id
                      WHERE %(target_type)s = 'memory_item'
                        AND mi.workspace_id = %(workspace_id)s
                        AND mr.memory_id = %(target_id)s

                      UNION ALL

                      SELECT
                        cr.created_at AS ts,
                        'conflict' AS kind,
                        jsonb_build_object(
                          'conflict_id', cr.conflict_id,
                          'conflict_type', cr.conflict_type,
                          'status', cr.status,
                          'left_memory_id', cr.left_memory_id,
                          'right_memory_id', cr.right_memory_id,
                          'resolution_note', cr.resolution_note,
                          'resolved_at', cr.resolved_at
                        ) AS payload
                      FROM conflict_record cr
                      WHERE %(target_type)s = 'memory_item'
                        AND cr.workspace_id = %(workspace_id)s
                        AND (
                          cr.left_memory_id = %(target_id)s
                          OR cr.right_memory_id = %(target_id)s
                        )

                      UNION ALL

                      SELECT
                        fr.requested_at AS ts,
                        'forget_request' AS kind,
                        jsonb_build_object(
                          'request_id', fr.request_id,
                          'target_type', fr.target_type,
                          'target_id', fr.target_id,
                          'requester_user_id', fr.requester_user_id,
                          'reviewed_by_user_id', fr.reviewed_by_user_id,
                          'status', fr.status,
                          'reason', fr.reason,
                          'resolved_at', fr.resolved_at
                        ) AS payload
                      FROM forget_request fr
                      WHERE fr.workspace_id = %(workspace_id)s
                        AND fr.target_type = %(target_type)s
                        AND fr.target_id = %(target_id)s
                    ) lifecycle
                    ORDER BY ts ASC
                    """,
                    {
                        "workspace_id": workspace_id,
                        "target_type": target_type,
                        "target_id": target_id,
                    },
                )
                rows = cur.fetchall()
        return AuditLifecycleResponse(items=rows)

    def list_actor_timeline(
        self,
        *,
        workspace_id: UUID | None,
        actor_type: str,
        actor_id: UUID,
        page: int,
        page_size: int,
    ) -> AuditQueryResponse:
        return self.list_audit_logs(
            workspace_id=workspace_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action_type=None,
            target_type=None,
            target_id=None,
            start_time=None,
            end_time=None,
            sort="desc",
            include_diff=False,
            page=page,
            page_size=page_size,
        )

    def get_audit_statistics(
        self, *, workspace_id: UUID | None, group_by: str
    ) -> AuditStatisticsResponse:
        allowed_group_by = {"action_type", "actor_type", "target_type"}
        if group_by not in allowed_group_by:
            raise ValueError(f"unsupported audit group_by: {group_by}")
        filters = []
        params: dict[str, object] = {}
        if workspace_id is not None:
            filters.append("workspace_id = %(workspace_id)s")
            params["workspace_id"] = workspace_id
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                      {group_by}::text AS group_key,
                      count(*) AS event_count,
                      max(created_at) AS last_event_at
                    FROM audit_log
                    {where_clause}
                    GROUP BY {group_by}
                    ORDER BY event_count DESC, group_key ASC
                    """,
                    params,
                )
                rows = cur.fetchall()
        return AuditStatisticsResponse(
            group_by=group_by,
            items=[AuditStatisticResponse(**row) for row in rows],
        )

    def list_conflicts(
        self, *, workspace_id: UUID | None, status: str | None, page: int, page_size: int
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
        if status is not None:
            clause = " AND" if " WHERE " in query else " WHERE"
            query += f"{clause} status = %(status)s"
            count_clause = " AND" if " WHERE " in count_query else " WHERE"
            count_query += f"{count_clause} status = %(status)s"
            params["status"] = status
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

    def create_conflict(self, payload: ConflictCreateRequest) -> ConflictResponse:
        if payload.left_memory_id == payload.right_memory_id:
            raise ConflictValidationError("conflict memories must be different")

        left_memory_id, right_memory_id = _normalize_memory_pair(
            payload.left_memory_id, payload.right_memory_id
        )
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                self._require_memory_in_workspace(cur, payload.workspace_id, left_memory_id)
                self._require_memory_in_workspace(cur, payload.workspace_id, right_memory_id)
                cur.execute(
                    """
                    SELECT conflict_id
                    FROM conflict_record
                    WHERE left_memory_id = %(left_memory_id)s
                      AND right_memory_id = %(right_memory_id)s
                    """,
                    {
                        "left_memory_id": left_memory_id,
                        "right_memory_id": right_memory_id,
                    },
                )
                if cur.fetchone() is not None:
                    raise ConflictAlreadyExistsError("conflict already exists for this pair")

                self._set_actor_context(
                    cur,
                    actor_type=payload.actor_type,
                    actor_id=payload.actor_id,
                    revision_reason="conflict created",
                )
                cur.execute(
                    """
                    INSERT INTO conflict_record (
                        workspace_id,
                        left_memory_id,
                        right_memory_id,
                        conflict_type,
                        status,
                        resolution_note
                    )
                    VALUES (
                        %(workspace_id)s,
                        %(left_memory_id)s,
                        %(right_memory_id)s,
                        %(conflict_type)s,
                        'open',
                        %(resolution_note)s
                    )
                    RETURNING conflict_id
                    """,
                    {
                        "workspace_id": payload.workspace_id,
                        "left_memory_id": left_memory_id,
                        "right_memory_id": right_memory_id,
                        "conflict_type": payload.conflict_type,
                        "resolution_note": payload.resolution_note,
                    },
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("failed to create conflict")
                conflict_id = row["conflict_id"]

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
                    SELECT
                        workspace_id,
                        %(actor_type)s,
                        %(actor_id)s,
                        'conflict.create',
                        'conflict_record',
                        conflict_id,
                        to_jsonb(conflict_record)
                    FROM conflict_record
                    WHERE conflict_id = %(conflict_id)s
                    """,
                    {
                        "actor_type": payload.actor_type,
                        "actor_id": payload.actor_id,
                        "conflict_id": conflict_id,
                    },
                )
            conn.commit()
        conflict = self._get_conflict(conflict_id, payload.workspace_id)
        if conflict is None:
            raise RuntimeError("created conflict cannot be loaded")
        return conflict

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

                self._set_actor_context(
                    cur,
                    actor_type=payload.actor_type,
                    actor_id=payload.actor_id,
                    revision_reason=f"conflict {payload.status}",
                )

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

    def list_agent_visible_memories(
        self, *, agent_id: UUID, workspace_id: UUID, page: int, page_size: int
    ) -> AgentVisibleMemoryListResponse:
        params: dict[str, object] = {
            "agent_id": agent_id,
            "workspace_id": workspace_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        with self._database.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*) AS total
                    FROM v_agent_visible_memory
                    WHERE agent_id = %(agent_id)s
                      AND workspace_id = %(workspace_id)s
                    """,
                    params,
                )
                total = cur.fetchone()["total"]
                cur.execute(
                    """
                    SELECT
                        memory_id,
                        workspace_id,
                        memory_type,
                        canonical_text,
                        summary,
                        confidence,
                        importance,
                        status,
                        access_level,
                        updated_at
                    FROM v_agent_visible_memory
                    WHERE agent_id = %(agent_id)s
                      AND workspace_id = %(workspace_id)s
                    ORDER BY updated_at DESC
                    LIMIT %(limit)s OFFSET %(offset)s
                    """,
                    params,
                )
                rows = cur.fetchall()
        return AgentVisibleMemoryListResponse(
            items=[AgentVisibleMemoryResponse(**row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

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

                reviewed_by_user_id = (
                    payload.reviewed_by_user_id if payload.status != "pending" else None
                )
                if (
                    before_row["status"] == payload.status
                    and before_row["reviewed_by_user_id"] == reviewed_by_user_id
                ):
                    return ForgetRequestResponse(**before_row)

                actor_type = "user" if reviewed_by_user_id is not None else "system"
                self._set_actor_context(
                    cur,
                    actor_type=actor_type,
                    actor_id=reviewed_by_user_id,
                    revision_reason=f"forget request {payload.status}",
                )

                if payload.status in {"approved", "done"}:
                    self._require_forget_target(
                        cur,
                        workspace_id,
                        before_row["target_type"],
                        before_row["target_id"],
                    )
                    if before_row["target_type"] == "memory_item":
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
                    else:
                        self._soft_forget_governed_target(
                            cur,
                            workspace_id=workspace_id,
                            target_type=before_row["target_type"],
                            target_id=before_row["target_id"],
                            actor_type=actor_type,
                            actor_id=reviewed_by_user_id,
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
                        "reviewed_by_user_id": reviewed_by_user_id,
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
                        "actor_id": reviewed_by_user_id,
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

    def _require_memory_in_workspace(self, cur, workspace_id: UUID, memory_id: UUID) -> None:
        cur.execute(
            """
            SELECT 1 AS ok
            FROM memory_item
            WHERE memory_id = %(memory_id)s
              AND workspace_id = %(workspace_id)s
            """,
            {"memory_id": memory_id, "workspace_id": workspace_id},
        )
        if cur.fetchone() is None:
            raise TargetNotFoundError(f"memory_item {memory_id} not found")

    def _soft_forget_governed_target(
        self,
        cur,
        *,
        workspace_id: UUID,
        target_type: str,
        target_id: UUID,
        actor_type: str,
        actor_id: UUID | None,
    ) -> None:
        target_columns = {
            "source_document": ("source_document", "doc_id", "source_document.forget"),
            "wiki_page": ("wiki_page", "page_id", "wiki_page.forget"),
            "entity": ("entity", "entity_id", "entity.forget"),
        }
        if target_type not in target_columns:
            raise UnsupportedForgetTargetError(f"unsupported soft forget target: {target_type}")

        table_name, id_column, action_type = target_columns[target_type]
        cur.execute(
            f"""
            SELECT *
            FROM {table_name}
            WHERE {id_column} = %(target_id)s
              AND workspace_id = %(workspace_id)s
            FOR UPDATE
            """,
            {"target_id": target_id, "workspace_id": workspace_id},
        )
        before_row = cur.fetchone()
        if before_row is None:
            raise TargetNotFoundError(f"{target_type} {target_id} not found")
        if before_row["status"] == "forgotten":
            return

        cur.execute(
            f"""
            UPDATE {table_name}
            SET status = 'forgotten',
                forgotten_at = coalesce(forgotten_at, now())
            WHERE {id_column} = %(target_id)s
              AND workspace_id = %(workspace_id)s
            RETURNING *
            """,
            {"target_id": target_id, "workspace_id": workspace_id},
        )
        after_row = cur.fetchone()
        if after_row is None:
            raise RuntimeError(f"failed to forget {target_type} {target_id}")

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
                %(action_type)s,
                %(target_type)s,
                %(target_id)s,
                %(before_json)s::jsonb,
                %(after_json)s::jsonb
            )
            """,
            {
                "workspace_id": workspace_id,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "action_type": action_type,
                "target_type": target_type,
                "target_id": target_id,
                "before_json": _json_dumps(before_row),
                "after_json": _json_dumps(after_row),
            },
        )

    def _set_actor_context(
        self,
        cur,
        *,
        actor_type: str,
        actor_id: UUID | None,
        revision_reason: str,
    ) -> None:
        cur.execute(
            "SELECT set_config('app.actor_type', %(actor_type)s, true)",
            {"actor_type": actor_type},
        )
        cur.execute(
            "SELECT set_config('app.actor_id', %(actor_id)s, true)",
            {"actor_id": str(actor_id) if actor_id is not None else ""},
        )
        cur.execute(
            "SELECT set_config('app.revision_reason', %(revision_reason)s, true)",
            {"revision_reason": revision_reason},
        )

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


def _policy_audit_payload(row: dict[str, object]) -> dict[str, object]:
    return {
        "policy_id": row["policy_id"],
        "workspace_id": row["workspace_id"],
        "principal_type": row["principal_type"],
        "principal_id": row["principal_id"],
        "resource_type": row["resource_type"],
        "resource_scope": row["resource_scope"],
        "effect": row["effect"],
        "predicate_json": row["predicate_json"],
        "created_at": row["created_at"],
    }


def _normalize_memory_pair(left_memory_id: UUID, right_memory_id: UUID) -> tuple[UUID, UUID]:
    if left_memory_id.int < right_memory_id.int:
        return left_memory_id, right_memory_id
    return right_memory_id, left_memory_id


def _json_diff(
    before_json: dict[str, object] | None, after_json: dict[str, object] | None
) -> dict[str, dict[str, object | None]]:
    before = before_json or {}
    after = after_json or {}
    keys = set(before) | set(after)
    return {
        key: {"before": before.get(key), "after": after.get(key)}
        for key in sorted(keys)
        if before.get(key) != after.get(key)
    }
