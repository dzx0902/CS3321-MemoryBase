from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from ..core.config import Settings
from ..core.database import Database
from ..models.graph import (
    GraphActorContext,
    GraphEdge,
    GraphHealthResponse,
    GraphNode,
    GraphResponse,
    GraphSyncResponse,
)

try:  # pragma: no cover - exercised only when neo4j is installed.
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - optional dependency path.
    GraphDatabase = None


class GraphUnavailableError(Exception):
    pass


class GraphRepository(Protocol):
    def build_workspace_graph(self, workspace_id: UUID, limit: int) -> GraphResponse:
        ...


class GraphVisibilityRepository(Protocol):
    def list_visible_memory_ids(
        self,
        workspace_id: UUID,
        agent_id: UUID | None,
    ) -> set[str]:
        ...

    def insert_graph_sync_audit(
        self,
        *,
        workspace_id: UUID,
        actor: GraphActorContext,
        node_count: int,
        edge_count: int,
    ) -> None:
        ...


class PostgresGraphRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def build_workspace_graph(self, workspace_id: UUID, limit: int) -> GraphResponse:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}

        def add_node(node: GraphNode) -> None:
            nodes[node.id] = node

        def add_edge(edge: GraphEdge) -> None:
            if edge.source in nodes and edge.target in nodes:
                edges[edge.id] = edge

        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT workspace_id, slug, name, scope_type
                    FROM workspace
                    WHERE workspace_id = %(workspace_id)s
                    """,
                    {"workspace_id": workspace_id},
                )
                workspace = cur.fetchone()
                if workspace is None:
                    return GraphResponse(
                        workspace_id=workspace_id,
                        source="postgres-preview",
                        nodes=[],
                        edges=[],
                    )

                workspace_id_str = str(workspace_id)
                add_node(
                    GraphNode(
                        id=f"workspace:{workspace_id_str}",
                        type="workspace",
                        label="Workspace",
                        title=workspace["name"],
                        subtitle=workspace["slug"],
                        properties=_clean(workspace),
                    )
                )

                cur.execute(
                    """
                    SELECT doc_id, workspace_id, doc_type, title, source_path, status, imported_at
                    FROM source_document
                    WHERE workspace_id = %(workspace_id)s
                    ORDER BY imported_at DESC
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit},
                )
                for row in cur.fetchall():
                    node_id = f"source:{row['doc_id']}"
                    add_node(_node(node_id, "source", "Source", row["title"], row["doc_type"], row))
                    add_edge(
                        _edge(
                            f"workspace-source:{row['doc_id']}",
                            f"workspace:{workspace_id_str}",
                            node_id,
                            "CONTAINS",
                        )
                    )

                cur.execute(
                    """
                    SELECT sc.chunk_id,
                           sc.doc_id,
                           sc.chunk_no,
                           sc.chunk_text,
                           sc.start_line,
                           sc.end_line,
                           sc.token_count
                    FROM source_chunk sc
                    JOIN source_document sd ON sd.doc_id = sc.doc_id
                    WHERE sd.workspace_id = %(workspace_id)s
                    ORDER BY sd.imported_at DESC, sc.chunk_no ASC
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit * 4},
                )
                for row in cur.fetchall():
                    node_id = f"chunk:{row['chunk_id']}"
                    add_node(
                        _node(
                            node_id,
                            "chunk",
                            "Chunk",
                            f"Chunk {row['chunk_no']}",
                            _excerpt(row["chunk_text"]),
                            row,
                        )
                    )
                    add_edge(
                        _edge(
                            f"source-chunk:{row['doc_id']}:{row['chunk_id']}",
                            f"source:{row['doc_id']}",
                            node_id,
                            "HAS_CHUNK",
                        )
                    )

                cur.execute(
                    """
                    SELECT memory_id, workspace_id, created_from_doc_id, memory_type, summary,
                           canonical_text, confidence, importance, status, access_level, updated_at
                    FROM memory_item
                    WHERE workspace_id = %(workspace_id)s
                    ORDER BY importance DESC, updated_at DESC
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit},
                )
                for row in cur.fetchall():
                    node_id = f"memory:{row['memory_id']}"
                    add_node(
                        _node(
                            node_id,
                            "memory",
                            "Memory",
                            row["summary"] or _excerpt(row["canonical_text"], 80),
                            row["memory_type"],
                            row,
                        )
                    )
                    add_edge(
                        _edge(
                            f"workspace-memory:{row['memory_id']}",
                            f"workspace:{workspace_id_str}",
                            node_id,
                            "CONTAINS",
                        )
                    )
                    if row["created_from_doc_id"]:
                        add_edge(
                            _edge(
                                f"memory-created-from:{row['memory_id']}:{row['created_from_doc_id']}",
                                node_id,
                                f"source:{row['created_from_doc_id']}",
                                "CREATED_FROM",
                            )
                        )

                cur.execute(
                    """
                    SELECT me.memory_id, me.chunk_id, me.evidence_role, me.weight, me.note
                    FROM memory_evidence me
                    JOIN memory_item mi ON mi.memory_id = me.memory_id
                    WHERE mi.workspace_id = %(workspace_id)s
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit * 5},
                )
                for row in cur.fetchall():
                    add_edge(
                        _edge(
                            f"memory-evidence:{row['memory_id']}:{row['chunk_id']}:{row['evidence_role']}",
                            f"memory:{row['memory_id']}",
                            f"chunk:{row['chunk_id']}",
                            "SUPPORTED_BY",
                            row,
                        )
                    )

                cur.execute(
                    """
                    SELECT entity_id, workspace_id, canonical_name, entity_type, description, status
                    FROM entity
                    WHERE workspace_id = %(workspace_id)s
                    ORDER BY updated_at DESC, canonical_name ASC
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit},
                )
                for row in cur.fetchall():
                    node_id = f"entity:{row['entity_id']}"
                    add_node(
                        _node(
                            node_id,
                            "entity",
                            "Entity",
                            row["canonical_name"],
                            row["entity_type"],
                            row,
                        )
                    )
                    add_edge(
                        _edge(
                            f"workspace-entity:{row['entity_id']}",
                            f"workspace:{workspace_id_str}",
                            node_id,
                            "CONTAINS",
                        )
                    )

                cur.execute(
                    """
                    SELECT memory_id, entity_id, relation_role
                    FROM memory_entity
                    WHERE workspace_id = %(workspace_id)s
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit * 5},
                )
                for row in cur.fetchall():
                    add_edge(
                        _edge(
                            f"memory-entity:{row['memory_id']}:{row['entity_id']}:{row['relation_role']}",
                            f"memory:{row['memory_id']}",
                            f"entity:{row['entity_id']}",
                            "MENTIONS",
                            row,
                        )
                    )

                cur.execute(
                    """
                    SELECT scene_id, workspace_id, scene_slug, title, summary, updated_at
                    FROM memory_scene
                    WHERE workspace_id = %(workspace_id)s
                    ORDER BY updated_at DESC
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit},
                )
                for row in cur.fetchall():
                    node_id = f"scene:{row['scene_id']}"
                    add_node(_node(node_id, "scene", "Scene", row["title"], row["scene_slug"], row))
                    add_edge(
                        _edge(
                            f"workspace-scene:{row['scene_id']}",
                            f"workspace:{workspace_id_str}",
                            node_id,
                            "CONTAINS",
                        )
                    )

                cur.execute(
                    """
                    SELECT scene_id, memory_id, cell_role, sort_order, note
                    FROM memory_scene_cell
                    WHERE workspace_id = %(workspace_id)s
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit * 5},
                )
                for row in cur.fetchall():
                    add_edge(
                        _edge(
                            f"scene-memory:{row['scene_id']}:{row['memory_id']}",
                            f"scene:{row['scene_id']}",
                            f"memory:{row['memory_id']}",
                            "CONTAINS_MEMORY",
                            row,
                        )
                    )

                cur.execute(
                    """
                    SELECT page_id, workspace_id, page_slug, page_type, title, current_revision_no,
                           generated_from_scene_id,
                           generated_from_memory_id,
                           needs_rebuild,
                           status,
                           updated_at
                    FROM wiki_page
                    WHERE workspace_id = %(workspace_id)s
                    ORDER BY updated_at DESC
                    LIMIT %(limit)s
                    """,
                    {"workspace_id": workspace_id, "limit": limit},
                )
                for row in cur.fetchall():
                    node_id = f"wiki:{row['page_id']}"
                    add_node(_node(node_id, "wiki", "Wiki", row["title"], row["page_type"], row))
                    add_edge(
                        _edge(
                            f"workspace-wiki:{row['page_id']}",
                            f"workspace:{workspace_id_str}",
                            node_id,
                            "CONTAINS",
                        )
                    )
                    if row["generated_from_memory_id"]:
                        add_edge(
                            _edge(
                                f"wiki-memory:{row['page_id']}:{row['generated_from_memory_id']}",
                                node_id,
                                f"memory:{row['generated_from_memory_id']}",
                                "DERIVED_FROM",
                            )
                        )
                    if row["generated_from_scene_id"]:
                        add_edge(
                            _edge(
                                f"wiki-scene:{row['page_id']}:{row['generated_from_scene_id']}",
                                node_id,
                                f"scene:{row['generated_from_scene_id']}",
                                "DERIVED_FROM",
                            )
                        )

        return GraphResponse(
            workspace_id=workspace_id,
            source="postgres-preview",
            nodes=list(nodes.values()),
            edges=list(edges.values()),
        )


class PostgresGraphVisibilityRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list_visible_memory_ids(
        self,
        workspace_id: UUID,
        agent_id: UUID | None,
    ) -> set[str]:
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                if agent_id is None:
                    cur.execute(
                        """
                        SELECT memory_id
                        FROM memory_item
                        WHERE workspace_id = %(workspace_id)s
                          AND status = 'active'
                          AND access_level IN ('public', 'project')
                          AND valid_from <= now()
                          AND (valid_to IS NULL OR valid_to > now())
                        """,
                        {"workspace_id": workspace_id},
                    )
                else:
                    cur.execute(
                        """
                        SELECT memory_id
                        FROM v_agent_visible_memory
                        WHERE workspace_id = %(workspace_id)s
                          AND agent_id = %(agent_id)s
                        """,
                        {"workspace_id": workspace_id, "agent_id": agent_id},
                    )
                return {str(row["memory_id"]) for row in cur.fetchall()}

    def insert_graph_sync_audit(
        self,
        *,
        workspace_id: UUID,
        actor: GraphActorContext,
        node_count: int,
        edge_count: int,
    ) -> None:
        with self.db.connection() as conn:
            with conn.cursor() as cur:
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
                        'graph.sync',
                        'workspace',
                        %(workspace_id)s,
                        %(after_json)s::jsonb
                    )
                    """,
                    {
                        "workspace_id": workspace_id,
                        "actor_type": actor.actor_type,
                        "actor_id": actor.actor_id,
                        "after_json": json.dumps(
                            {
                                "workspace_id": str(workspace_id),
                                "node_count": node_count,
                                "edge_count": edge_count,
                                "actor_type": actor.actor_type,
                                "actor_id": str(actor.actor_id) if actor.actor_id else None,
                                "revision_reason": actor.revision_reason,
                            }
                        ),
                    },
                )
            conn.commit()


