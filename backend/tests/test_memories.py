from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.api.deps import get_memory_service
from app.main import create_app
from app.models.memory import (
    ActorContext,
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryDetailResponse,
    MemoryListResponse,
    MemorySummaryResponse,
    MemoryUpdateRequest,
)
from app.services.memory_service import MemoryNotFoundError
from fastapi.testclient import TestClient


class FakeMemoryService:
    def __init__(self) -> None:
        now = datetime(2026, 5, 16, tzinfo=timezone.utc)
        self.workspace_id = uuid4()
        self.memory_id = uuid4()
        self.chunk_id = uuid4()
        self.memory = MemoryDetailResponse(
            memory_id=self.memory_id,
            workspace_id=self.workspace_id,
            created_from_doc_id=None,
            memory_type="decision",
            canonical_text="最终选择 MemoryBase 作为数据库课程项目。",
            summary="项目选题决策",
            confidence=0.9,
            importance=5,
            status="active",
            access_level="project",
            current_revision_no=1,
            created_at=now,
            updated_at=now,
            evidence_count=1,
            owner_user_id=None,
            owner_agent_id=None,
            valid_from=now,
            valid_to=None,
            superseded_by_memory_id=None,
            evidence=[
                {
                    "evidence_id": uuid4(),
                    "chunk_id": self.chunk_id,
                    "evidence_role": "supports",
                    "weight": 1.0,
                    "note": None,
                    "doc_id": uuid4(),
                    "source_title": "discussion_01",
                    "chunk_no": 1,
                    "chunk_text": "我们决定选择 MemoryBase。",
                    "start_line": 1,
                    "end_line": 2,
                }
            ],
            revisions=[
                {
                    "revision_no": 1,
                    "revision_text": "最终选择 MemoryBase 作为数据库课程项目。",
                    "revision_summary": "项目选题决策",
                    "revision_reason": "initial create",
                    "editor_type": "system",
                    "editor_id": None,
                    "created_at": now,
                }
            ],
        )

    def create_memory(self, payload: MemoryCreateRequest) -> MemorySummaryResponse:
        self.memory = self.memory.model_copy(
            update={
                "workspace_id": payload.workspace_id,
                "memory_type": payload.memory_type,
                "canonical_text": payload.canonical_text,
                "summary": payload.summary,
                "confidence": payload.confidence,
                "importance": payload.importance,
                "access_level": payload.access_level,
                "evidence_count": len(payload.evidence),
            }
        )
        return MemorySummaryResponse(**self.memory.model_dump(exclude={"evidence", "revisions"}))

    def list_memories(
        self,
        *,
        workspace_id: UUID | None,
        memory_type: str | None,
        status: str | None,
        access_level: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> MemoryListResponse:
        if workspace_id is not None and workspace_id != self.workspace_id:
            return MemoryListResponse(items=[], page=page, page_size=page_size, total=0)
        item = MemorySummaryResponse(**self.memory.model_dump(exclude={"evidence", "revisions"}))
        return MemoryListResponse(items=[item], page=page, page_size=page_size, total=1)

    def get_memory(self, memory_id: UUID, workspace_id: UUID) -> MemoryDetailResponse:
        if memory_id != self.memory_id or workspace_id != self.workspace_id:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        return deepcopy(self.memory)

    def update_memory(
        self,
        memory_id: UUID,
        workspace_id: UUID,
        payload: MemoryUpdateRequest,
        actor: ActorContext,
    ) -> MemoryDetailResponse:
        if memory_id != self.memory_id or workspace_id != self.workspace_id:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        updated = self.memory.model_copy(
            update={
                "canonical_text": payload.canonical_text or self.memory.canonical_text,
                "summary": payload.summary if payload.summary is not None else self.memory.summary,
                "current_revision_no": self.memory.current_revision_no + 1,
                "status": payload.status or self.memory.status,
            }
        )
        self.memory = updated
        return deepcopy(self.memory)

    def delete_memory(
        self, memory_id: UUID, workspace_id: UUID, actor: ActorContext
    ) -> MemoryDeleteResponse:
        if memory_id != self.memory_id or workspace_id != self.workspace_id:
            raise MemoryNotFoundError(f"memory {memory_id} not found")
        self.memory = self.memory.model_copy(
            update={"status": "archived", "valid_to": datetime(2026, 5, 16, tzinfo=timezone.utc)}
        )
        return MemoryDeleteResponse(memory_id=self.memory_id, status="archived")


def build_client() -> tuple[TestClient, FakeMemoryService]:
    app = create_app()
    fake_service = FakeMemoryService()
    app.dependency_overrides[get_memory_service] = lambda: fake_service
    return TestClient(app), fake_service


def test_create_memory_returns_summary() -> None:
    client, fake_service = build_client()

    response = client.post(
        "/api/memories",
        json={
            "workspace_id": str(fake_service.workspace_id),
            "memory_type": "decision",
            "canonical_text": "最终选择 MemoryBase 作为数据库课程项目。",
            "summary": "项目选题决策",
            "confidence": 0.9,
            "importance": 5,
            "access_level": "project",
            "evidence": [
                {
                    "chunk_id": str(fake_service.chunk_id),
                    "evidence_role": "supports",
                    "weight": 0.9,
                    "note": "Direct source chunk.",
                }
            ],
        },
    )

    assert response.status_code == 201
    assert response.json()["memory_type"] == "decision"
    assert response.json()["evidence_count"] == 1


def test_list_memories_returns_collection() -> None:
    client, fake_service = build_client()

    response = client.get("/api/memories", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["summary"] == "项目选题决策"


def test_get_memory_returns_detail() -> None:
    client, fake_service = build_client()

    response = client.get(
        f"/api/memories/{fake_service.memory_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
    )

    assert response.status_code == 200
    assert response.json()["current_revision_no"] == 1
    assert len(response.json()["revisions"]) == 1


def test_update_memory_returns_new_revision_state() -> None:
    client, fake_service = build_client()

    response = client.patch(
        f"/api/memories/{fake_service.memory_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
        headers={
            "X-Actor-Type": "user",
            "X-Revision-Reason": "manual update",
        },
        json={
            "canonical_text": "最终选择 MemoryBase 作为数据库课程项目，并优先完成后端。",
            "summary": "项目选题与分工更新",
        },
    )

    assert response.status_code == 200
    assert response.json()["canonical_text"].endswith("优先完成后端。")
    assert response.json()["current_revision_no"] == 2


def test_delete_memory_soft_deletes_record() -> None:
    client, fake_service = build_client()

    response = client.delete(
        f"/api/memories/{fake_service.memory_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
    )

    assert response.status_code == 200
    assert response.json() == {"memory_id": str(fake_service.memory_id), "status": "archived"}


def test_memory_endpoints_return_404_for_unknown_record() -> None:
    client, _ = build_client()

    response = client.get(f"/api/memories/{uuid4()}", params={"workspace_id": str(uuid4())})

    assert response.status_code == 404
