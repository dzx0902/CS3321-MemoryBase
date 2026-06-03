from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models.governance import (
    AuditLifecycleResponse,
    AuditQueryResponse,
    AuditStatisticsResponse,
    ConflictCreateRequest,
    ConflictListResponse,
    ConflictResponse,
    ConflictUpdateRequest,
    ForgetRequestCreateRequest,
    ForgetRequestListResponse,
    ForgetRequestResponse,
    ForgetRequestUpdateRequest,
    ForgetVerificationResponse,
    PolicyCreateRequest,
    PolicyDeleteResponse,
    PolicyListResponse,
    PolicyResponse,
    PolicyUpdateRequest,
    TimelineCreateRequest,
    TimelineEntryResponse,
    TimelineListResponse,
)
from ..services.governance_service import (
    ConflictAlreadyExistsError,
    ConflictNotFoundError,
    ConflictValidationError,
    ForgetRequestNotFoundError,
    GovernanceService,
    PolicyNotFoundError,
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
    principal_type: str | None = Query(default=None),
    principal_id: UUID | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    effect: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> PolicyListResponse:
    return service.list_policies(
        workspace_id=workspace_id,
        principal_type=principal_type,
        principal_id=principal_id,
        resource_type=resource_type,
        effect=effect,
        page=page,
        page_size=page_size,
    )


@router.patch("/policies/{policy_id}", response_model=PolicyResponse)
def update_policy(
    policy_id: UUID,
    payload: PolicyUpdateRequest,
    workspace_id: UUID = Query(...),
    service: GovernanceService = Depends(get_governance_service),
) -> PolicyResponse:
    try:
        return service.update_policy(
            policy_id=policy_id,
            workspace_id=workspace_id,
            payload=payload,
        )
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/policies/{policy_id}", response_model=PolicyDeleteResponse)
def delete_policy(
    policy_id: UUID,
    workspace_id: UUID = Query(...),
    service: GovernanceService = Depends(get_governance_service),
) -> PolicyDeleteResponse:
    try:
        return service.delete_policy(policy_id=policy_id, workspace_id=workspace_id)
    except PolicyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/audit", response_model=AuditQueryResponse)
def list_audit_logs(
    workspace_id: UUID | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    actor_id: UUID | None = Query(default=None),
    action_type: str | None = Query(default=None),
    target_type: str | None = Query(default=None),
    target_id: UUID | None = Query(default=None),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
    include_diff: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> AuditQueryResponse:
    try:
        return service.list_audit_logs(
            workspace_id=workspace_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
            include_diff=include_diff,
            page=page,
            page_size=page_size,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/audit/lifecycle", response_model=AuditLifecycleResponse)
def list_audit_lifecycle(
    workspace_id: UUID = Query(...),
    target_type: str = Query(...),
    target_id: UUID = Query(...),
    service: GovernanceService = Depends(get_governance_service),
) -> AuditLifecycleResponse:
    try:
        return service.list_audit_lifecycle(
            workspace_id=workspace_id,
            target_type=target_type,
            target_id=target_id,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/audit/actors/{actor_type}/{actor_id}/timeline", response_model=AuditQueryResponse)
def list_actor_timeline(
    actor_type: str,
    actor_id: UUID,
    workspace_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> AuditQueryResponse:
    return service.list_actor_timeline(
        workspace_id=workspace_id,
        actor_type=actor_type,
        actor_id=actor_id,
        page=page,
        page_size=page_size,
    )


@router.get("/audit/statistics", response_model=AuditStatisticsResponse)
def get_audit_statistics(
    workspace_id: UUID | None = Query(default=None),
    group_by: str = Query(default="action_type", pattern="^(action_type|actor_type|target_type)$"),
    service: GovernanceService = Depends(get_governance_service),
) -> AuditStatisticsResponse:
    return service.get_audit_statistics(workspace_id=workspace_id, group_by=group_by)


@router.get("/conflicts", response_model=ConflictListResponse)
def list_conflicts(
    workspace_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: GovernanceService = Depends(get_governance_service),
) -> ConflictListResponse:
    return service.list_conflicts(
        workspace_id=workspace_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.post("/conflicts", response_model=ConflictResponse, status_code=status.HTTP_201_CREATED)
def create_conflict(
    payload: ConflictCreateRequest,
    service: GovernanceService = Depends(get_governance_service),
) -> ConflictResponse:
    try:
        return service.create_conflict(payload)
    except ConflictAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ConflictValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TargetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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


@router.post("/forget-requests/{request_id}/verify", response_model=ForgetVerificationResponse)
def verify_forget_request(
    request_id: UUID,
    workspace_id: UUID = Query(...),
    service: GovernanceService = Depends(get_governance_service),
) -> ForgetVerificationResponse:
    try:
        return service.verify_forget_request(request_id=request_id, workspace_id=workspace_id)
    except ForgetRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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
