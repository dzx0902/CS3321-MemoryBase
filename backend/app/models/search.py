from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SearchScope = Literal["all", "chunks", "memories", "sources"]
SearchResultType = Literal["chunk", "memory", "source"]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    agent_id: UUID | None = None
    query_text: str = Field(min_length=1)
    scope: SearchScope = "all"
    limit: int = Field(default=10, ge=1, le=50)


class SearchItemResponse(BaseModel):
    result_type: SearchResultType
    result_id: UUID
    doc_id: UUID | None = None
    source_path: str | None = None
    source_title: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    snippet: str
    score: float
    strategies: list[str]


class SearchResponse(BaseModel):
    workspace_id: UUID
    query_text: str
    tokenized_query: str
    result_count: int
    items: list[SearchItemResponse]
