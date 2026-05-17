from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.recall import RecallRequest, RecallResponse
from ..services.recall_service import RecallService
from .deps import get_recall_service

router = APIRouter(prefix="/recall", tags=["recall"])


@router.post("", response_model=RecallResponse)
def execute_recall(
    payload: RecallRequest,
    service: RecallService = Depends(get_recall_service),
) -> RecallResponse:
    return service.execute(payload)