class Neo4jGraphStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._driver_instance = None

    def health(self) -> GraphHealthResponse:
        if not self.settings.neo4j_enabled:
            return GraphHealthResponse(
                enabled=False,
                available=False,
                uri=self.settings.neo4j_uri,
                database=self.settings.neo4j_database,
                error="Neo4j is disabled. Set NEO4J_ENABLED=true to enable graph sync.",
            )
        if GraphDatabase is None:
            return GraphHealthResponse(
                enabled=True,
                available=False,
                uri=self.settings.neo4j_uri,
                database=self.settings.neo4j_database,
                error="neo4j Python package is not installed",
            )
        try:
            driver = self._get_driver()
            driver.verify_connectivity()
            return GraphHealthResponse(
                enabled=True,
                available=True,
                uri=self.settings.neo4j_uri,
                database=self.settings.neo4j_database,
            )
        except Exception as exc:  # pragma: no cover - depends on external service.
            return GraphHealthResponse(
                enabled=True,
                available=False,
                uri=self.settings.neo4j_uri,
                database=self.settings.neo4j_database,
                error=str(exc),
            )

    def sync(self, graph: GraphResponse) -> GraphSyncResponse:
        self._ensure_available()
        driver = self._get_driver()
        workspace_id = str(graph.workspace_id)
        edge_groups = _group_edges_by_relation_type(graph.edges)

        with driver.session(database=self.settings.neo4j_database) as session:
            session.run(
                "MATCH (n:MemoryBaseNode {workspace_id: $workspace_id}) DETACH DELETE n",
                workspace_id=workspace_id,
            )
            session.run(
                """
                UNWIND $nodes AS node
                MERGE (n:MemoryBaseNode {id: node.id})
                SET n.workspace_id = $workspace_id,
                    n.type = node.type,
                    n.label = node.label,
                    n.title = node.title,
                    n.subtitle = node.subtitle,
                    n.properties_json = node.properties_json
                """,
                workspace_id=workspace_id,
                nodes=[
                    {
                        "id": node.id,
                        "type": node.type,
                        "label": node.label,
                        "title": node.title,
                        "subtitle": node.subtitle,
                        "properties_json": _jsonish(node.properties),
                    }
                    for node in graph.nodes
                ],
            )
            for relation_type, edges in edge_groups.items():
                session.run(
                    f"""
                    UNWIND $edges AS edge
                    MATCH (a:MemoryBaseNode {{id: edge.source}})
                    MATCH (b:MemoryBaseNode {{id: edge.target}})
                    MERGE (a)-[r:{relation_type} {{id: edge.id}}]->(b)
                    SET r.label = edge.label,
                        r.properties_json = edge.properties_json
                    """,
                    edges=[
                        {
                            "id": edge.id,
                            "source": edge.source,
                            "target": edge.target,
                            "label": edge.label,
                            "properties_json": _jsonish(edge.properties),
                        }
                        for edge in edges
                    ],
                )

        return GraphSyncResponse(
            workspace_id=graph.workspace_id,
            status="synced",
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )

    def load_workspace_graph(self, workspace_id: UUID, limit: int) -> GraphResponse:
        self._ensure_available()
        driver = self._get_driver()

        with driver.session(database=self.settings.neo4j_database) as session:
            node_records = session.run(
                """
                MATCH (n:MemoryBaseNode {workspace_id: $workspace_id})
                RETURN n
                LIMIT $limit
                """,
                workspace_id=str(workspace_id),
                limit=limit * 8,
            )
            nodes = [_neo4j_node(record["n"]) for record in node_records]
            node_ids = {node.id for node in nodes}
            edge_records = session.run(
                """
                MATCH (a:MemoryBaseNode {workspace_id: $workspace_id})
                    -[r]->(b:MemoryBaseNode {workspace_id: $workspace_id})
                RETURN a.id AS source, b.id AS target, type(r) AS type, r
                LIMIT $limit
                """,
                workspace_id=str(workspace_id),
                limit=limit * 12,
            )
            edges = [
                _neo4j_edge(record["source"], record["target"], record["type"], record["r"])
                for record in edge_records
                if record["source"] in node_ids and record["target"] in node_ids
            ]

        return GraphResponse(workspace_id=workspace_id, source="neo4j", nodes=nodes, edges=edges)

    def close(self) -> None:
        if self._driver_instance is not None:
            self._driver_instance.close()
            self._driver_instance = None

    def _ensure_available(self) -> None:
        health = self.health()
        if not health.available:
            raise GraphUnavailableError(health.error or "Neo4j is unavailable")

    def _get_driver(self):
        if self._driver_instance is not None:
            return self._driver_instance
        if GraphDatabase is None:
            raise GraphUnavailableError("neo4j Python package is not installed")
        self._driver_instance = GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )
        return self._driver_instance


