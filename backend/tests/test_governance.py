from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.api.deps import get_governance_service
from app.main import create_app
from app.models.governance import (
    AuditEntryResponse,
    AuditQueryResponse,
    ConflictListResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    PolicyCreateRequest,
    PolicyListResponse,
    PolicyResponse,
    TimelineCreateRequest,
    TimelineEntryResponse,
    TimelineListResponse,
)
from app.services.governance_service import ConflictNotFoundError
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

    def create_policy(self, payload: PolicyCreateRequest) -> PolicyResponse:
        self.policy = self.policy.model_copy(update={"workspace_id": payload.workspace_id})
        return self.policy

    def list_policies(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> PolicyListResponse:
        if workspace_id is not None and workspace_id != self.workspace_id:
            return PolicyListResponse(items=[], page=page, page_size=page_size, total=0)
        return PolicyListResponse(items=[self.policy], page=page, page_size=page_size, total=1)

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
        if workspace_id is not None and workspace_id != self.workspace_id:
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
        return self.audit_log

    def list_conflicts(
        self, *, workspace_id: UUID | None, page: int, page_size: int
    ) -> ConflictListResponse:
        if workspace_id is not None and workspace_id != self.workspace_id:
            return ConflictListResponse(items=[], page=page, page_size=page_size, total=0)
        return ConflictListResponse(items=[self.conflict], page=page, page_size=page_size, total=1)

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


def test_list_audit_returns_logs() -> None:
    client, fake_service = build_client()

    response = client.get("/api/audit", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["items"][0]["action_type"] == "memory.update"
    assert response.json()["total"] == 1


def test_list_conflicts_returns_records() -> None:
    client, fake_service = build_client()

    response = client.get("/api/conflicts", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "open"
    assert response.json()["items"][0]["left_memory_text"] == "继续推进校园食堂系统。"


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
