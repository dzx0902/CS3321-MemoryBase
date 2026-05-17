from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.api.deps import get_recall_service, get_wiki_service
from app.main import create_app
from app.models.recall import RecallRequest, RecallResponse
from app.models.wiki import WikiExportRequest, WikiExportResponse
from fastapi.testclient import TestClient


class FakeRecallService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.memory_id = uuid4()
        self.chunk_id = uuid4()
        self.doc_id = uuid4()

    def execute(self, payload: RecallRequest) -> RecallResponse:
        return RecallResponse(
            recall_id=uuid4(),
            workspace_id=payload.workspace_id,
            query_text=payload.query_text,
            result_count=1,
            memories=[
                {
                    "memory_id": self.memory_id,
                    "memory_type": "decision",
                    "canonical_text": "我们放弃校园食堂系统，转做 MemoryBase。",
                    "summary": "项目方向变更",
                    "confidence": 0.88,
                    "importance": 5,
                    "status": "active",
                    "access_level": "project",
                    "score": 1.42,
                    "evidence": [
                        {
                            "chunk_id": self.chunk_id,
                            "doc_id": self.doc_id,
                            "source_title": "meeting_01",
                            "chunk_no": 1,
                            "chunk_text": "团队决定从校园食堂系统切换到 MemoryBase。",
                            "start_line": 10,
                            "end_line": 12,
                            "evidence_role": "supports",
                            "weight": 1.0,
                        }
                    ],
                }
            ],
            context_pack={
                "query_text": payload.query_text,
                "filters": {
                    "agent_id": None,
                    "access_level": None,
                    "memory_type": None,
                    "status": "active",
                },
                "top_memory_ids": [str(self.memory_id)],
                "matched_source_ids": [str(self.doc_id)],
            },
            created_at=datetime(2026, 5, 16, tzinfo=timezone.utc),
        )


class FakeWikiService:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.page_id = uuid4()

    def export_page(self, payload: WikiExportRequest) -> WikiExportResponse:
        return WikiExportResponse(
            page_id=self.page_id,
            workspace_id=payload.workspace_id,
            page_slug=payload.page_slug,
            title=payload.title,
            page_type=payload.page_type,
            revision_no=1,
            body_markdown=f"# {payload.title}\n\nGenerated wiki content.\n",
            needs_rebuild=False,
            output_path="data/markdown_wiki/demo-report.md",
            frontmatter_json={
                "workspace_id": str(payload.workspace_id),
                "page_slug": payload.page_slug,
                "generated_at": "2026-05-16T00:00:00Z",
                "source_ids": [str(uuid4())],
            },
            source_doc_ids=[uuid4()],
            created_at=datetime(2026, 5, 16, tzinfo=timezone.utc),
        )


def build_client() -> tuple[TestClient, FakeRecallService, FakeWikiService]:
    app = create_app()
    fake_recall = FakeRecallService()
    fake_wiki = FakeWikiService()
    app.dependency_overrides[get_recall_service] = lambda: fake_recall
    app.dependency_overrides[get_wiki_service] = lambda: fake_wiki
    return TestClient(app), fake_recall, fake_wiki


def test_recall_returns_memory_and_evidence() -> None:
    client, fake_recall, _ = build_client()

    response = client.post(
        "/api/recall",
        json={
            "workspace_id": str(fake_recall.workspace_id),
            "query_text": "为什么放弃校园食堂系统？",
        },
    )

    assert response.status_code == 200
    assert response.json()["result_count"] == 1
    assert response.json()["memories"][0]["evidence"][0]["source_title"] == "meeting_01"
    assert response.json()["memories"][0]["evidence"][0]["start_line"] == 10


def test_wiki_export_returns_markdown_page() -> None:
    client, _, fake_wiki = build_client()

    response = client.post(
        "/api/wiki/export",
        json={
            "workspace_id": str(fake_wiki.workspace_id),
            "page_slug": "demo-report",
            "title": "Demo Report",
            "page_type": "report",
        },
    )

    assert response.status_code == 200
    assert response.json()["page_slug"] == "demo-report"
    assert response.json()["body_markdown"].startswith("# Demo Report")
    assert response.json()["output_path"].endswith("demo-report.md")
