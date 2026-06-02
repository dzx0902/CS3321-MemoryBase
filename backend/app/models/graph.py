from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

GraphSource = Literal["neo4j", "postgres-preview"]


class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    title: str
    subtitle: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    workspace_id: UUID
    source: GraphSource
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphHealthResponse(BaseModel):
    enabled: bool
    available: bool
    uri: str
    database: str
    error: str | None = None


class GraphSyncResponse(BaseModel):
    workspace_id: UUID
    status: Literal["synced"]
    node_count: int
    edge_count: int
