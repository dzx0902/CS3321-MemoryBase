from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.agent import AgentRegisterRequest, AgentRegisterResponse
from ..models.governance import AgentVisibleMemoryListResponse
from ..services.agent_service import AgentService, AgentWorkspaceNotFoundError
from ..services.governance_service import GovernanceService
from .deps import get_agent_service, get_governance_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_agent(
    payload: AgentRegisterRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentRegisterResponse:
    try:
        return service.register_agent(payload)
    except AgentWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{agent_id}/visible-memories", response_model=AgentVisibleMemoryListResponse)
def list_agent_visible_memories(
    agent_id: UUID,
    workspace_id: UUID = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> AgentVisibleMemoryListResponse:
    return service.list_agent_visible_memories(
        agent_id=agent_id,
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
    )
