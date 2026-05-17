from __future__ import annotations

from app.api.deps import get_recall_service
from app.models.recall import RecallRequest, RecallResponse
from app.services.recall_service import RecallService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/recall", tags=["recall"])


@router.post("", response_model=RecallResponse)
def execute_recall(
    payload: RecallRequest,
    service: RecallService = Depends(get_recall_service),
) -> RecallResponse:
    return service.execute(payload)
