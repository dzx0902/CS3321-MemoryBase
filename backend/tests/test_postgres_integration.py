from __future__ import annotations

from pathlib import Path

import psycopg

WORKSPACE_ID = "00000000-0000-0000-0000-000000000201"
AGENT_ID = "00000000-0000-0000-0000-000000000301"
PRIVATE_MEMORY_ID = "00000000-0000-0000-0000-000000000713"
MEMORY_ID = "00000000-0000-0000-0000-000000000711"
CONFLICT_ID = "00000000-0000-0000-0000-000000001001"
REVIEWER_USER_ID = "00000000-0000-0000-0000-000000000101"


def test_memory_revision_and_audit_end_to_end(integration_client, integration_db: str) -> None:
    response = integration_client.patch(
        f"/api/memories/{MEMORY_ID}",
        params={"workspace_id": WORKSPACE_ID},
        headers={
            "X-Actor-Type": "user",
            "X-Revision-Reason": "integration update",
        },
        json={
            "canonical_text": "团队放弃了校园食堂系统，并优先完成 MemoryBase 后端。",
            "summary": "项目方向与分工更新",
        },
    )

    assert response.status_code == 200
    assert response.json()["current_revision_no"] == 2

    detail_response = integration_client.get(
        f"/api/memories/{MEMORY_ID}", params={"workspace_id": WORKSPACE_ID}
    )
    assert detail_response.status_code == 200
    assert len(detail_response.json()["revisions"]) == 2
    assert detail_response.json()["revisions"][-1]["revision_no"] == 2

    audit_response = integration_client.get(
        "/api/audit",
        params={
            "workspace_id": WORKSPACE_ID,
            "target_type": "memory_item",
            "target_id": MEMORY_ID,
            "action_type": "memory.update",
        },
    )
    assert audit_response.status_code == 200
    assert audit_response.json()["total"] >= 1
    assert audit_response.json()["items"][0]["after_json"]["canonical_text"].endswith("后端。")


