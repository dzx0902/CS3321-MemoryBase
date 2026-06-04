from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ..models.memory import ActorContext, EditorType
from ..models.memory_extraction import (
    MemoryCandidateDecisionResponse,
    MemoryCandidateListResponse,
    MemoryExtractionFromChunksRequest,
    MemoryExtractionResponse,
)
from ..services.memory_extraction_service import (
    MemoryExtractionService,
    MemoryExtractionValidationError,
)
from ..services.memory_service import MemoryNotFoundError, MemoryValidationError
from .deps import get_memory_extraction_service

router = APIRouter(tags=["memory-extraction"])


@router.post(
    "/memory-extraction/from-chunks",
    response_model=MemoryExtractionResponse,
    status_code=status.HTTP_201_CREATED,
)
def extract_from_chunks(
    payload: MemoryExtractionFromChunksRequest,
    x_actor_type: EditorType = Header(default="system", alias="X-Actor-Type"),
    x_actor_id: UUID | None = Header(default=None, alias="X-Actor-Id"),
    service: MemoryExtractionService = Depends(get_memory_extraction_service),
) -> MemoryExtractionResponse:
    try:
        actor = ActorContext(
            actor_type=x_actor_type,
            actor_id=x_actor_id,
            revision_reason="rule-based memory extraction",
        )
        candidates = service.extract_from_chunks(payload, actor)
    except MemoryExtractionValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MemoryExtractionResponse(
        workspace_id=payload.workspace_id,
        created_count=len(candidates),
        candidates=candidates,
    )


@router.get("/memory-candidates", response_model=MemoryCandidateListResponse)
def list_memory_candidates(
    workspace_id: UUID | None = Query(default=None),
    memory_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: MemoryExtractionService = Depends(get_memory_extraction_service),
) -> MemoryCandidateListResponse:
    return service.list_candidates(
        workspace_id=workspace_id,
        memory_type=memory_type,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/memory-candidates/{memory_id}/approve",
    response_model=MemoryCandidateDecisionResponse,
)
def approve_memory_candidate(
    memory_id: UUID,
    workspace_id: UUID = Query(...),
    x_actor_type: EditorType = Header(default="user", alias="X-Actor-Type"),
    x_actor_id: UUID | None = Header(default=None, alias="X-Actor-Id"),
    service: MemoryExtractionService = Depends(get_memory_extraction_service),
) -> MemoryCandidateDecisionResponse:
    try:
        actor = ActorContext(
            actor_type=x_actor_type,
            actor_id=x_actor_id,
            revision_reason="approve candidate memory",
        )
        return MemoryCandidateDecisionResponse(
            memory=service.approve_candidate(memory_id, workspace_id, actor)
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MemoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/memory-candidates/{memory_id}/reject",
    response_model=MemoryCandidateDecisionResponse,
)
def reject_memory_candidate(
    memory_id: UUID,
    workspace_id: UUID = Query(...),
    x_actor_type: EditorType = Header(default="user", alias="X-Actor-Type"),
    x_actor_id: UUID | None = Header(default=None, alias="X-Actor-Id"),
    service: MemoryExtractionService = Depends(get_memory_extraction_service),
) -> MemoryCandidateDecisionResponse:
    try:
        actor = ActorContext(
            actor_type=x_actor_type,
            actor_id=x_actor_id,
            revision_reason="reject candidate memory",
        )
        return MemoryCandidateDecisionResponse(
            memory=service.reject_candidate(memory_id, workspace_id, actor)
        )
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MemoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
