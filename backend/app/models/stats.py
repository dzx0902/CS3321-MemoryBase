from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StatsCountResponse(BaseModel):
    name: str
    count: int


class MemoryStatisticResponse(BaseModel):
    memory_type: str
    status: str
    access_level: str
    memory_count: int
    avg_confidence: float | None = None
    avg_importance: float | None = None


class StatsOverviewResponse(BaseModel):
    workspace_id: UUID
    source_count: int
    chunk_count: int
    memory_count: int
    active_memory_count: int
    recall_count: int
    wiki_page_count: int
    policy_count: int
    audit_count: int
    conflict_count: int
    forget_request_count: int
    entity_count: int
    scene_count: int
    latest_activity_at: datetime | None = None
    memory_statistics: list[MemoryStatisticResponse]
    memory_type_counts: list[StatsCountResponse]
    source_status_counts: list[StatsCountResponse]
