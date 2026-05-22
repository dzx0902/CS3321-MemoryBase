from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..models.agent import AgentRegisterRequest, AgentRegisterResponse
from ..services.agent_service import AgentService, AgentWorkspaceNotFoundError
from .deps import get_agent_service

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
