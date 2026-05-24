from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.api.deps import get_semantic_service
from app.main import create_app
from app.models.semantic import (
    EntityListResponse,
    EntityResponse,
    SceneListResponse,
    SceneResponse,
)
from fastapi.testclient import TestClient


class FakeSemanticService:
    def __init__(self) -> None:
        now = datetime(2026, 5, 16, tzinfo=timezone.utc)
        self.workspace_id = uuid4()
        self.entity = EntityResponse(
            entity_id=uuid4(),
            workspace_id=self.workspace_id,
            canonical_name="MemoryBase",
            entity_type="project",
            description="Demo project",
            status="active",
            memory_count=3,
            created_at=now,
            updated_at=now,
        )
        self.scene = SceneResponse(
            scene_id=uuid4(),
            workspace_id=self.workspace_id,
            scene_slug="topic-decision",
            title="Topic Decision",
            summary="Project topic decision scene",
            memory_count=2,
            created_at=now,
            updated_at=now,
        )

    def list_entities(self, *, workspace_id, entity_type, status, keyword, page, page_size):
        return EntityListResponse(items=[self.entity], page=page, page_size=page_size, total=1)

    def list_scenes(self, *, workspace_id, keyword, page, page_size):
        return SceneListResponse(items=[self.scene], page=page, page_size=page_size, total=1)


def test_semantic_endpoints_return_entities_and_scenes() -> None:
    app = create_app()
    fake_service = FakeSemanticService()
    app.dependency_overrides[get_semantic_service] = lambda: fake_service
    client = TestClient(app)

    entities = client.get(f"/api/entities?workspace_id={fake_service.workspace_id}")
    scenes = client.get(f"/api/scenes?workspace_id={fake_service.workspace_id}")

    assert entities.status_code == 200
    assert entities.json()["items"][0]["canonical_name"] == "MemoryBase"
    assert scenes.status_code == 200
    assert scenes.json()["items"][0]["scene_slug"] == "topic-decision"
