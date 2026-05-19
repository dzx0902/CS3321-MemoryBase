from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.source import (
    SourceCreateRequest,
    SourceDetailResponse,
    SourceImportResponse,
    SourceListResponse,
)
from ..services.source_service import (
    SourceConflictError,
    SourceNotFoundError,
    SourceService,
)
from .deps import get_source_service

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceImportResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreateRequest,
    service: SourceService = Depends(get_source_service),
) -> SourceImportResponse:
    try:
        return service.import_source(payload)
    except SourceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get("", response_model=SourceListResponse)
def list_sources(
    workspace_id: UUID | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: SourceService = Depends(get_source_service),
) -> SourceListResponse:
    return service.list_sources(
        workspace_id=workspace_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/{doc_id}", response_model=SourceDetailResponse)
def get_source(
    doc_id: UUID,
    workspace_id: UUID = Query(...),
    service: SourceService = Depends(get_source_service),
) -> SourceDetailResponse:
    try:
        return service.get_source(doc_id, workspace_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
