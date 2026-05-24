from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .common import PageResponse


class EntityResponse(BaseModel):
    entity_id: UUID
    workspace_id: UUID
    canonical_name: str
    entity_type: str
    description: str | None = None
    status: str
    memory_count: int = 0
    created_at: datetime
    updated_at: datetime


class SceneResponse(BaseModel):
    scene_id: UUID
    workspace_id: UUID
    scene_slug: str
    title: str
    summary: str | None = None
    memory_count: int = 0
    created_at: datetime
    updated_at: datetime


class EntityListResponse(PageResponse[EntityResponse]):
    pass


class SceneListResponse(PageResponse[SceneResponse]):
    pass
