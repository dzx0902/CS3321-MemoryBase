from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from .common import PageResponse

PrincipalType = Literal["user", "agent", "role"]
ResourceType = Literal["memory_item", "source_document", "wiki_page", "workspace"]
ResourceScope = Literal["public", "project", "team", "private", "all"]
PolicyEffect = Literal["allow", "deny"]
TimelineEventType = Literal["meeting", "proposal", "decision", "revision", "conflict", "resolution"]
ConflictStatus = Literal["open", "resolved", "ignored"]
ForgetTargetType = Literal["memory_item", "source_document", "wiki_page", "entity"]
ForgetRequestStatus = Literal["pending", "approved", "rejected", "done"]


class PolicyCreateRequest(BaseModel):
    workspace_id: UUID
    principal_type: PrincipalType
    principal_id: UUID | None = None
    resource_type: ResourceType
    resource_scope: ResourceScope = "project"
    effect: PolicyEffect
    predicate_json: dict[str, Any] = Field(default_factory=dict)


class PolicyUpdateRequest(BaseModel):
    resource_scope: ResourceScope | None = None
    effect: PolicyEffect | None = None
    predicate_json: dict[str, Any] | None = None


class PolicyResponse(BaseModel):
    policy_id: UUID
    workspace_id: UUID
    principal_type: PrincipalType
    principal_id: UUID | None = None
    resource_type: ResourceType
    resource_scope: ResourceScope
    effect: PolicyEffect
    predicate_json: dict[str, Any]
    created_at: datetime


class PolicyListResponse(PageResponse[PolicyResponse]):
    pass


class PolicyDeleteResponse(BaseModel):
    policy_id: UUID
    workspace_id: UUID
    deleted: bool


class AuditQueryResponse(BaseModel):
    items: list["AuditEntryResponse"]
    page: int
    page_size: int
    total: int


class AuditEntryResponse(BaseModel):
    audit_id: UUID
    workspace_id: UUID
    actor_type: str
    actor_id: UUID | None = None
    action_type: str
    target_type: str
    target_id: UUID | None = None
    before_json: dict[str, Any] | None = None
    after_json: dict[str, Any] | None = None
    diff_json: dict[str, Any] | None = None
    created_at: datetime


class AuditLifecycleEventResponse(BaseModel):
    ts: datetime
    kind: str
    payload: dict[str, Any]


class AuditLifecycleResponse(BaseModel):
    items: list[AuditLifecycleEventResponse]


class AuditStatisticResponse(BaseModel):
    group_key: str
    event_count: int
    last_event_at: datetime | None = None


class AuditStatisticsResponse(BaseModel):
    group_by: str
    items: list[AuditStatisticResponse]


class AgentVisibleMemoryResponse(BaseModel):
    memory_id: UUID
    workspace_id: UUID
    memory_type: str
    canonical_text: str
    summary: str | None = None
    confidence: float
    importance: int
    status: str
    access_level: str
    updated_at: datetime


class AgentVisibleMemoryListResponse(PageResponse[AgentVisibleMemoryResponse]):
    pass


class ConflictResponse(BaseModel):
    conflict_id: UUID
    workspace_id: UUID
    conflict_type: str
    status: ConflictStatus
    resolution_note: str | None = None
    resolved_by_actor_type: str | None = None
    resolved_by_actor_id: UUID | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    left_memory_id: UUID
    left_memory_type: str
    left_memory_text: str
    left_memory_summary: str | None = None
    right_memory_id: UUID
    right_memory_type: str
    right_memory_text: str
    right_memory_summary: str | None = None


class ConflictListResponse(PageResponse[ConflictResponse]):
    pass


class ConflictDetectionResponse(BaseModel):
    memory_id: UUID
    detected_count: int
    conflicts: list[ConflictResponse]


class ConflictCreateRequest(BaseModel):
    workspace_id: UUID
    left_memory_id: UUID
    right_memory_id: UUID
    conflict_type: Literal[
        "semantic",
        "temporal",
        "policy",
        "duplicate",
        "contradiction",
        "supersession",
        "uncertain",
    ] = "semantic"
    resolution_note: str | None = None
    actor_type: Literal["user", "agent", "system"] = "system"
    actor_id: UUID | None = None


class ConflictUpdateRequest(BaseModel):
    status: ConflictStatus
    resolution_note: str | None = None
    actor_type: Literal["user", "agent", "system"] = "user"
    actor_id: UUID | None = None


class ForgetRequestCreateRequest(BaseModel):
    workspace_id: UUID
    target_type: ForgetTargetType
    target_id: UUID
    requester_user_id: UUID | None = None
    reason: str = Field(min_length=1)


class ForgetRequestUpdateRequest(BaseModel):
    status: ForgetRequestStatus
    reviewed_by_user_id: UUID | None = None

    @model_validator(mode="after")
    def validate_reviewer_for_status(self) -> "ForgetRequestUpdateRequest":
        if self.status != "pending" and self.reviewed_by_user_id is None:
            raise ValueError("reviewed_by_user_id is required for reviewed requests")
        return self


class ForgetRequestResponse(BaseModel):
    request_id: UUID
    workspace_id: UUID
    target_type: ForgetTargetType
    target_id: UUID
    requester_user_id: UUID | None = None
    reviewed_by_user_id: UUID | None = None
    reason: str
    status: ForgetRequestStatus
    requested_at: datetime
    resolved_at: datetime | None = None


class ForgetRequestListResponse(PageResponse[ForgetRequestResponse]):
    pass


class ForgetVerificationCheckResponse(BaseModel):
    name: str
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


class ForgetVerificationResponse(BaseModel):
    request_id: UUID
    workspace_id: UUID
    target_type: ForgetTargetType
    target_id: UUID
    status: ForgetRequestStatus
    passed: bool
    checks: list[ForgetVerificationCheckResponse]


class TimelineCreateRequest(BaseModel):
    workspace_id: UUID
    title: str = Field(min_length=1, max_length=240)
    event_type: TimelineEventType
    event_time: datetime
    description: str | None = None
    importance: int = Field(default=3, ge=1, le=5)
    memory_id: UUID | None = None
    doc_id: UUID | None = None


class TimelineEntryResponse(BaseModel):
    timeline_id: UUID
    workspace_id: UUID
    event_time: datetime
    event_type: TimelineEventType
    title: str
    description: str | None = None
    importance: int
    memory_id: UUID | None = None
    doc_id: UUID | None = None
    memory_type: str | None = None
    memory_text: str | None = None
    source_title: str | None = None


class TimelineListResponse(PageResponse[TimelineEntryResponse]):
    pass
