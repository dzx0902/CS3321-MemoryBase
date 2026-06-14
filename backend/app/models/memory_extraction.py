from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .memory import MemoryListResponse, MemorySummaryResponse

MemoryExtractionMethod = Literal["rule_based", "llm"]


class LlmAnalysisOptions(BaseModel):
    api_key: str | None = Field(default=None, min_length=1)
    base_url: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    provider: str | None = Field(default="openai-compatible", min_length=1)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=128, le=8000)

    @field_validator("api_key", "base_url", "model", "provider", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class MemoryExtractionFromChunksRequest(BaseModel):
    workspace_id: UUID
    chunk_ids: list[UUID] = Field(min_length=1)
    max_candidates: int = Field(default=10, ge=1, le=50)
    method: MemoryExtractionMethod = "rule_based"
    llm: LlmAnalysisOptions | None = None


class MemoryExtractionResponse(BaseModel):
    workspace_id: UUID
    method: MemoryExtractionMethod
    created_count: int
    candidates: list[MemorySummaryResponse]


class MemoryCandidateListResponse(MemoryListResponse):
    pass


class MemoryCandidateDecisionResponse(BaseModel):
    memory: MemorySummaryResponse
