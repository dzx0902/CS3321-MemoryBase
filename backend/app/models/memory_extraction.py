from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from .memory import MemoryListResponse, MemorySummaryResponse


class MemoryExtractionFromChunksRequest(BaseModel):
    workspace_id: UUID
    chunk_ids: list[UUID] = Field(min_length=1)
    max_candidates: int = Field(default=10, ge=1, le=50)


class MemoryExtractionResponse(BaseModel):
    workspace_id: UUID
    created_count: int
    candidates: list[MemorySummaryResponse]


class MemoryCandidateListResponse(MemoryListResponse):
    pass


class MemoryCandidateDecisionResponse(BaseModel):
    memory: MemorySummaryResponse
