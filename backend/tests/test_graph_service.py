from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from app.core.config import Settings
from app.models.graph import (
    GraphEdge,
    GraphHealthResponse,
    GraphNode,
    GraphResponse,
)
from app.services.graph_service import (
    GraphService,
    GraphUnavailableError,
    Neo4jGraphStore,
)


class FakeGraphRepository:
    def __init__(self, graph: GraphResponse) -> None:
        self.graph = graph
        self.calls: list[tuple[UUID, int]] = []

    def build_workspace_graph(self, workspace_id: UUID, limit: int) -> GraphResponse:
        self.calls.append((workspace_id, limit))
        return self.graph


class FakeVisibilityRepository:
    def __init__(self, visible_memory_ids: set[str]) -> None:
        self.visible_memory_ids = visible_memory_ids
        self.calls: list[tuple[UUID, UUID | None]] = []
        self.audit_calls: list[dict[str, object]] = []

    def list_visible_memory_ids(
        self, workspace_id: UUID, agent_id: UUID | None
    ) -> set[str]:
        self.calls.append((workspace_id, agent_id))
        return set(self.visible_memory_ids)

    def insert_graph_sync_audit(
        self,
        *,
        workspace_id: UUID,
        actor,
        node_count: int,
        edge_count: int,
    ) -> None:
        self.audit_calls.append(
            {
                "workspace_id": workspace_id,
                "actor": actor,
                "node_count": node_count,
                "edge_count": edge_count,
            }
        )


class FakeStore:
    def __init__(self, graph: GraphResponse | None = None) -> None:
        self.graph = graph
        self.health_response = GraphHealthResponse(
            enabled=True,
            available=True,
            uri="bolt://localhost:7687",
            database="neo4j",
        )
        self.load_calls: list[tuple[UUID, int]] = []
        self.sync_calls: list[GraphResponse] = []
        self.raise_on_load = False
        self.raise_on_sync = False

    def health(self) -> GraphHealthResponse:
        return self.health_response

    def load_workspace_graph(self, workspace_id: UUID, limit: int) -> GraphResponse:
        self.load_calls.append((workspace_id, limit))
        if self.raise_on_load:
            raise GraphUnavailableError("neo4j unavailable")
        assert self.graph is not None
        return self.graph

    def sync(self, graph: GraphResponse):
        self.sync_calls.append(graph)
        if self.raise_on_sync:
            raise GraphUnavailableError("neo4j unavailable")
        from app.models.graph import GraphSyncResponse

        return GraphSyncResponse(
            workspace_id=graph.workspace_id,
            status="synced",
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )


def build_graph(workspace_id: UUID) -> GraphResponse:
    memory_visible = "memory:11111111-1111-1111-1111-111111111111"
    memory_hidden = "memory:22222222-2222-2222-2222-222222222222"
    chunk_id = "chunk:33333333-3333-3333-3333-333333333333"
    entity_id = "entity:44444444-4444-4444-4444-444444444444"
    scene_id = "scene:55555555-5555-5555-5555-555555555555"
    source_id = "source:66666666-6666-6666-6666-666666666666"
    wiki_id = "wiki:77777777-7777-7777-7777-777777777777"
    workspace_node_id = f"workspace:{workspace_id}"

    return GraphResponse(
        workspace_id=workspace_id,
        source="neo4j",
        nodes=[
            GraphNode(id=workspace_node_id, type="workspace", label="Workspace", title="Demo"),
            GraphNode(id=source_id, type="source", label="Source", title="Doc"),
            GraphNode(id=chunk_id, type="chunk", label="Chunk", title="Chunk 1"),
            GraphNode(id=memory_visible, type="memory", label="Memory", title="Visible"),
            GraphNode(
                id=memory_hidden,
                type="memory",
                label="Memory",
                title="Hidden",
                properties={"access_level": "private"},
            ),
            GraphNode(id=entity_id, type="entity", label="Entity", title="MemoryBase"),
            GraphNode(id=scene_id, type="scene", label="Scene", title="Story"),
            GraphNode(id=wiki_id, type="wiki", label="Wiki", title="Page"),
        ],
        edges=[
            GraphEdge(
                id="workspace-source",
                source=workspace_node_id,
                target=source_id,
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="workspace-chunk",
                source=workspace_node_id,
                target=chunk_id,
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="workspace-memory-visible",
                source=workspace_node_id,
                target=memory_visible,
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="workspace-memory-hidden",
                source=workspace_node_id,
                target=memory_hidden,
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="workspace-entity",
                source=workspace_node_id,
                target=entity_id,
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="workspace-scene",
                source=workspace_node_id,
                target=scene_id,
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="workspace-wiki",
                source=workspace_node_id,
                target=wiki_id,
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="memory-visible-chunk",
                source=memory_visible,
                target=chunk_id,
                type="SUPPORTED_BY",
                label="Supported By",
            ),
            GraphEdge(
                id="memory-hidden-chunk",
                source=memory_hidden,
                target=chunk_id,
                type="SUPPORTED_BY",
                label="Supported By",
            ),
            GraphEdge(
                id="memory-hidden-entity",
                source=memory_hidden,
                target=entity_id,
                type="MENTIONS",
                label="Mentions",
            ),
            GraphEdge(
                id="scene-hidden-memory",
                source=scene_id,
                target=memory_hidden,
                type="CONTAINS_MEMORY",
                label="Contains Memory",
            ),
            GraphEdge(
                id="wiki-hidden-memory",
                source=wiki_id,
                target=memory_hidden,
                type="DERIVED_FROM",
                label="Derived From",
            ),
        ],
    )


