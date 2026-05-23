from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

WikiPageType = Literal["source", "entity", "concept", "synthesis", "report", "timeline", "handbook"]


class WikiExportPageRequest(BaseModel):
    page_slug: str = Field(min_length=1, max_length=240)
    title: str = Field(min_length=1, max_length=240)
    page_type: WikiPageType = "report"
    max_memories: int = Field(default=20, ge=1, le=100)
    memory_ids: list[UUID] | None = None


class WikiExportRequest(WikiExportPageRequest):
    workspace_id: UUID
    write_files: bool = True


class WikiExportResponse(BaseModel):
    page_id: UUID
    workspace_id: UUID
    page_slug: str
    title: str
    page_type: WikiPageType
    revision_no: int
    body_markdown: str
    needs_rebuild: bool
    output_path: str
    frontmatter_json: dict[str, Any]
    source_doc_ids: list[UUID]
    created_at: datetime | None = None


class WikiBatchExportRequest(BaseModel):
    workspace_id: UUID
    pages: list[WikiExportPageRequest] = Field(min_length=1)
    write_files: bool = True


class WikiBatchExportPageResponse(BaseModel):
    page_id: UUID
    page_slug: str
    revision_no: int
    file_path: str
    memory_count: int
    source_count: int


class WikiBatchExportResponse(BaseModel):
    workspace_id: UUID
    pages: list[WikiBatchExportPageResponse]
