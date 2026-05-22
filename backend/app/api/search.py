from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.search import SearchRequest, SearchResponse
from ..services.search_service import SearchService
from .deps import get_search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def execute_search(
    payload: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    return service.execute(payload)