def test_graph_service_filters_to_agent_visible_memories() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    visible_memory_id = "11111111-1111-1111-1111-111111111111"
    store = FakeStore(build_graph(workspace_id))
    repository = FakeGraphRepository(build_graph(workspace_id))
    visibility = FakeVisibilityRepository({visible_memory_id})
    service = GraphService(repository=repository, store=store, visibility_repository=visibility)

    graph = service.load_workspace_graph(
        workspace_id=workspace_id,
        limit=20,
        fallback=True,
        agent_id=agent_id,
    )

    node_ids = {node.id for node in graph.nodes}
    edge_ids = {edge.id for edge in graph.edges}

    assert "memory:11111111-1111-1111-1111-111111111111" in node_ids
    assert "memory:22222222-2222-2222-2222-222222222222" not in node_ids
    assert "memory-hidden-chunk" not in edge_ids
    assert "memory-hidden-entity" not in edge_ids
    assert "scene-hidden-memory" not in edge_ids
    assert "wiki-hidden-memory" not in edge_ids
    assert "chunk:33333333-3333-3333-3333-333333333333" in node_ids
    assert "entity:44444444-4444-4444-4444-444444444444" in node_ids
    assert visibility.calls == [(workspace_id, agent_id)]


def test_graph_service_filters_to_public_and_project_without_agent() -> None:
    workspace_id = uuid4()
    project_memory_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    graph = build_graph(workspace_id).model_copy(
        update={
            "nodes": [
                GraphNode(
                    id=f"workspace:{workspace_id}",
                    type="workspace",
                    label="Workspace",
                    title="Demo",
                ),
                GraphNode(
                    id=f"memory:{project_memory_id}",
                    type="memory",
                    label="Memory",
                    title="Project",
                    properties={"access_level": "project"},
                ),
                GraphNode(
                    id="memory:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    type="memory",
                    label="Memory",
                    title="Team",
                    properties={"access_level": "team"},
                ),
                GraphNode(
                    id="memory:cccccccc-cccc-cccc-cccc-cccccccccccc",
                    type="memory",
                    label="Memory",
                    title="Private",
                    properties={"access_level": "private"},
                ),
            ],
            "edges": [
                GraphEdge(
                    id="workspace-project",
                    source=f"workspace:{workspace_id}",
                    target=f"memory:{project_memory_id}",
                    type="CONTAINS",
                    label="Contains",
                ),
                GraphEdge(
                    id="workspace-team",
                    source=f"workspace:{workspace_id}",
                    target="memory:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    type="CONTAINS",
                    label="Contains",
                ),
                GraphEdge(
                    id="workspace-private",
                    source=f"workspace:{workspace_id}",
                    target="memory:cccccccc-cccc-cccc-cccc-cccccccccccc",
                    type="CONTAINS",
                    label="Contains",
                ),
            ],
        }
    )
    store = FakeStore(graph)
    repository = FakeGraphRepository(graph)
    visibility = FakeVisibilityRepository({project_memory_id})
    service = GraphService(repository=repository, store=store, visibility_repository=visibility)

    filtered = service.load_workspace_graph(
        workspace_id=workspace_id,
        limit=20,
        fallback=True,
        agent_id=None,
    )

    node_ids = {node.id for node in filtered.nodes}
    assert f"memory:{project_memory_id}" in node_ids
    assert "memory:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb" not in node_ids
    assert "memory:cccccccc-cccc-cccc-cccc-cccccccccccc" not in node_ids
    assert visibility.calls == [(workspace_id, None)]


def test_graph_service_falls_back_to_postgres_when_neo4j_unavailable() -> None:
    workspace_id = uuid4()
    store = FakeStore()
    store.raise_on_load = True
    repository_graph = GraphResponse(
        workspace_id=workspace_id,
        source="postgres-preview",
        nodes=[],
        edges=[],
    )
    repository = FakeGraphRepository(repository_graph)
    visibility = FakeVisibilityRepository(set())
    service = GraphService(repository=repository, store=store, visibility_repository=visibility)

    graph = service.load_workspace_graph(
        workspace_id=workspace_id,
        limit=10,
        fallback=True,
        agent_id=None,
    )

    assert graph.source == "postgres-preview"
    assert repository.calls == [(workspace_id, 10)]


