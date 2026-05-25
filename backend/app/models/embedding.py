from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EmbeddingGenerateRequest(BaseModel):
    text: str = Field(min_length=1)
    provider: str = "local"
    model: str = "hashing-v1"
    dimension: int = Field(default=128, ge=8, le=4096)


class EmbeddingGenerateResponse(BaseModel):
    provider: str
    model: str
    dimension: int
    embedding: list[float]
    text_hash: str


class EmbeddingBackfillRequest(BaseModel):
    workspace_id: UUID
    target: Literal["memories", "chunks", "all"] = "all"
    provider: str = "local"
    model: str = "hashing-v1"
    dimension: int = Field(default=128, ge=8, le=4096)
    limit: int = Field(default=100, ge=1, le=1000)


class EmbeddingBackfillResponse(BaseModel):
    workspace_id: UUID
    target: str
    memory_count: int = 0
    chunk_count: int = 0


class MemoryEmbeddingRecord(BaseModel):
    embedding_id: UUID
    memory_id: UUID
    workspace_id: UUID
    provider: str
    model: str
    dimension: int
    embedding_text_hash: str
    created_at: datetime


class ChunkEmbeddingRecord(BaseModel):
    embedding_id: UUID
    chunk_id: UUID
    doc_id: UUID
    workspace_id: UUID
    provider: str
    model: str
    dimension: int
    embedding_text_hash: str
    created_at: datetime
