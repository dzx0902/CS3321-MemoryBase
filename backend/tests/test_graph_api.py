from __future__ import annotations

from uuid import UUID, uuid4

from app.api.deps import get_graph_service
from app.main import create_app
from app.models.graph import GraphHealthResponse, GraphResponse, GraphSyncResponse
from app.services.graph_service import GraphUnavailableError
from fastapi.testclient import TestClient


class FakeGraphService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.agent_id = uuid4()
        self.last_workspace_call: dict[str, object] | None = None
        self.last_preview_call: dict[str, object] | None = None
        self.last_sync_call: dict[str, object] | None = None
        self.raise_workspace_unavailable = False
        self.raise_sync_unavailable = False

    def health(self) -> GraphHealthResponse:
        return GraphHealthResponse(
            enabled=True,
            available=True,
            uri="bolt://localhost:7687",
            database="neo4j",
        )

    def load_workspace_graph(
        self,
        workspace_id: UUID,
        limit: int,
        fallback: bool,
        agent_id: UUID | None,
    ) -> GraphResponse:
        self.last_workspace_call = {
            "workspace_id": workspace_id,
            "limit": limit,
            "fallback": fallback,
            "agent_id": agent_id,
        }
        if self.raise_workspace_unavailable:
            raise GraphUnavailableError("neo4j offline")
        return GraphResponse(
            workspace_id=workspace_id,
            source="neo4j",
            nodes=[],
            edges=[],
        )

    def preview_workspace(self, workspace_id: UUID, limit: int) -> GraphResponse:
        self.last_preview_call = {"workspace_id": workspace_id, "limit": limit}
        return GraphResponse(
            workspace_id=workspace_id,
            source="postgres-preview",
            nodes=[],
            edges=[],
        )

    def sync_workspace(
        self,
        workspace_id: UUID,
        limit: int,
        agent_id: UUID | None,
    ) -> GraphSyncResponse:
        self.last_sync_call = {
            "workspace_id": workspace_id,
            "limit": limit,
            "agent_id": agent_id,
        }
        if self.raise_sync_unavailable:
            raise GraphUnavailableError("neo4j offline")
        return GraphSyncResponse(
            workspace_id=workspace_id,
            status="synced",
            node_count=4,
            edge_count=3,
        )


def build_client() -> tuple[TestClient, FakeGraphService]:
    app = create_app()
    fake_graph = FakeGraphService()
    app.dependency_overrides[get_graph_service] = lambda: fake_graph
    return TestClient(app), fake_graph


def test_workspace_graph_accepts_optional_agent_id() -> None:
    client, fake_graph = build_client()

    response = client.get(
        "/api/graph/workspace",
        params={
            "workspace_id": str(fake_graph.workspace_id),
            "agent_id": str(fake_graph.agent_id),
            "limit": 20,
            "fallback": "false",
        },
    )

    assert response.status_code == 200
    assert fake_graph.last_workspace_call == {
        "workspace_id": fake_graph.workspace_id,
        "limit": 20,
        "fallback": False,
        "agent_id": fake_graph.agent_id,
    }


def test_workspace_graph_allows_human_mode_without_agent_id() -> None:
    client, fake_graph = build_client()

    response = client.get(
        "/api/graph/workspace",
        params={"workspace_id": str(fake_graph.workspace_id)},
    )

    assert response.status_code == 200
    assert fake_graph.last_workspace_call is not None
    assert fake_graph.last_workspace_call["agent_id"] is None


def test_workspace_graph_maps_unavailable_error_to_503() -> None:
    client, fake_graph = build_client()
    fake_graph.raise_workspace_unavailable = True

    response = client.get(
        "/api/graph/workspace",
        params={"workspace_id": str(fake_graph.workspace_id)},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "neo4j offline"


def test_workspace_preview_keeps_workspace_only_contract() -> None:
    client, fake_graph = build_client()

    response = client.get(
        "/api/graph/workspace/preview",
        params={"workspace_id": str(fake_graph.workspace_id), "limit": 12},
    )

    assert response.status_code == 200
    assert fake_graph.last_preview_call == {
        "workspace_id": fake_graph.workspace_id,
        "limit": 12,
    }


def test_workspace_sync_accepts_optional_agent_id() -> None:
    client, fake_graph = build_client()

    response = client.post(
        "/api/graph/workspace/sync",
        params={
            "workspace_id": str(fake_graph.workspace_id),
            "agent_id": str(fake_graph.agent_id),
            "limit": 60,
        },
    )

    assert response.status_code == 200
    assert fake_graph.last_sync_call == {
        "workspace_id": fake_graph.workspace_id,
        "limit": 60,
        "agent_id": fake_graph.agent_id,
    }


def test_workspace_sync_maps_unavailable_error_to_503() -> None:
    client, fake_graph = build_client()
    fake_graph.raise_sync_unavailable = True

    response = client.post(
        "/api/graph/workspace/sync",
        params={"workspace_id": str(fake_graph.workspace_id)},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "neo4j offline"
