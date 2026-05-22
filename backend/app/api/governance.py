from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.governance import (
    AuditQueryResponse,
    ConflictListResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    ForgetRequestCreateRequest,
    ForgetRequestListResponse,
    ForgetRequestResponse,
    ForgetRequestUpdateRequest,
    PolicyCreateRequest,
    PolicyListResponse,
    PolicyResponse,
    TimelineCreateRequest,
    TimelineEntryResponse,
    TimelineListResponse,
)
from ..services.governance_service import (
    ConflictNotFoundError,
    ForgetRequestNotFoundError,
    GovernanceService,
    ReviewerRequiredError,
    TargetNotFoundError,
    UnsupportedForgetTargetError,
    UserNotFoundError,
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


@router.get("/policies", response_model=PolicyListResponse)
def list_policies(
    workspace_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> PolicyListResponse:
    return service.list_policies(workspace_id=workspace_id, page=page, page_size=page_size)


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


@router.get("/conflicts", response_model=ConflictListResponse)
def list_conflicts(
    workspace_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> ConflictListResponse:
    return service.list_conflicts(workspace_id=workspace_id, page=page, page_size=page_size)


@router.patch("/conflicts/{conflict_id}", response_model=ConflictResponse)
def update_conflict(
    conflict_id: UUID,
    payload: ConflictUpdateRequest,
    workspace_id: UUID = Query(...),
    service: GovernanceService = Depends(get_governance_service),
) -> ConflictResponse:
    try:
        return service.update_conflict(conflict_id, workspace_id, payload)
    except ConflictNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/forget-requests",
    response_model=ForgetRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_forget_request(
    payload: ForgetRequestCreateRequest,
    service: GovernanceService = Depends(get_governance_service),
) -> ForgetRequestResponse:
    try:
        return service.create_forget_request(payload)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (TargetNotFoundError, UserNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedForgetTargetError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/forget-requests", response_model=ForgetRequestListResponse)
def list_forget_requests(
    workspace_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> ForgetRequestListResponse:
    return service.list_forget_requests(
        workspace_id=workspace_id,
        status=status,
        target_type=target_type,
        page=page,
        page_size=page_size,
    )


@router.patch("/forget-requests/{request_id}", response_model=ForgetRequestResponse)
def update_forget_request(
    request_id: UUID,
    payload: ForgetRequestUpdateRequest,
    workspace_id: UUID = Query(...),
    service: GovernanceService = Depends(get_governance_service),
) -> ForgetRequestResponse:
    try:
        return service.update_forget_request(request_id, workspace_id, payload)
    except ForgetRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (TargetNotFoundError, UserNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnsupportedForgetTargetError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except ReviewerRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/timeline", response_model=TimelineListResponse)
def list_timeline(
    workspace_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> TimelineListResponse:
    return service.list_timeline(workspace_id=workspace_id, page=page, page_size=page_size)


@router.post("/timeline", response_model=TimelineEntryResponse, status_code=status.HTTP_201_CREATED)
def create_timeline_entry(
    payload: TimelineCreateRequest,
    service: GovernanceService = Depends(get_governance_service),
) -> TimelineEntryResponse:
    return service.create_timeline_entry(payload)
