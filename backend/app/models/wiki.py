from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from .common import PageResponse

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


class WikiRevisionResponse(BaseModel):
    page_id: UUID
    revision_no: int
    frontmatter_json: dict[str, Any]
    body_markdown: str
    generated_by: str | None = None
    created_at: datetime


class WikiPageSummaryResponse(BaseModel):
    page_id: UUID
    workspace_id: UUID
    page_slug: str
    title: str
    page_type: WikiPageType
    current_revision_no: int
    needs_rebuild: bool
    status: str
    generated_from_memory_id: UUID | None = None
    generated_from_scene_id: UUID | None = None
    memory_count: int = 0
    source_count: int = 0
    latest_revision_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WikiPageDetailResponse(WikiPageSummaryResponse):
    latest_revision: WikiRevisionResponse | None = None
    memory_ids: list[UUID] = Field(default_factory=list)
    source_doc_ids: list[UUID] = Field(default_factory=list)


class WikiPageListResponse(PageResponse[WikiPageSummaryResponse]):
    pass


class WikiRevisionListResponse(PageResponse[WikiRevisionResponse]):
    pass
