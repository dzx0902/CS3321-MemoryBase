from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.source import (
    SourceCreateRequest,
    SourceDetailResponse,
    SourceImportResponse,
    SourceSummaryResponse,
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


@router.get("", response_model=list[SourceSummaryResponse])
def list_sources(
    workspace_id: UUID | None = Query(default=None),
    service: SourceService = Depends(get_source_service),
) -> list[SourceSummaryResponse]:
    return service.list_sources(workspace_id=workspace_id)


@router.get("/{doc_id}", response_model=SourceDetailResponse)
def get_source(
    doc_id: UUID,
    service: SourceService = Depends(get_source_service),
) -> SourceDetailResponse:
    try:
        return service.get_source(doc_id)
    except SourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
