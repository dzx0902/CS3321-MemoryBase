from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.wiki import WikiExportRequest, WikiExportResponse
from ..services.wiki_service import WikiService
from .deps import get_wiki_service

router = APIRouter(prefix="/wiki", tags=["wiki"])


@router.post("/export", response_model=WikiExportResponse)
def export_wiki(
    payload: WikiExportRequest,
    service: WikiService = Depends(get_wiki_service),
) -> WikiExportResponse:
    return service.export_page(payload)
