from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RecallRequest(BaseModel):
    workspace_id: UUID
    agent_id: UUID | None = None
    query_text: str = Field(min_length=1)
    memory_type: str | None = None
    access_level: str | None = None
    status: str | None = "active"
    as_of: datetime | None = None
    limit: int = Field(default=10, ge=1, le=50)


class RecallContextPackRequest(RecallRequest):
    max_tokens: int = Field(default=3000, ge=100, le=16000)


class RecallEvidenceResponse(BaseModel):
    chunk_id: UUID
    doc_id: UUID
    source_title: str
    chunk_no: int
    chunk_text: str
    start_line: int | None = None
    end_line: int | None = None
    evidence_role: str
    weight: float


class RecallMemoryResponse(BaseModel):
    memory_id: UUID
    memory_type: str
    canonical_text: str
    summary: str | None = None
    confidence: float
    importance: int
    status: str
    access_level: str
    score: float
    evidence: list[RecallEvidenceResponse]


class RecallResponse(BaseModel):
    recall_id: UUID | None = None
    workspace_id: UUID
    query_text: str
    result_count: int
    memories: list[RecallMemoryResponse]
    context_pack: dict[str, Any]
    created_at: datetime | None = None


class RecallContextPackResponse(BaseModel):
    markdown: str
    recall_id: UUID | None = None
    result_count: int
    citation_map: dict[str, Any]
    token_count: int
