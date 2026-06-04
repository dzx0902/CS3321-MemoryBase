from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.recall import (
    RecallContextPackRequest,
    RecallContextPackResponse,
    RecallRequest,
    RecallResponse,
)
from ..services.context_pack_service import format_context_pack
from ..services.recall_service import RecallService
from .deps import get_recall_service

router = APIRouter(prefix="/recall", tags=["recall"])


@router.post("", response_model=RecallResponse)
def execute_recall(
    payload: RecallRequest,
    service: RecallService = Depends(get_recall_service),
) -> RecallResponse:
    return service.execute(payload)


@router.post("/context-pack", response_model=RecallContextPackResponse)
def execute_context_pack(
    payload: RecallContextPackRequest,
    service: RecallService = Depends(get_recall_service),
) -> RecallContextPackResponse:
    recall = service.execute(RecallRequest(**payload.model_dump(exclude={"max_tokens"})))
    context = format_context_pack(recall, max_tokens=payload.max_tokens)
    return RecallContextPackResponse(
        markdown=context.markdown,
        recall_id=recall.recall_id,
        result_count=recall.result_count,
        citation_map=context.citation_map,
        token_count=context.token_count,
        token_budget=context.token_budget,
        selected_memories=context.selected_memories,
        supporting_evidence=context.supporting_evidence,
        conflict_warnings=context.conflict_warnings,
        risk_notes=context.risk_notes,
        excluded_memories=context.excluded_memories,
    )
