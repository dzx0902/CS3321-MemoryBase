from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from ..core.config import Settings
from ..core.database import Database
from ..models.graph import GraphEdge, GraphHealthResponse, GraphNode, GraphResponse, GraphSyncResponse

try:  # pragma: no cover - exercised only when neo4j is installed.
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - optional dependency path.
    GraphDatabase = None


class GraphUnavailableError(Exception):
    pass


class GraphRepository(Protocol):
    def build_workspace_graph(self, workspace_id: UUID, limit: int) -> GraphResponse:
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
                    return GraphResponse(workspace_id=workspace_id, source="postgres-preview", nodes=[], edges=[])

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
                    add_edge(_edge(f"workspace-source:{row['doc_id']}", f"workspace:{workspace_id_str}", node_id, "CONTAINS"))

                cur.execute(
                    """
                    SELECT sc.chunk_id, sc.doc_id, sc.chunk_no, sc.chunk_text, sc.start_line, sc.end_line, sc.token_count
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
                    title = f"Chunk {row['chunk_no']}"
                    add_node(_node(node_id, "chunk", "Chunk", title, _excerpt(row["chunk_text"]), row))
                    add_edge(_edge(f"source-chunk:{row['doc_id']}:{row['chunk_id']}", f"source:{row['doc_id']}", node_id, "HAS_CHUNK"))

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
                    add_edge(_edge(f"workspace-memory:{row['memory_id']}", f"workspace:{workspace_id_str}", node_id, "CONTAINS"))
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
                    add_node(_node(node_id, "entity", "Entity", row["canonical_name"], row["entity_type"], row))
                    add_edge(_edge(f"workspace-entity:{row['entity_id']}", f"workspace:{workspace_id_str}", node_id, "CONTAINS"))

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
                    add_edge(_edge(f"workspace-scene:{row['scene_id']}", f"workspace:{workspace_id_str}", node_id, "CONTAINS"))

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
                           generated_from_scene_id, generated_from_memory_id, needs_rebuild, status, updated_at
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
                    add_edge(_edge(f"workspace-wiki:{row['page_id']}", f"workspace:{workspace_id_str}", node_id, "CONTAINS"))
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

        return GraphResponse(workspace_id=workspace_id, source="postgres-preview", nodes=list(nodes.values()), edges=list(edges.values()))


class Neo4jGraphStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

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
            driver = self._driver()
            with driver:
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
        driver = self._driver()
        workspace_id = str(graph.workspace_id)
        with driver:
            with driver.session(database=self.settings.neo4j_database) as session:
                session.run(
                    "MATCH (n:MemoryBaseNode {workspace_id: $workspace_id}) DETACH DELETE n",
                    workspace_id=workspace_id,
                )
                for node in graph.nodes:
                    session.run(
                        """
                        MERGE (n:MemoryBaseNode {id: $id})
                        SET n.workspace_id = $workspace_id,
                            n.type = $type,
                            n.label = $label,
                            n.title = $title,
                            n.subtitle = $subtitle,
                            n.properties_json = $properties_json
                        """,
                        id=node.id,
                        workspace_id=workspace_id,
                        type=node.type,
                        label=node.label,
                        title=node.title,
                        subtitle=node.subtitle,
                        properties_json=_jsonish(node.properties),
                    )
                for edge in graph.edges:
                    rel_type = _safe_rel_type(edge.type)
                    session.run(
                        f"""
                        MATCH (a:MemoryBaseNode {{id: $source}})
                        MATCH (b:MemoryBaseNode {{id: $target}})
                        MERGE (a)-[r:{rel_type} {{id: $id}}]->(b)
                        SET r.label = $label,
                            r.properties_json = $properties_json
                        """,
                        id=edge.id,
                        source=edge.source,
                        target=edge.target,
                        label=edge.label,
                        properties_json=_jsonish(edge.properties),
                    )
        return GraphSyncResponse(
            workspace_id=graph.workspace_id,
            status="synced",
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )

    def load_workspace_graph(self, workspace_id: UUID, limit: int) -> GraphResponse:
        self._ensure_available()
        driver = self._driver()
        with driver:
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
                    MATCH (a:MemoryBaseNode {workspace_id: $workspace_id})-[r]->(b:MemoryBaseNode {workspace_id: $workspace_id})
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

    def _ensure_available(self) -> None:
        health = self.health()
        if not health.available:
            raise GraphUnavailableError(health.error or "Neo4j is unavailable")

    def _driver(self):
        if GraphDatabase is None:
            raise GraphUnavailableError("neo4j Python package is not installed")
        return GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )


class GraphService:
    def __init__(self, repository: GraphRepository, store: Neo4jGraphStore) -> None:
        self.repository = repository
        self.store = store

    def health(self) -> GraphHealthResponse:
        return self.store.health()

    def preview_workspace(self, workspace_id: UUID, limit: int) -> GraphResponse:
        return self.repository.build_workspace_graph(workspace_id, limit)

    def sync_workspace(self, workspace_id: UUID, limit: int) -> GraphSyncResponse:
        graph = self.repository.build_workspace_graph(workspace_id, limit)
        return self.store.sync(graph)

    def load_workspace_graph(self, workspace_id: UUID, limit: int, fallback: bool) -> GraphResponse:
        try:
            graph = self.store.load_workspace_graph(workspace_id, limit)
            if graph.nodes:
                return graph
        except GraphUnavailableError:
            if not fallback:
                raise
        return self.repository.build_workspace_graph(workspace_id, limit)


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
    import json

    return json.dumps(value, ensure_ascii=False, default=str)


def _safe_rel_type(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.upper())
    return cleaned or "RELATED_TO"


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
    import json

    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except (TypeError, json.JSONDecodeError):
        return {"value": value}
