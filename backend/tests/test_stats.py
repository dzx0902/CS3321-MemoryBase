from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.api.deps import get_stats_service
from app.main import create_app
from app.models.stats import MemoryStatisticResponse, StatsCountResponse, StatsOverviewResponse
from fastapi.testclient import TestClient


class FakeStatsService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()

    def overview(self, *, workspace_id) -> StatsOverviewResponse:
        return StatsOverviewResponse(
            workspace_id=workspace_id,
            source_count=6,
            chunk_count=24,
            memory_count=20,
            active_memory_count=19,
            recall_count=3,
            wiki_page_count=3,
            policy_count=2,
            audit_count=8,
            conflict_count=1,
            forget_request_count=1,
            entity_count=4,
            scene_count=1,
            latest_activity_at=datetime(2026, 5, 16, tzinfo=timezone.utc),
            memory_statistics=[
                MemoryStatisticResponse(
                    memory_type="decision",
                    status="active",
                    access_level="project",
                    memory_count=5,
                    avg_confidence=0.9,
                    avg_importance=4.0,
                )
            ],
            memory_type_counts=[StatsCountResponse(name="decision", count=5)],
            source_status_counts=[StatsCountResponse(name="active", count=6)],
        )


def test_stats_overview_returns_workspace_dashboard_counts() -> None:
    app = create_app()
    fake_service = FakeStatsService()
    app.dependency_overrides[get_stats_service] = lambda: fake_service
    client = TestClient(app)

    response = client.get(f"/api/stats/overview?workspace_id={fake_service.workspace_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == str(fake_service.workspace_id)
    assert payload["memory_count"] == 20
    assert payload["memory_statistics"][0]["memory_type"] == "decision"
    assert payload["source_status_counts"][0]["name"] == "active"
