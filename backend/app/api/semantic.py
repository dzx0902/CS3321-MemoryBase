from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ..models.semantic import EntityListResponse, SceneListResponse
from ..services.semantic_service import SemanticService
from .deps import get_semantic_service

router = APIRouter(tags=["semantic"])


@router.get("/entities", response_model=EntityListResponse)
def list_entities(
    workspace_id: UUID | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: SemanticService = Depends(get_semantic_service),
) -> EntityListResponse:
    return service.list_entities(
        workspace_id=workspace_id,
        entity_type=entity_type,
        status=status_filter,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/scenes", response_model=SceneListResponse)
def list_scenes(
    workspace_id: UUID | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: SemanticService = Depends(get_semantic_service),
) -> SceneListResponse:
    return service.list_scenes(
        workspace_id=workspace_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
