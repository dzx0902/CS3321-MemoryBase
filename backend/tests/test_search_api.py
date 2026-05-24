from __future__ import annotations

from uuid import uuid4

from app.api.deps import get_search_service
from app.main import create_app
from app.models.search import SearchRequest, SearchResponse
from fastapi.testclient import TestClient


class FakeSearchService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.chunk_id = uuid4()
        self.doc_id = uuid4()
        self.last_payload: SearchRequest | None = None

    def execute(self, payload: SearchRequest) -> SearchResponse:
        self.last_payload = payload
        return SearchResponse(
            workspace_id=payload.workspace_id,
            query_text=payload.query_text,
            tokenized_query="校园 食堂 cafeteria",
            result_count=1,
            items=[
                {
                    "result_type": "chunk",
                    "result_id": self.chunk_id,
                    "doc_id": self.doc_id,
                    "source_path": "data/raw_sources/demo_workspace/discussion_01_project_pivot.md",
                    "source_title": "Discussion 01: Project Pivot",
                    "start_line": 8,
                    "end_line": 12,
                    "snippet": "The cafeteria system was too CRUD-heavy.",
                    "score": 0.031,
                    "strategies": ["chunk_fts", "trigram_fuzzy"],
                }
            ],
        )


def build_client() -> tuple[TestClient, FakeSearchService]:
    app = create_app()
    fake_search = FakeSearchService()
    app.dependency_overrides[get_search_service] = lambda: fake_search
    return TestClient(app), fake_search


def test_search_returns_structured_items_without_show_lines() -> None:
    client, fake_search = build_client()

    response = client.post(
        "/api/search",
        json={
            "workspace_id": str(fake_search.workspace_id),
            "query_text": "为什么放弃校园食堂方向",
            "scope": "all",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tokenized_query"] == "校园 食堂 cafeteria"
    assert payload["items"][0]["source_path"].endswith("discussion_01_project_pivot.md")
    assert payload["items"][0]["strategies"] == ["chunk_fts", "trigram_fuzzy"]
    assert fake_search.last_payload is not None
    assert fake_search.last_payload.scope == "all"


def test_search_rejects_presentation_only_show_lines_field() -> None:
    client, fake_search = build_client()

    response = client.post(
        "/api/search",
        json={
            "workspace_id": str(fake_search.workspace_id),
            "query_text": "cafeteria",
            "show_lines": True,
        },
    )

    assert response.status_code == 422
