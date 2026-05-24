from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ..models.stats import StatsOverviewResponse
from ..services.stats_service import StatsService
from .deps import get_stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverviewResponse)
def get_stats_overview(
    workspace_id: UUID = Query(...),
    service: StatsService = Depends(get_stats_service),
) -> StatsOverviewResponse:
    return service.overview(workspace_id=workspace_id)
