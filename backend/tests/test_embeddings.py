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
    SiliconFlowEmbeddingProvider,
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


def test_siliconflow_embedding_provider_maps_response(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    class FakeClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def post(self, url, *, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.services.embedding_service.httpx.Client", FakeClient)
    provider = SiliconFlowEmbeddingProvider(
        api_key="test-key",
        base_url="https://api.siliconflow.cn/v1/",
    )

    result = provider.embed(
        EmbeddingGenerateRequest(
            text="demo",
            provider="siliconflow",
            model="Qwen/Qwen3-Embedding-0.6B",
            dimension=1024,
        )
    )

    assert captured["url"] == "https://api.siliconflow.cn/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["dimensions"] == 1024
    assert result.provider == "siliconflow"
    assert result.model == "Qwen/Qwen3-Embedding-0.6B"
    assert result.dimension == 3
    assert result.embedding == [0.1, 0.2, 0.3]
