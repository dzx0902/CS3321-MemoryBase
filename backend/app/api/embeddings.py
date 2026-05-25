from __future__ import annotations

from fastapi import APIRouter, Depends

from ..models.embedding import EmbeddingGenerateRequest, EmbeddingGenerateResponse
from ..services.embedding_service import EmbeddingService
from .deps import get_embedding_service

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/generate", response_model=EmbeddingGenerateResponse)
def generate_embedding(
    payload: EmbeddingGenerateRequest,
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingGenerateResponse:
    return service.embed(payload)
