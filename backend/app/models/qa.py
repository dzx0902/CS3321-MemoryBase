from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .recall import RetrievalMode


class AnswerRequest(BaseModel):
    workspace_id: UUID
    query_text: str = Field(min_length=1)
    agent_id: UUID | None = None
    memory_type: str | None = None
    access_level: str | None = None
    status: str | None = "active"
    retrieval_mode: RetrievalMode = "hybrid"
    limit: int = Field(default=10, ge=1, le=50)
    max_context_tokens: int = Field(default=3000, ge=100, le=16000)
    max_answer_tokens: int | None = Field(default=None, ge=1, le=4096)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class AnswerResponse(BaseModel):
    answer: str
    provider: str
    model: str
    recall_id: UUID | None = None
    result_count: int
    citation_map: dict[str, Any]
    token_count: int
    token_budget: int
    selected_memories: list[dict[str, Any]]
    supporting_evidence: list[dict[str, Any]]
    created_at: datetime | None = None