class GraphService:
    def __init__(
        self,
        repository: GraphRepository,
        store: Neo4jGraphStore,
        visibility_repository: GraphVisibilityRepository,
    ) -> None:
        self.repository = repository
        self.store = store
        self.visibility_repository = visibility_repository

    def health(self) -> GraphHealthResponse:
        return self.store.health()

    def preview_workspace(self, workspace_id: UUID, limit: int) -> GraphResponse:
        return self.repository.build_workspace_graph(workspace_id, limit)

    def sync_workspace(
        self,
        workspace_id: UUID,
        limit: int,
        agent_id: UUID | None,
    ) -> GraphSyncResponse:
        graph = self.repository.build_workspace_graph(workspace_id, limit)
        result = self.store.sync(graph)
        actor = GraphActorContext(
            actor_type="agent" if agent_id is not None else "system",
            actor_id=agent_id,
            revision_reason="graph sync",
        )
        self.visibility_repository.insert_graph_sync_audit(
            workspace_id=workspace_id,
            actor=actor,
            node_count=result.node_count,
            edge_count=result.edge_count,
        )
        return result

    def load_workspace_graph(
        self,
        workspace_id: UUID,
        limit: int,
        fallback: bool,
        agent_id: UUID | None,
    ) -> GraphResponse:
        try:
            graph = self.store.load_workspace_graph(workspace_id, limit)
            if graph.nodes:
                return self._filter_graph(graph, workspace_id=workspace_id, agent_id=agent_id)
        except GraphUnavailableError:
            if not fallback:
                raise
        graph = self.repository.build_workspace_graph(workspace_id, limit)
        return self._filter_graph(graph, workspace_id=workspace_id, agent_id=agent_id)

    def close(self) -> None:
        self.store.close()

    def _filter_graph(
        self,
        graph: GraphResponse,
        *,
        workspace_id: UUID,
        agent_id: UUID | None,
    ) -> GraphResponse:
        visible_memory_ids = self.visibility_repository.list_visible_memory_ids(
            workspace_id,
            agent_id,
        )
        allowed_node_ids: set[str] = set()
        for node in graph.nodes:
            if node.type != "memory":
                allowed_node_ids.add(node.id)
                continue
            memory_uuid = _memory_uuid_from_node(node.id)
            if memory_uuid is None:
                continue
            if memory_uuid in visible_memory_ids:
                allowed_node_ids.add(node.id)

        filtered_edges = [
            edge
            for edge in graph.edges
            if edge.source in allowed_node_ids and edge.target in allowed_node_ids
        ]
        connected_node_ids = {
            node_id
            for edge in filtered_edges
            for node_id in (edge.source, edge.target)
        }
        filtered_nodes = [
            node
            for node in graph.nodes
            if node.id in allowed_node_ids
            and (node.type == "workspace" or node.id in connected_node_ids)
        ]
        return GraphResponse(
            workspace_id=graph.workspace_id,
            source=graph.source,
            nodes=filtered_nodes,
            edges=filtered_edges,
        )


