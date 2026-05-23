from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.api.deps import get_governance_service
from app.main import create_app
from app.models.governance import (
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
from app.services.governance_service import ConflictNotFoundError, PolicyNotFoundError
from fastapi.testclient import TestClient


class FakeGovernanceService:
    def __init__(self) -> None:
        now = datetime(2026, 5, 16, tzinfo=timezone.utc)
        self.workspace_id = uuid4()
        self.policy_id = uuid4()
        self.memory_id = uuid4()
        self.conflict_id = uuid4()
        self.doc_id = uuid4()
        self.timeline_id = uuid4()
        self.forget_request_id = uuid4()
        self.policy = PolicyResponse(
            policy_id=self.policy_id,
            workspace_id=self.workspace_id,
            principal_type="role",
            principal_id=None,
            resource_type="memory_item",
            resource_scope="project",
            effect="allow",
            predicate_json={"access_level": "project"},
            created_at=now,
        )
        self.audit_item = AuditEntryResponse(
            audit_id=uuid4(),
            workspace_id=self.workspace_id,
            actor_type="system",
            actor_id=None,
            action_type="memory.update",
            target_type="memory_item",
            target_id=self.memory_id,
            before_json={"status": "active"},
            after_json={"status": "archived"},
            created_at=now,
        )
        self.audit_log = AuditQueryResponse(items=[self.audit_item], page=1, page_size=20, total=1)
        self.conflict = ConflictResponse(
            conflict_id=self.conflict_id,
            workspace_id=self.workspace_id,
            conflict_type="semantic",
            status="open",
            resolution_note=None,
            resolved_by_actor_type=None,
            resolved_by_actor_id=None,
            resolved_at=None,
            created_at=now,
            updated_at=now,
            left_memory_id=self.memory_id,
            left_memory_type="decision",
            left_memory_text="继续推进校园食堂系统。",
            left_memory_summary="旧方案",
            right_memory_id=uuid4(),
            right_memory_type="decision",
            right_memory_text="转向 MemoryBase。",
            right_memory_summary="新方案",
        )
        self.timeline_entry = TimelineEntryResponse(
            timeline_id=self.timeline_id,
            workspace_id=self.workspace_id,
            event_time=now,
            event_type="decision",
            title="项目方向确认",
            description="团队确认以 MemoryBase 为项目主线。",
            importance=5,
            memory_id=self.memory_id,
            doc_id=self.doc_id,
            memory_type="decision",
            memory_text="最终选择 MemoryBase。",
            source_title="meeting_02",
        )
        self.forget_request = ForgetRequestResponse(
            request_id=self.forget_request_id,
            workspace_id=self.workspace_id,
            target_type="memory_item",
            target_id=self.memory_id,
            requester_user_id=uuid4(),
            reviewed_by_user_id=None,
            reason="Remove sensitive memory from recall.",
            status="pending",
            requested_at=now,
            resolved_at=None,
        )

    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        self.policy = self.policy.model_copy(update={"workspace_id": payload.workspace_id})
        return self.policy

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
        if workspace_id is not None and workspace_id != self.workspace_id:
            return PolicyListResponse(items=[], page=page, page_size=page_size, total=0)
        if principal_type is not None and principal_type != self.policy.principal_type:
            return PolicyListResponse(items=[], page=page, page_size=page_size, total=0)
        if principal_id is not None and principal_id != self.policy.principal_id:
            return PolicyListResponse(items=[], page=page, page_size=page_size, total=0)
        if resource_type is not None and resource_type != self.policy.resource_type:
            return PolicyListResponse(items=[], page=page, page_size=page_size, total=0)
        if effect is not None and effect != self.policy.effect:
            return PolicyListResponse(items=[], page=page, page_size=page_size, total=0)
        return PolicyListResponse(items=[self.policy], page=page, page_size=page_size, total=1)

    def update_policy(
        self, *, policy_id: UUID, workspace_id: UUID, payload: PolicyUpdateRequest
    ) -> PolicyResponse:
        if policy_id != self.policy_id or workspace_id != self.workspace_id:
            raise PolicyNotFoundError("policy not found")
        self.policy = self.policy.model_copy(update=payload.model_dump(exclude_unset=True))
        return self.policy

    def delete_policy(self, *, policy_id: UUID, workspace_id: UUID) -> PolicyDeleteResponse:
        if policy_id != self.policy_id or workspace_id != self.workspace_id:
            raise PolicyNotFoundError("policy not found")
        return PolicyDeleteResponse(
            policy_id=policy_id,
            workspace_id=workspace_id,
            deleted=True,
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
        if workspace_id is not None and workspace_id != self.workspace_id:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if actor_id is not None and actor_id != self.audit_item.actor_id:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if actor_type is not None and actor_type != self.audit_item.actor_type:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if action_type is not None and action_type != self.audit_item.action_type:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if target_type is not None and target_type != self.audit_item.target_type:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if target_id is not None and target_id != self.audit_item.target_id:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if start_time is not None and self.audit_item.created_at < start_time:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if end_time is not None and self.audit_item.created_at > end_time:
            return AuditQueryResponse(items=[], page=page, page_size=page_size, total=0)
        if include_diff:
            diff_item = self.audit_item.model_copy(
                update={"diff_json": {"status": {"before": "active", "after": "archived"}}}
            )
            return AuditQueryResponse(items=[diff_item], page=page, page_size=page_size, total=1)
        return self.audit_log

    def list_audit_lifecycle(
        self, *, workspace_id: UUID, target_type: str, target_id: UUID
    ) -> AuditLifecycleResponse:
        return AuditLifecycleResponse(
            items=[
                {
                    "ts": self.audit_item.created_at,
                    "kind": "audit",
                    "payload": self.audit_item.model_dump(mode="json"),
                }
            ]
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
        return self.audit_log

    def get_audit_statistics(
        self, *, workspace_id: UUID | None, group_by: str
    ) -> AuditStatisticsResponse:
        return AuditStatisticsResponse(
            group_by=group_by,
            items=[
                AuditStatisticResponse(
                    group_key="memory.update",
                    event_count=1,
                    last_event_at=self.audit_item.created_at,
                )
            ],
        )

    def list_conflicts(
        self, *, workspace_id: UUID | None, status: str | None, page: int, page_size: int
    ) -> ConflictListResponse:
        if workspace_id is not None and workspace_id != self.workspace_id:
            return ConflictListResponse(items=[], page=page, page_size=page_size, total=0)
        if status is not None and status != self.conflict.status:
            return ConflictListResponse(items=[], page=page, page_size=page_size, total=0)
        return ConflictListResponse(items=[self.conflict], page=page, page_size=page_size, total=1)

    def create_conflict(self, payload: ConflictCreateRequest) -> ConflictResponse:
        self.conflict = self.conflict.model_copy(
            update={
                "workspace_id": payload.workspace_id,
                "left_memory_id": payload.left_memory_id,
                "right_memory_id": payload.right_memory_id,
                "conflict_type": payload.conflict_type,
                "resolution_note": payload.resolution_note,
            }
        )
        return self.conflict

    def update_conflict(
        self, conflict_id: UUID, workspace_id: UUID, payload: ConflictUpdateRequest
    ) -> ConflictResponse:
        if conflict_id != self.conflict_id or workspace_id != self.workspace_id:
            raise ConflictNotFoundError(f"conflict {conflict_id} not found")
        self.conflict = self.conflict.model_copy(
            update={
                "status": payload.status,
                "resolution_note": payload.resolution_note,
                "resolved_by_actor_type": payload.actor_type,
                "resolved_by_actor_id": payload.actor_id,
                "resolved_at": datetime(2026, 5, 17, tzinfo=timezone.utc),
            }
        )
        return self.conflict

    def list_agent_visible_memories(
        self, *, agent_id: UUID, workspace_id: UUID, page: int, page_size: int
    ) -> AgentVisibleMemoryListResponse:
        item = AgentVisibleMemoryResponse(
            memory_id=self.memory_id,
            workspace_id=workspace_id,
            memory_type="decision",
            canonical_text="Visible project memory.",
            summary="Visible",
            confidence=0.9,
            importance=4,
            status="active",
            access_level="project",
            updated_at=self.audit_item.created_at,
        )
        return AgentVisibleMemoryListResponse(items=[item], page=page, page_size=page_size, total=1)

    def list_timeline(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> TimelineListResponse:
        if workspace_id is not None and workspace_id != self.workspace_id:
            return TimelineListResponse(items=[], page=page, page_size=page_size, total=0)
        return TimelineListResponse(
            items=[self.timeline_entry], page=page, page_size=page_size, total=1
        )

    def create_timeline_entry(self, payload: TimelineCreateRequest) -> TimelineEntryResponse:
        self.timeline_entry = self.timeline_entry.model_copy(
            update={
                "workspace_id": payload.workspace_id,
                "title": payload.title,
                "event_type": payload.event_type,
                "event_time": payload.event_time,
                "description": payload.description,
                "importance": payload.importance,
                "memory_id": payload.memory_id,
                "doc_id": payload.doc_id,
            }
        )
        return self.timeline_entry

    def create_forget_request(self, payload: ForgetRequestCreateRequest) -> ForgetRequestResponse:
        self.forget_request = self.forget_request.model_copy(
            update={
                "workspace_id": payload.workspace_id,
                "target_type": payload.target_type,
                "target_id": payload.target_id,
                "requester_user_id": payload.requester_user_id,
                "reason": payload.reason,
                "status": "pending",
            }
        )
        return self.forget_request

    def list_forget_requests(
        self,
        *,
        workspace_id: UUID | None,
        status: str | None,
        target_type: str | None,
        page: int,
        page_size: int,
    ) -> ForgetRequestListResponse:
        if workspace_id is not None and workspace_id != self.workspace_id:
            return ForgetRequestListResponse(items=[], page=page, page_size=page_size, total=0)
        if status is not None and status != self.forget_request.status:
            return ForgetRequestListResponse(items=[], page=page, page_size=page_size, total=0)
        if target_type is not None and target_type != self.forget_request.target_type:
            return ForgetRequestListResponse(items=[], page=page, page_size=page_size, total=0)
        return ForgetRequestListResponse(
            items=[self.forget_request], page=page, page_size=page_size, total=1
        )

    def update_forget_request(
        self, request_id: UUID, workspace_id: UUID, payload: ForgetRequestUpdateRequest
    ) -> ForgetRequestResponse:
        reviewed_by_user_id = payload.reviewed_by_user_id if payload.status != "pending" else None
        self.forget_request = self.forget_request.model_copy(
            update={
                "request_id": request_id,
                "workspace_id": workspace_id,
                "status": payload.status,
                "reviewed_by_user_id": reviewed_by_user_id,
                "resolved_at": datetime(2026, 5, 17, tzinfo=timezone.utc)
                if payload.status != "pending"
                else None,
            }
        )
        return self.forget_request


def build_client() -> tuple[TestClient, FakeGovernanceService]:
    app = create_app()
    fake_service = FakeGovernanceService()
    app.dependency_overrides[get_governance_service] = lambda: fake_service
    return TestClient(app), fake_service


def test_create_policy_returns_created_policy() -> None:
    client, fake_service = build_client()

    response = client.post(
        "/api/policies",
        json={
            "workspace_id": str(fake_service.workspace_id),
            "principal_type": "role",
            "resource_type": "memory_item",
            "resource_scope": "project",
            "effect": "allow",
            "predicate_json": {"access_level": "project"},
        },
    )

    assert response.status_code == 201
    assert response.json()["effect"] == "allow"


def test_list_policies_returns_items() -> None:
    client, fake_service = build_client()

    response = client.get("/api/policies", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_policies_applies_governance_filters() -> None:
    client, fake_service = build_client()

    response = client.get(
        "/api/policies",
        params={
            "workspace_id": str(fake_service.workspace_id),
            "principal_type": "role",
            "resource_type": "memory_item",
            "effect": "deny",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_update_and_delete_policy_routes() -> None:
    client, fake_service = build_client()

    update_response = client.patch(
        f"/api/policies/{fake_service.policy_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
        json={"effect": "deny", "predicate_json": {"reason": "test"}},
    )
    delete_response = client.delete(
        f"/api/policies/{fake_service.policy_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
    )

    assert update_response.status_code == 200
    assert update_response.json()["effect"] == "deny"
    assert update_response.json()["predicate_json"] == {"reason": "test"}
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


def test_list_audit_returns_logs() -> None:
    client, fake_service = build_client()

    response = client.get("/api/audit", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["items"][0]["action_type"] == "memory.update"
    assert response.json()["total"] == 1


def test_audit_diff_lifecycle_actor_timeline_and_statistics_routes() -> None:
    client, fake_service = build_client()

    diff_response = client.get(
        "/api/audit",
        params={
            "workspace_id": str(fake_service.workspace_id),
            "include_diff": "true",
        },
    )
    assert diff_response.status_code == 200
    assert "status" in diff_response.json()["items"][0]["diff_json"]

    lifecycle_response = client.get(
        "/api/audit/lifecycle",
        params={
            "workspace_id": str(fake_service.workspace_id),
            "target_type": "memory_item",
            "target_id": str(fake_service.memory_id),
        },
    )
    assert lifecycle_response.status_code == 200
    assert lifecycle_response.json()["items"][0]["kind"] == "audit"

    actor_response = client.get(
        f"/api/audit/actors/system/{fake_service.memory_id}/timeline",
        params={"workspace_id": str(fake_service.workspace_id)},
    )
    assert actor_response.status_code == 200

    statistics_response = client.get(
        "/api/audit/statistics",
        params={"workspace_id": str(fake_service.workspace_id), "group_by": "action_type"},
    )
    assert statistics_response.status_code == 200
    assert statistics_response.json()["items"][0]["group_key"] == "memory.update"


def test_list_conflicts_returns_records() -> None:
    client, fake_service = build_client()

    response = client.get("/api/conflicts", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "open"
    assert response.json()["items"][0]["left_memory_text"] == "继续推进校园食堂系统。"


def test_list_conflicts_filters_by_status() -> None:
    client, fake_service = build_client()

    response = client.get(
        "/api/conflicts",
        params={
            "workspace_id": str(fake_service.workspace_id),
            "status": "resolved",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_create_conflict_returns_created_conflict() -> None:
    client, fake_service = build_client()

    response = client.post(
        "/api/conflicts",
        json={
            "workspace_id": str(fake_service.workspace_id),
            "left_memory_id": str(fake_service.memory_id),
            "right_memory_id": str(uuid4()),
            "conflict_type": "contradiction",
            "resolution_note": "route test",
        },
    )

    assert response.status_code == 201
    assert response.json()["conflict_type"] == "contradiction"


def test_agent_visible_memories_route() -> None:
    client, fake_service = build_client()

    response = client.get(
        f"/api/agents/{uuid4()}/visible-memories",
        params={"workspace_id": str(fake_service.workspace_id)},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["access_level"] == "project"


def test_update_conflict_returns_new_status() -> None:
    client, fake_service = build_client()

    response = client.patch(
        f"/api/conflicts/{fake_service.conflict_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
        json={"status": "resolved", "resolution_note": "accepted new direction"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def test_list_timeline_returns_entries() -> None:
    client, fake_service = build_client()

    response = client.get("/api/timeline", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "项目方向确认"


def test_create_timeline_entry_returns_created_item() -> None:
    client, fake_service = build_client()

    response = client.post(
        "/api/timeline",
        json={
            "workspace_id": str(fake_service.workspace_id),
            "title": "完成后端闭环",
            "event_type": "revision",
            "event_time": "2026-05-16T08:00:00Z",
            "description": "补齐 revision、recall 和 wiki 导出。",
            "importance": 4,
            "memory_id": str(fake_service.memory_id),
            "doc_id": str(fake_service.doc_id),
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "完成后端闭环"


def test_create_forget_request_returns_pending_request() -> None:
    client, fake_service = build_client()
    requester_user_id = uuid4()

    response = client.post(
        "/api/forget-requests",
        json={
            "workspace_id": str(fake_service.workspace_id),
            "target_type": "memory_item",
            "target_id": str(fake_service.memory_id),
            "requester_user_id": str(requester_user_id),
            "reason": "Remove sensitive memory from recall.",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert response.json()["target_id"] == str(fake_service.memory_id)


def test_list_forget_requests_returns_page() -> None:
    client, fake_service = build_client()

    response = client.get(
        "/api/forget-requests",
        params={
            "workspace_id": str(fake_service.workspace_id),
            "status": "pending",
            "target_type": "memory_item",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["request_id"] == str(fake_service.forget_request_id)


def test_update_forget_request_returns_reviewed_request() -> None:
    client, fake_service = build_client()
    reviewer_id = uuid4()

    response = client.patch(
        f"/api/forget-requests/{fake_service.forget_request_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
        json={"status": "approved", "reviewed_by_user_id": str(reviewer_id)},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["reviewed_by_user_id"] == str(reviewer_id)
    assert response.json()["resolved_at"] is not None


def test_update_forget_request_accepts_pending_with_stale_reviewer() -> None:
    client, fake_service = build_client()

    response = client.patch(
        f"/api/forget-requests/{fake_service.forget_request_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
        json={"status": "pending", "reviewed_by_user_id": str(uuid4())},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["reviewed_by_user_id"] is None


def test_update_forget_request_requires_reviewer_for_terminal_status() -> None:
    client, fake_service = build_client()

    response = client.patch(
        f"/api/forget-requests/{fake_service.forget_request_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
        json={"status": "approved"},
    )

    assert response.status_code == 422
