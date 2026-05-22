from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.conversation import (
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
)
from ..services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
    ConversationValidationError,
)
from .deps import get_conversation_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreateRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> SessionResponse:
    try:
        return service.create_session(payload)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConversationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=SessionListResponse)
def list_sessions(
    workspace_id: UUID = Query(...),
    agent_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: ConversationService = Depends(get_conversation_service),
) -> SessionListResponse:
    try:
        return service.list_sessions(
            workspace_id=workspace_id,
            agent_id=agent_id,
            page=page,
            page_size=page_size,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    workspace_id: UUID | None = Query(default=None),
    service: ConversationService = Depends(get_conversation_service),
) -> SessionResponse:
    try:
        return service.get_session(session_id, workspace_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
