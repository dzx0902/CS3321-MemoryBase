from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.recall import RecallResponse
from app.services.context_pack_service import format_context_pack


def build_recall_response(*, repeated_text: str = "") -> RecallResponse:
    workspace_id = uuid4()
    memory_id = uuid4()
    doc_id = uuid4()
    return RecallResponse(
        recall_id=uuid4(),
        workspace_id=workspace_id,
        query_text="为什么放弃校园食堂方向",
        result_count=1,
        memories=[
            {
                "memory_id": memory_id,
                "memory_type": "decision",
                "canonical_text": (
                    "The team abandoned the campus cafeteria system because it was too "
                    f"CRUD-heavy. {repeated_text}"
                ),
                "summary": "Project topic decision.",
                "confidence": 0.95,
                "importance": 5,
                "status": "active",
                "access_level": "project",
                "score": 1.3,
                "evidence": [
                    {
                        "chunk_id": uuid4(),
                        "doc_id": doc_id,
                        "source_title": "Discussion 01: Project Pivot",
                        "chunk_no": 2,
                        "chunk_text": (
                            "The cafeteria idea was abandoned because it did not show "
                            f"enough database depth. {repeated_text}"
                        ),
                        "start_line": 10,
                        "end_line": 12,
                        "evidence_role": "supports",
                        "weight": 1.0,
                    }
                ],
            }
        ],
        context_pack={
            "query_text": "为什么放弃校园食堂方向",
            "filters": {"status": "active"},
            "top_memory_ids": [str(memory_id)],
            "matched_source_ids": [str(doc_id)],
        },
        created_at=datetime(2026, 5, 22, tzinfo=timezone.utc),
    )


def test_format_context_pack_renders_agent_ready_markdown_with_citations() -> None:
    result = format_context_pack(build_recall_response(), max_tokens=800)

    assert "# MemoryBase Context" in result.markdown
    assert "## Relevant Memories" in result.markdown
    assert "## Evidence" in result.markdown
    assert "## Known Conflicts / Risks" in result.markdown
    assert "## Do Not Assume" in result.markdown
    assert "[M1]" in result.markdown
    assert "[E1]" in result.markdown
    assert result.citation_map["memories"]["M1"]["memory_type"] == "decision"
    assert result.citation_map["evidence"]["E1"]["source_title"] == "Discussion 01: Project Pivot"


def test_format_context_pack_respects_token_budget() -> None:
    result = format_context_pack(
        build_recall_response(repeated_text="long text " * 400),
        max_tokens=120,
    )

    assert result.token_count <= 120
    assert "[Truncated to fit token budget]" in result.markdown
