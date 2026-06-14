from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.api.deps import get_memory_extraction_service
from app.main import create_app
from app.models.memory import ActorContext, MemorySummaryResponse
from fastapi.testclient import TestClient


class FakeMemoryExtractionService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.chunk_id = uuid4()
        self.payload = None
        self.actor = None

    def extract_from_chunks(self, payload, actor: ActorContext):
        self.payload = payload
        self.actor = actor
        now = datetime(2026, 6, 14, tzinfo=timezone.utc)
        return [
            MemorySummaryResponse(
                memory_id=uuid4(),
                workspace_id=payload.workspace_id,
                created_from_doc_id=uuid4(),
                memory_type="policy",
                canonical_text="Private notes must stay hidden from project-only agents.",
                summary="Private notes visibility",
                confidence=0.88,
                importance=4,
                status="candidate",
                access_level="project",
                current_revision_no=1,
                created_at=now,
                updated_at=now,
                evidence_count=1,
            )
        ]

    def list_candidates(
        self,
        *,
        workspace_id: UUID | None,
        memory_type: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ):
        raise AssertionError("not used")


def test_extract_from_chunks_accepts_llm_options() -> None:
    app = create_app()
    fake_service = FakeMemoryExtractionService()
    app.dependency_overrides[get_memory_extraction_service] = lambda: fake_service
    client = TestClient(app)

    response = client.post(
        "/api/memory-extraction/from-chunks",
        json={
            "workspace_id": str(fake_service.workspace_id),
            "chunk_ids": [str(fake_service.chunk_id)],
            "max_candidates": 3,
            "method": "llm",
            "llm": {
                "api_key": "test-key",
                "base_url": "https://api.example.com/v1",
                "model": "analysis-model",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["method"] == "llm"
    assert payload["created_count"] == 1
    assert payload["candidates"][0]["memory_type"] == "policy"
    assert fake_service.payload.method == "llm"
    assert fake_service.payload.llm.api_key == "test-key"
    assert fake_service.actor.revision_reason == "llm memory extraction"
