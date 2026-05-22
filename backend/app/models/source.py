from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import PageResponse

DocType = Literal["markdown", "txt", "meeting", "chat", "note", "report", "inline_agent_note"]


class HealthDatabaseStatus(BaseModel):
    status: Literal["up", "down"]
    error: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    database: HealthDatabaseStatus


class SourceCreateRequest(BaseModel):
    workspace_id: UUID
    title: str = Field(min_length=1, max_length=240)
    doc_type: DocType = "markdown"
    raw_text: str = Field(min_length=1)
    source_path: str | None = None
    session_id: UUID | None = None
    imported_by_user_id: UUID | None = None


class SourceImportResponse(BaseModel):
    doc_id: UUID
    chunk_count: int


class SourceChunkResponse(BaseModel):
    chunk_id: UUID
    chunk_no: int
    chunk_text: str
    start_line: int | None
    end_line: int | None
    token_count: int | None


class SourceSummaryResponse(BaseModel):
    doc_id: UUID
    workspace_id: UUID
    title: str
    doc_type: DocType
    source_path: str | None = None
    status: str = "active"
    imported_at: datetime
    chunk_count: int


class SourceListResponse(PageResponse[SourceSummaryResponse]):
    pass


class SourceDetailResponse(SourceSummaryResponse):
    session_id: UUID | None = None
    checksum: str | None = None
    raw_text: str
    chunks: list[SourceChunkResponse]