def test_graph_service_raises_without_fallback() -> None:
    workspace_id = uuid4()
    store = FakeStore()
    store.raise_on_load = True
    repository = FakeGraphRepository(
        GraphResponse(workspace_id=workspace_id, source="postgres-preview", nodes=[], edges=[])
    )
    service = GraphService(
        repository=repository,
        store=store,
        visibility_repository=FakeVisibilityRepository(set()),
    )

    with pytest.raises(GraphUnavailableError):
        service.load_workspace_graph(
            workspace_id=workspace_id,
            limit=10,
            fallback=False,
            agent_id=None,
        )


def test_graph_service_sync_records_audit_attribution() -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    graph = build_graph(workspace_id)
    store = FakeStore(graph)
    repository = FakeGraphRepository(graph)
    visibility = FakeVisibilityRepository(set())
    service = GraphService(
        repository=repository,
        store=store,
        visibility_repository=visibility,
    )

    result = service.sync_workspace(
        workspace_id=workspace_id,
        limit=15,
        agent_id=agent_id,
    )

    assert result.status == "synced"
    assert repository.calls == [(workspace_id, 15)]
    assert store.sync_calls == [graph]
    assert len(visibility.audit_calls) == 1
    assert visibility.audit_calls[0]["workspace_id"] == workspace_id
    assert visibility.audit_calls[0]["node_count"] == len(graph.nodes)
    assert visibility.audit_calls[0]["edge_count"] == len(graph.edges)
    actor = visibility.audit_calls[0]["actor"]
    assert actor.actor_type == "agent"
    assert actor.actor_id == agent_id


@dataclass
class FakeSession:
    run_calls: list[tuple[str, dict[str, object]]]

    def run(self, query: str, **params):
        self.run_calls.append((query, params))
        return []

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FakeDriver:
    def __init__(self) -> None:
        self.verify_calls = 0
        self.run_calls: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def verify_connectivity(self) -> None:
        self.verify_calls += 1

    def session(self, *, database: str):
        assert database == "neo4j"
        return FakeSession(self.run_calls)

    def close(self) -> None:
        self.closed = True


def _settings(*, enabled: bool = True) -> Settings:
    return Settings(
        neo4j_enabled=enabled,
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="memorybase",
        neo4j_database="neo4j",
    )


def test_neo4j_store_reuses_driver_and_closes_on_shutdown(monkeypatch) -> None:
    created_drivers: list[FakeDriver] = []

    def fake_driver_factory(uri: str, auth: tuple[str, str]) -> FakeDriver:
        assert uri == "bolt://localhost:7687"
        assert auth == ("neo4j", "memorybase")
        driver = FakeDriver()
        created_drivers.append(driver)
        return driver

    monkeypatch.setattr(
        "app.services.graph_service.GraphDatabase",
        type("FakeGraphDatabase", (), {"driver": staticmethod(fake_driver_factory)}),
    )

    store = Neo4jGraphStore(_settings())

    first = store._get_driver()
    second = store._get_driver()
    assert first is second
    assert len(created_drivers) == 1

    store.close()
    assert created_drivers[0].closed is True


def test_neo4j_store_sync_batches_nodes_and_edges(monkeypatch) -> None:
    created_drivers: list[FakeDriver] = []

    def fake_driver_factory(uri: str, auth: tuple[str, str]) -> FakeDriver:
        driver = FakeDriver()
        created_drivers.append(driver)
        return driver

    monkeypatch.setattr(
        "app.services.graph_service.GraphDatabase",
        type("FakeGraphDatabase", (), {"driver": staticmethod(fake_driver_factory)}),
    )

    workspace_id = uuid4()
    graph = GraphResponse(
        workspace_id=workspace_id,
        source="postgres-preview",
        nodes=[
            GraphNode(id="workspace:1", type="workspace", label="Workspace", title="Demo"),
            GraphNode(id="memory:1", type="memory", label="Memory", title="Visible"),
            GraphNode(id="chunk:1", type="chunk", label="Chunk", title="Chunk 1"),
        ],
        edges=[
            GraphEdge(
                id="edge-1",
                source="workspace:1",
                target="memory:1",
                type="CONTAINS",
                label="Contains",
            ),
            GraphEdge(
                id="edge-2",
                source="memory:1",
                target="chunk:1",
                type="SUPPORTED_BY",
                label="Supported By",
            ),
            GraphEdge(
                id="edge-3",
                source="workspace:1",
                target="chunk:1",
                type="CONTAINS",
                label="Contains",
            ),
        ],
    )

    store = Neo4jGraphStore(_settings())
    result = store.sync(graph)

    assert result.node_count == 3
    assert result.edge_count == 3
    run_calls = created_drivers[0].run_calls
    assert len(run_calls) == 4
    assert "DETACH DELETE" in run_calls[0][0]
    assert "UNWIND $nodes AS node" in run_calls[1][0]
    assert "UNWIND $edges AS edge" in run_calls[2][0]
    assert "UNWIND $edges AS edge" in run_calls[3][0]


def test_neo4j_store_health_disabled_short_circuits() -> None:
    store = Neo4jGraphStore(_settings(enabled=False))

    health = store.health()

    assert health.enabled is False
    assert health.available is False
    assert "disabled" in (health.error or "")
