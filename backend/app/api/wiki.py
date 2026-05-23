from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.wiki import (
    WikiBatchExportRequest,
    WikiBatchExportResponse,
    WikiExportRequest,
    WikiExportResponse,
)
from ..services.wiki_service import WikiService
from .deps import get_wiki_service

router = APIRouter(prefix="/wiki", tags=["wiki"])


@router.post("/export", response_model=WikiExportResponse | WikiBatchExportResponse)
def export_wiki(
    payload: WikiExportRequest | WikiBatchExportRequest,
    service: WikiService = Depends(get_wiki_service),
) -> WikiExportResponse | WikiBatchExportResponse:
    if isinstance(payload, WikiBatchExportRequest):
        return service.export_pages(payload)
    return service.export_page(payload)
