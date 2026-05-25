from __future__ import annotations

from app.main import app
from app.models.embedding import EmbeddingGenerateRequest
from app.services.embedding_service import LocalHashingEmbeddingProvider, cosine_similarity
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
