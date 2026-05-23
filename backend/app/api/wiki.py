from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.wiki import (
    WikiBatchExportRequest,
    WikiBatchExportResponse,
    WikiExportRequest,
    WikiExportResponse,
    WikiPageDetailResponse,
    WikiPageListResponse,
    WikiRevisionListResponse,
)
from ..services.wiki_service import WikiService
from .deps import get_wiki_service

router = APIRouter(prefix="/wiki", tags=["wiki"])


@router.get("", response_model=WikiPageListResponse)
def list_wiki_pages(
    workspace_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: WikiService = Depends(get_wiki_service),
) -> WikiPageListResponse:
    return service.list_pages(
        workspace_id=workspace_id,
        status=status_filter,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/{page_id}", response_model=WikiPageDetailResponse)
def get_wiki_page(
    page_id: UUID,
    workspace_id: UUID = Query(...),
    service: WikiService = Depends(get_wiki_service),
) -> WikiPageDetailResponse:
    page = service.get_page(page_id=page_id, workspace_id=workspace_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="wiki page not found")
    return page


@router.get("/{page_id}/revisions", response_model=WikiRevisionListResponse)
def list_wiki_revisions(
    page_id: UUID,
    workspace_id: UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: WikiService = Depends(get_wiki_service),
) -> WikiRevisionListResponse:
    return service.list_revisions(
        page_id=page_id,
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
    )


@router.post("/export", response_model=WikiExportResponse | WikiBatchExportResponse)
def export_wiki(
    payload: WikiExportRequest | WikiBatchExportRequest,
    service: WikiService = Depends(get_wiki_service),
) -> WikiExportResponse | WikiBatchExportResponse:
    if isinstance(payload, WikiBatchExportRequest):
        return service.export_pages(payload)
    return service.export_page(payload)