def test_recall_policy_visibility_and_log_end_to_end(
    integration_client, integration_db: str
) -> None:
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent (
                    agent_id, workspace_id, name, agent_type, status, owner_user_id
                )
                VALUES (
                    '00000000-0000-0000-0000-000000000302',
                    %(workspace_id)s,
                    'limited-retriever',
                    'retriever',
                    'active',
                    '00000000-0000-0000-0000-000000000104'
                )
                ON CONFLICT (agent_id) DO NOTHING
                """,
                {"workspace_id": WORKSPACE_ID},
            )
        conn.commit()

    hidden_response = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "agent_id": "00000000-0000-0000-0000-000000000302",
            "query_text": "Private budget",
        },
    )
    assert hidden_response.status_code == 200
    assert hidden_response.json()["result_count"] == 0

    policy_response = integration_client.post(
        "/api/policies",
        json={
            "workspace_id": WORKSPACE_ID,
            "principal_type": "agent",
            "principal_id": "00000000-0000-0000-0000-000000000302",
            "resource_type": "memory_item",
            "resource_scope": "private",
            "effect": "allow",
            "predicate_json": {"reason": "integration test"},
        },
    )
    assert policy_response.status_code == 201

    visible_response = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "agent_id": "00000000-0000-0000-0000-000000000302",
            "query_text": "Private budget",
        },
    )
    assert visible_response.status_code == 200
    assert visible_response.json()["result_count"] == 1
    assert visible_response.json()["memories"][0]["memory_id"] == PRIVATE_MEMORY_ID
    assert visible_response.json()["context_pack"]["top_memory_ids"] == [PRIVATE_MEMORY_ID]

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT result_count, top_memory_ids_json, context_pack_json
                FROM recall_log
                WHERE workspace_id = %(workspace_id)s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"workspace_id": WORKSPACE_ID},
            )
            row = cur.fetchone()
    assert row is not None
    assert row[0] == 1
    assert row[1] == [PRIVATE_MEMORY_ID]
    assert row[2]["top_memory_ids"] == [PRIVATE_MEMORY_ID]


def test_source_list_keyword_filter_end_to_end(integration_client, integration_db: str) -> None:
    response = integration_client.get(
        "/api/sources",
        params={
            "workspace_id": WORKSPACE_ID,
            "keyword": "Policy and Recall",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Discussion 04: Policy and Recall"


def test_chinese_demo_recall_finds_cafeteria_memory(
    integration_client, integration_db: str
) -> None:
    response = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "agent_id": AGENT_ID,
            "query_text": "为什么放弃校园食堂系统？",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["result_count"] >= 1
    memory_texts = [item["canonical_text"] for item in response.json()["memories"]]
    assert any("cafeteria system" in text for text in memory_texts)
    assert any(item["evidence"] for item in response.json()["memories"])


def test_memory_create_accepts_evidence_objects(integration_client, integration_db: str) -> None:
    response = integration_client.post(
        "/api/memories",
        json={
            "workspace_id": WORKSPACE_ID,
            "created_from_doc_id": "00000000-0000-0000-0000-000000000501",
            "memory_type": "decision",
            "canonical_text": "Evidence objects preserve role, weight, and note.",
            "summary": "Evidence object contract",
            "confidence": 0.91,
            "importance": 4,
            "access_level": "project",
            "evidence": [
                {
                    "chunk_id": "00000000-0000-0000-0000-000000000602",
                    "evidence_role": "context",
                    "weight": 0.7,
                    "note": "Custom evidence metadata.",
                }
            ],
        },
    )

    assert response.status_code == 201
    memory_id = response.json()["memory_id"]
    detail = integration_client.get(
        f"/api/memories/{memory_id}", params={"workspace_id": WORKSPACE_ID}
    )
    assert detail.status_code == 200
    evidence = detail.json()["evidence"][0]
    assert evidence["evidence_role"] == "context"
    assert evidence["weight"] == 0.7
    assert evidence["note"] == "Custom evidence metadata."


def test_memory_delete_sets_valid_to(integration_client, integration_db: str) -> None:
    response = integration_client.delete(
        f"/api/memories/{MEMORY_ID}", params={"workspace_id": WORKSPACE_ID}
    )
    assert response.status_code == 200

    detail = integration_client.get(
        f"/api/memories/{MEMORY_ID}", params={"workspace_id": WORKSPACE_ID}
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "archived"
    assert detail.json()["valid_to"] is not None


def test_conflict_timeline_and_audit_end_to_end(integration_client, integration_db: str) -> None:
    conflict_response = integration_client.get(
        "/api/conflicts", params={"workspace_id": WORKSPACE_ID}
    )
    assert conflict_response.status_code == 200
    assert conflict_response.json()["items"][0]["conflict_id"] == CONFLICT_ID

    patch_response = integration_client.patch(
        f"/api/conflicts/{CONFLICT_ID}",
        params={"workspace_id": WORKSPACE_ID},
        json={
            "status": "resolved",
            "resolution_note": "accepted MemoryBase direction",
            "actor_type": "user",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "resolved"

    timeline_create = integration_client.post(
        "/api/timeline",
        json={
            "workspace_id": WORKSPACE_ID,
            "title": "补齐 P0/P1 后端闭环",
            "event_type": "revision",
            "event_time": "2026-05-16T12:00:00Z",
            "description": "完成 recall、policy、conflict 和 wiki export 的后端收口。",
            "importance": 5,
            "memory_id": MEMORY_ID,
            "doc_id": "00000000-0000-0000-0000-000000000504",
        },
    )
    assert timeline_create.status_code == 201

    timeline_list = integration_client.get("/api/timeline", params={"workspace_id": WORKSPACE_ID})
    assert timeline_list.status_code == 200
    assert any(item["title"] == "补齐 P0/P1 后端闭环" for item in timeline_list.json()["items"])

    audit_response = integration_client.get(
        "/api/audit",
        params={
            "workspace_id": WORKSPACE_ID,
            "target_type": "conflict_record",
            "action_type": "conflict.update",
        },
    )
    assert audit_response.status_code == 200
    assert audit_response.json()["total"] >= 1


def test_wiki_export_writes_file_and_revision_end_to_end(
    integration_client, integration_db: str
) -> None:
    first = integration_client.post(
        "/api/wiki/export",
        json={
            "workspace_id": WORKSPACE_ID,
            "page_slug": "demo-report",
            "title": "Demo Report",
            "page_type": "report",
            "memory_ids": [MEMORY_ID],
            "write_files": True,
        },
    )
    assert first.status_code == 200
    assert first.json()["revision_no"] == 1
    output_path = Path(first.json()["output_path"])
    assert output_path.exists()
    contents = output_path.read_text(encoding="utf-8")
    assert "workspace_id:" in contents
    assert f"data/markdown_wiki/{WORKSPACE_ID}/demo-report.md" in first.json()["output_path"]
    assert "memory_ids:" in contents
    assert "source_doc_ids:" in contents
    assert first.json()["frontmatter_json"]["memory_ids"] == [MEMORY_ID]

    second = integration_client.post(
        "/api/wiki/export",
        json={
            "workspace_id": WORKSPACE_ID,
            "page_slug": "demo-report",
            "title": "Demo Report",
            "page_type": "report",
            "memory_ids": [MEMORY_ID],
        },
    )
    assert second.status_code == 200
    assert second.json()["revision_no"] == 2


def test_forget_request_approval_forgets_memory_and_excludes_recall(
    integration_client, integration_db: str
) -> None:
    before_recall = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "Recall should return memory items",
            "limit": 5,
        },
    )
    assert before_recall.status_code == 200
    assert any(item["memory_id"] == MEMORY_ID for item in before_recall.json()["memories"])

    create_response = integration_client.post(
        "/api/forget-requests",
        json={
            "workspace_id": WORKSPACE_ID,
            "target_type": "memory_item",
            "target_id": MEMORY_ID,
            "requester_user_id": REVIEWER_USER_ID,
            "reason": "Exercise the forget governance workflow.",
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["status"] == "pending"
    request_id = create_response.json()["request_id"]

    approve_response = integration_client.patch(
        f"/api/forget-requests/{request_id}",
        params={"workspace_id": WORKSPACE_ID},
        json={
            "status": "approved",
            "reviewed_by_user_id": REVIEWER_USER_ID,
        },
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["resolved_at"] is not None

    memory_detail = integration_client.get(
        f"/api/memories/{MEMORY_ID}", params={"workspace_id": WORKSPACE_ID}
    )
    assert memory_detail.status_code == 200
    assert memory_detail.json()["status"] == "forgotten"
    assert memory_detail.json()["valid_to"] is not None

    after_recall = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "Recall should return memory items",
            "limit": 5,
        },
    )
    assert after_recall.status_code == 200
    assert all(item["memory_id"] != MEMORY_ID for item in after_recall.json()["memories"])

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM audit_log
                WHERE workspace_id = %(workspace_id)s
                  AND (
                    (action_type = 'forget_request.update' AND target_id = %(request_id)s)
                    OR (action_type = 'memory.forget' AND target_id = %(memory_id)s)
                  )
                """,
                {
                    "workspace_id": WORKSPACE_ID,
                    "request_id": request_id,
                    "memory_id": MEMORY_ID,
                },
            )
            audit_count = cur.fetchone()[0]
    assert audit_count >= 2
