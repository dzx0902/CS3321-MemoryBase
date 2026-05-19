from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.api.deps import get_source_service
from app.main import create_app
from app.models.source import (
    SourceCreateRequest,
    SourceDetailResponse,
    SourceImportResponse,
    SourceListResponse,
    SourceSummaryResponse,
)
from app.services.source_service import SourceNotFoundError
from fastapi.testclient import TestClient


class FakeSourceService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.doc_id = uuid4()
        self.source = SourceDetailResponse(
            doc_id=self.doc_id,
            workspace_id=self.workspace_id,
            title="discussion_01",
            doc_type="markdown",
            source_path="data/raw_sources/demo_workspace/discussion_01.md",
            imported_at=datetime(2026, 5, 16, tzinfo=timezone.utc),
            chunk_count=2,
            session_id=None,
            checksum="fake-checksum",
            raw_text="line1\nline2\nline3",
            chunks=[
                {
                    "chunk_id": uuid4(),
                    "chunk_no": 1,
                    "chunk_text": "line1\nline2",
                    "start_line": 1,
                    "end_line": 2,
                    "token_count": 2,
                },
                {
                    "chunk_id": uuid4(),
                    "chunk_no": 2,
                    "chunk_text": "line3",
                    "start_line": 3,
                    "end_line": 3,
                    "token_count": 1,
                },
            ],
        )

    def import_source(self, payload: SourceCreateRequest) -> SourceImportResponse:
        self.source = self.source.model_copy(
            update={"workspace_id": payload.workspace_id, "title": payload.title}
        )
        return SourceImportResponse(doc_id=self.doc_id, chunk_count=self.source.chunk_count)

    def list_sources(
        self,
        *,
        workspace_id: UUID | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> SourceListResponse:
        if workspace_id is not None and workspace_id != self.workspace_id:
            return SourceListResponse(items=[], page=page, page_size=page_size, total=0)
        if keyword is not None and keyword not in self.source.title:
            source_path = self.source.source_path or ""
            if keyword not in source_path:
                return SourceListResponse(items=[], page=page, page_size=page_size, total=0)
        item = SourceSummaryResponse(
            doc_id=self.source.doc_id,
            workspace_id=self.source.workspace_id,
            title=self.source.title,
            doc_type=self.source.doc_type,
            source_path=self.source.source_path,
            imported_at=self.source.imported_at,
            chunk_count=self.source.chunk_count,
        )
        return SourceListResponse(items=[item], page=page, page_size=page_size, total=1)

    def get_source(self, doc_id: UUID, workspace_id: UUID) -> SourceDetailResponse:
        if doc_id != self.doc_id or workspace_id != self.workspace_id:
            raise SourceNotFoundError(f"source {doc_id} not found")
        return deepcopy(self.source)


def build_client() -> tuple[TestClient, FakeSourceService]:
    app = create_app()
    fake_service = FakeSourceService()
    app.dependency_overrides[get_source_service] = lambda: fake_service
    return TestClient(app), fake_service


def test_create_source_returns_import_summary() -> None:
    client, fake_service = build_client()

    response = client.post(
        "/api/sources",
        json={
            "workspace_id": str(fake_service.workspace_id),
            "title": "meeting_notes",
            "doc_type": "markdown",
            "raw_text": "# Notes\nMemoryBase backend plan",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "doc_id": str(fake_service.doc_id),
        "chunk_count": 2,
    }


def test_list_sources_supports_workspace_filter() -> None:
    client, fake_service = build_client()

    response = client.get("/api/sources", params={"workspace_id": str(fake_service.workspace_id)})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "discussion_01"


def test_list_sources_supports_keyword_filter() -> None:
    client, fake_service = build_client()

    matched = client.get(
        "/api/sources",
        params={"workspace_id": str(fake_service.workspace_id), "keyword": "discussion_01"},
    )
    unmatched = client.get(
        "/api/sources",
        params={"workspace_id": str(fake_service.workspace_id), "keyword": "not-present"},
    )

    assert matched.status_code == 200
    assert matched.json()["total"] == 1
    assert unmatched.status_code == 200
    assert unmatched.json()["total"] == 0


def test_get_source_returns_chunks() -> None:
    client, fake_service = build_client()

    response = client.get(
        f"/api/sources/{fake_service.doc_id}",
        params={"workspace_id": str(fake_service.workspace_id)},
    )

    assert response.status_code == 200
    assert response.json()["doc_id"] == str(fake_service.doc_id)
    assert len(response.json()["chunks"]) == 2


def test_get_source_returns_404_for_unknown_doc() -> None:
    client, _ = build_client()

    response = client.get(f"/api/sources/{uuid4()}", params={"workspace_id": str(uuid4())})

    assert response.status_code == 404
