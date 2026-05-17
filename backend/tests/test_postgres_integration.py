from __future__ import annotations

from pathlib import Path

import psycopg

WORKSPACE_ID = "00000000-0000-0000-0000-000000000201"
AGENT_ID = "00000000-0000-0000-0000-000000000301"
PRIVATE_MEMORY_ID = "00000000-0000-0000-0000-000000000713"
MEMORY_ID = "00000000-0000-0000-0000-000000000711"
CONFLICT_ID = "00000000-0000-0000-0000-000000001001"


def test_memory_revision_and_audit_end_to_end(integration_client, integration_db: str) -> None:
    response = integration_client.patch(
        f"/api/memories/{MEMORY_ID}",
        json={
            "canonical_text": "团队放弃了校园食堂系统，并优先完成 MemoryBase 后端。",
            "summary": "项目方向与分工更新",
            "revision_reason": "integration update",
            "editor_type": "user",
        },
    )

    assert response.status_code == 200
    assert response.json()["current_revision_no"] == 2

    detail_response = integration_client.get(f"/api/memories/{MEMORY_ID}")
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


def test_conflict_timeline_and_audit_end_to_end(integration_client, integration_db: str) -> None:
    conflict_response = integration_client.get(
        "/api/conflicts", params={"workspace_id": WORKSPACE_ID}
    )
    assert conflict_response.status_code == 200
    assert conflict_response.json()[0]["conflict_id"] == CONFLICT_ID

    patch_response = integration_client.patch(
        f"/api/conflicts/{CONFLICT_ID}",
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
    assert any(item["title"] == "补齐 P0/P1 后端闭环" for item in timeline_list.json())

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
        },
    )
    assert first.status_code == 200
    assert first.json()["revision_no"] == 1
    output_path = Path(first.json()["output_path"])
    assert output_path.exists()
    contents = output_path.read_text(encoding="utf-8")
    assert "workspace_id:" in contents
    assert "source_ids:" in contents

    second = integration_client.post(
        "/api/wiki/export",
        json={
            "workspace_id": WORKSPACE_ID,
            "page_slug": "demo-report",
            "title": "Demo Report",
            "page_type": "report",
        },
    )
    assert second.status_code == 200
    assert second.json()["revision_no"] == 2