def _node(
    node_id: str,
    node_type: str,
    label: str,
    title: str,
    subtitle: str | None,
    properties: dict[str, Any],
) -> GraphNode:
    return GraphNode(
        id=node_id,
        type=node_type,
        label=label,
        title=title,
        subtitle=subtitle,
        properties=_clean(properties),
    )


def _edge(
    edge_id: str,
    source: str,
    target: str,
    edge_type: str,
    properties: dict[str, Any] | None = None,
) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        type=edge_type,
        label=edge_type.replace("_", " ").title(),
        properties=_clean(properties or {}),
    )


def _clean(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _clean_value(value) for key, value in row.items()}


def _clean_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _excerpt(value: str | None, max_len: int = 120) -> str:
    if not value:
        return ""
    return value if len(value) <= max_len else value[: max_len - 3] + "..."


def _jsonish(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _safe_rel_type(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.upper())
    return cleaned or "RELATED_TO"


def _group_edges_by_relation_type(edges: list[GraphEdge]) -> dict[str, list[GraphEdge]]:
    grouped: dict[str, list[GraphEdge]] = defaultdict(list)
    for edge in edges:
        grouped[_safe_rel_type(edge.type)].append(edge)
    return dict(grouped)


def _memory_uuid_from_node(node_id: str) -> str | None:
    if not node_id.startswith("memory:"):
        return None
    return node_id.split(":", 1)[1]


def _neo4j_node(raw_node: Any) -> GraphNode:
    data = dict(raw_node)
    properties = _parse_jsonish(data.get("properties_json"))
    return GraphNode(
        id=data.get("id", ""),
        type=data.get("type", "node"),
        label=data.get("label", data.get("type", "Node")),
        title=data.get("title", data.get("id", "")),
        subtitle=data.get("subtitle"),
        properties=properties,
    )


def _neo4j_edge(source: str, target: str, rel_type: str, raw_rel: Any) -> GraphEdge:
    data = dict(raw_rel)
    edge_id = data.get("id") or f"{source}:{rel_type}:{target}"
    return GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        type=rel_type,
        label=data.get("label", rel_type.replace("_", " ").title()),
        properties=_parse_jsonish(data.get("properties_json")),
    )


def _parse_jsonish(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except (TypeError, json.JSONDecodeError):
        return {"value": value}
