from __future__ import annotations

from uuid import UUID

from app.api.deps import get_memory_service
from app.models.memory import (
    MemoryCreateRequest,
    MemoryDeleteResponse,
    MemoryDetailResponse,
    MemorySummaryResponse,
    MemoryUpdateRequest,
)
from app.services.memory_service import MemoryNotFoundError, MemoryService
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemorySummaryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreateRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemorySummaryResponse:
    return service.create_memory(payload)


@router.get("", response_model=list[MemorySummaryResponse])
def list_memories(
    workspace_id: UUID | None = Query(default=None),
    memory_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    access_level: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: MemoryService = Depends(get_memory_service),
) -> list[MemorySummaryResponse]:
    return service.list_memories(
        workspace_id=workspace_id,
        memory_type=memory_type,
        status=status_filter,
        access_level=access_level,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/{memory_id}", response_model=MemoryDetailResponse)
def get_memory(
    memory_id: UUID,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryDetailResponse:
    try:
        return service.get_memory(memory_id)
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{memory_id}", response_model=MemoryDetailResponse)
def update_memory(
    memory_id: UUID,
    payload: MemoryUpdateRequest,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryDetailResponse:
    try:
        return service.update_memory(memory_id, payload)
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
def delete_memory(
    memory_id: UUID,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryDeleteResponse:
    try:
        return service.delete_memory(memory_id)
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
