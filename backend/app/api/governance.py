from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.governance import (
    AuditQueryResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    PolicyCreateRequest,
    PolicyResponse,
    TimelineCreateRequest,
    TimelineEntryResponse,
)
from ..services.governance_service import (
    ConflictNotFoundError,
    GovernanceService,
    WorkspaceNotFoundError,
)
from .deps import get_governance_service

router = APIRouter(tags=["governance"])


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreateRequest,
    service: GovernanceService = Depends(get_governance_service),
) -> PolicyResponse:
    return service.create_policy(payload)


@router.get("/policies", response_model=list[PolicyResponse])
def list_policies(
    workspace_id: UUID | None = Query(default=None),
    service: GovernanceService = Depends(get_governance_service),
) -> list[PolicyResponse]:
    return service.list_policies(workspace_id=workspace_id)


@router.get("/audit", response_model=AuditQueryResponse)
def list_audit_logs(
    workspace_id: UUID | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    action_type: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: UUID | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> AuditQueryResponse:
    try:
        return service.list_audit_logs(
            workspace_id=workspace_id,
            actor_type=actor_type,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/conflicts", response_model=list[ConflictResponse])
def list_conflicts(
    workspace_id: UUID | None = Query(default=None),
    service: GovernanceService = Depends(get_governance_service),
) -> list[ConflictResponse]:
    return service.list_conflicts(workspace_id=workspace_id)


@router.patch("/conflicts/{conflict_id}", response_model=ConflictResponse)
def update_conflict(
    conflict_id: UUID,
    payload: ConflictUpdateRequest,
    service: GovernanceService = Depends(get_governance_service),
) -> ConflictResponse:
    try:
        return service.update_conflict(conflict_id, payload)
    except ConflictNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/timeline", response_model=list[TimelineEntryResponse])
def list_timeline(
    workspace_id: UUID | None = Query(default=None),
    service: GovernanceService = Depends(get_governance_service),
) -> list[TimelineEntryResponse]:
    return service.list_timeline(workspace_id=workspace_id)


@router.post("/timeline", response_model=TimelineEntryResponse, status_code=status.HTTP_201_CREATED)
def create_timeline_entry(
    payload: TimelineCreateRequest,
    service: GovernanceService = Depends(get_governance_service),
) -> TimelineEntryResponse:
    return service.create_timeline_entry(payload)
