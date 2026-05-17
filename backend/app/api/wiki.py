from __future__ import annotations

from app.api.deps import get_wiki_service
from app.models.wiki import WikiExportRequest, WikiExportResponse
from app.services.wiki_service import WikiService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/wiki", tags=["wiki"])


@router.post("/export", response_model=WikiExportResponse)
def export_wiki(
    payload: WikiExportRequest,
    service: WikiService = Depends(get_wiki_service),
) -> WikiExportResponse:
    return service.export_page(payload)
