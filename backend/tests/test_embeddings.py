from __future__ import annotations

from app.main import app
from app.models.embedding import (
    EmbeddingBackfillRequest,
    EmbeddingBackfillResponse,
    EmbeddingGenerateRequest,
)
from app.services.embedding_service import (
    EmbeddingService,
    LocalHashingEmbeddingProvider,
    cosine_similarity,
)
from fastapi.testclient import TestClient


def test_local_hashing_embedding_is_deterministic_and_normalized() -> None:
    provider = LocalHashingEmbeddingProvider()
    payload = EmbeddingGenerateRequest(text="MemoryBase remembers project decisions.")

    first = provider.embed(payload)
    second = provider.embed(payload)

    assert first.embedding == second.embedding
    assert first.text_hash == second.text_hash
    assert len(first.embedding) == payload.dimension
    assert abs(cosine_similarity(first.embedding, first.embedding) - 1.0) < 0.000001


def test_embedding_api_generates_vector() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/embeddings/generate",
        json={"text": "Remember that PostgreSQL is the primary database.", "dimension": 32},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "local"
    assert payload["model"] == "hashing-v1"
    assert payload["dimension"] == 32
    assert len(payload["embedding"]) == 32
    assert payload["text_hash"]


def test_embedding_service_delegates_backfill_to_repository() -> None:
    class FakeRepository:
        def backfill(self, payload, provider):
            embedded = provider.embed(
                EmbeddingGenerateRequest(text="demo", dimension=payload.dimension)
            )
            assert len(embedded.embedding) == payload.dimension
            return EmbeddingBackfillResponse(
                workspace_id=payload.workspace_id,
                target=payload.target,
                memory_count=1,
                chunk_count=2,
            )

    service = EmbeddingService(
        provider=LocalHashingEmbeddingProvider(),
        repository=FakeRepository(),
    )
    payload = EmbeddingBackfillRequest(
        workspace_id="00000000-0000-0000-0000-000000000001",
        target="all",
        dimension=16,
    )

    result = service.backfill(payload)

    assert result.memory_count == 1
    assert result.chunk_count == 2
