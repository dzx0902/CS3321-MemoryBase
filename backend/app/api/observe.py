from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..models.conversation import (
    MessageBatchCreateRequest,
    MessageBatchResponse,
    MessageCreateRequest,
    MessageResponse,
)
from ..services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
    ConversationValidationError,
)
from .deps import get_conversation_service

router = APIRouter(prefix="/observe", tags=["observe"])


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def observe_message(
    payload: MessageCreateRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> MessageResponse:
    try:
        return service.create_message(payload)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConversationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/batch", response_model=MessageBatchResponse, status_code=status.HTTP_201_CREATED)
def observe_batch(
    payload: MessageBatchCreateRequest,
    service: ConversationService = Depends(get_conversation_service),
) -> MessageBatchResponse:
    try:
        return service.create_messages(payload)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConversationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
