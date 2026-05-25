from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from ..models.embedding import (
    ChunkEmbeddingRecord,
    EmbeddingBackfillRequest,
    EmbeddingBackfillResponse,
    EmbeddingGenerateRequest,
    EmbeddingGenerateResponse,
    MemoryEmbeddingRecord,
)
from ..services.embedding_service import EmbeddingService
from .deps import get_embedding_service

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/generate", response_model=EmbeddingGenerateResponse)
def generate_embedding(
    payload: EmbeddingGenerateRequest,
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingGenerateResponse:
    return service.embed(payload)


@router.post("/memories/{memory_id}", response_model=MemoryEmbeddingRecord)
def embed_memory(
    memory_id: UUID,
    provider: str = "local",
    model: str = "hashing-v1",
    dimension: int = 128,
    service: EmbeddingService = Depends(get_embedding_service),
) -> MemoryEmbeddingRecord:
    return service.embed_memory(
        memory_id=memory_id,
        provider_name=provider,
        model=model,
        dimension=dimension,
    )


@router.post("/chunks/{chunk_id}", response_model=ChunkEmbeddingRecord)
def embed_chunk(
    chunk_id: UUID,
    provider: str = "local",
    model: str = "hashing-v1",
    dimension: int = 128,
    service: EmbeddingService = Depends(get_embedding_service),
) -> ChunkEmbeddingRecord:
    return service.embed_chunk(
        chunk_id=chunk_id,
        provider_name=provider,
        model=model,
        dimension=dimension,
    )


@router.post("/backfill", response_model=EmbeddingBackfillResponse)
def backfill_embeddings(
    payload: EmbeddingBackfillRequest,
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingBackfillResponse:
    return service.backfill(payload)
