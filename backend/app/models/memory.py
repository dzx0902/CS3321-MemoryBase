from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MemoryType = Literal[
    "episodic",
    "semantic",
    "profile",
    "procedural",
    "decision",
    "preference",
    "task",
    "risk",
]
MemoryStatus = Literal["active", "archived", "forgotten", "superseded", "conflicted"]
AccessLevel = Literal["public", "project", "team", "private"]
EvidenceRole = Literal["supports", "refutes", "context", "source"]
EditorType = Literal["user", "agent", "system"]


class MemoryCreateRequest(BaseModel):
    workspace_id: UUID
    memory_type: MemoryType
    canonical_text: str = Field(min_length=1)
    summary: str | None = None
    confidence: float = Field(default=0.7, ge=0, le=1)
    importance: int = Field(default=3, ge=1, le=5)
    access_level: AccessLevel = "project"
    created_from_doc_id: UUID | None = None
    owner_user_id: UUID | None = None
    owner_agent_id: UUID | None = None
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)


class MemoryUpdateRequest(BaseModel):
    canonical_text: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    importance: int | None = Field(default=None, ge=1, le=5)
    status: MemoryStatus | None = None
    access_level: AccessLevel | None = None
    evidence_chunk_ids: list[UUID] | None = None
    revision_reason: str = "manual update"
    editor_type: EditorType = "user"
    editor_id: UUID | None = None


class MemoryEvidenceResponse(BaseModel):
    evidence_id: UUID
    chunk_id: UUID
    evidence_role: EvidenceRole
    weight: float
    note: str | None = None
    doc_id: UUID
    source_title: str
    chunk_no: int
    chunk_text: str
    start_line: int | None = None
    end_line: int | None = None


class MemoryRevisionResponse(BaseModel):
    revision_no: int
    revision_text: str
    revision_summary: str | None = None
    revision_reason: str | None = None
    editor_type: EditorType
    editor_id: UUID | None = None
    created_at: datetime


class MemorySummaryResponse(BaseModel):
    memory_id: UUID
    workspace_id: UUID
    created_from_doc_id: UUID | None = None
    memory_type: MemoryType
    canonical_text: str
    summary: str | None = None
    confidence: float
    importance: int
    status: MemoryStatus
    access_level: AccessLevel
    current_revision_no: int
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0


class MemoryDetailResponse(MemorySummaryResponse):
    owner_user_id: UUID | None = None
    owner_agent_id: UUID | None = None
    valid_from: datetime
    valid_to: datetime | None = None
    superseded_by_memory_id: UUID | None = None
    evidence: list[MemoryEvidenceResponse]
    revisions: list[MemoryRevisionResponse]


class MemoryDeleteResponse(BaseModel):
    memory_id: UUID
    status: MemoryStatus
