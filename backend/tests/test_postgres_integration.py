from __future__ import annotations

from pathlib import Path

import psycopg
import pytest

WORKSPACE_ID = "00000000-0000-0000-0000-000000000201"
AGENT_ID = "00000000-0000-0000-0000-000000000301"
PRIVATE_MEMORY_ID = "00000000-0000-0000-0000-000000000713"
MEMORY_ID = "00000000-0000-0000-0000-000000000711"
CONFLICT_ID = "00000000-0000-0000-0000-000000001001"
REVIEWER_USER_ID = "00000000-0000-0000-0000-000000000101"
SEMANTIC_MEMORY_ID = "00000000-0000-0000-0000-000000000701"
SOURCE_DOC_ID = "00000000-0000-0000-0000-000000000501"
WIKI_PAGE_ID = "00000000-0000-0000-0000-000000001301"
ENTITY_ID = "00000000-0000-0000-0000-000000000801"


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

    policy_list = integration_client.get(
        "/api/policies",
        params={
            "workspace_id": WORKSPACE_ID,
            "principal_type": "agent",
            "principal_id": "00000000-0000-0000-0000-000000000302",
            "resource_type": "memory_item",
            "effect": "allow",
        },
    )
    assert policy_list.status_code == 200
    assert policy_list.json()["total"] == 1

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


def test_memory_detail_includes_entities_and_scenes(
    integration_client, integration_db: str
) -> None:
    response = integration_client.get(
        f"/api/memories/{SEMANTIC_MEMORY_ID}", params={"workspace_id": WORKSPACE_ID}
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(
        entity["canonical_name"] == "Campus Cafeteria System"
        for entity in payload["entities"]
    )
    assert any(scene["scene_slug"] == "topic-decision" for scene in payload["scenes"])


def test_semantic_tables_and_conflicts_enforce_integrity(integration_db: str) -> None:
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workspace(workspace_id, slug, name, scope_type)
                VALUES (
                  '00000000-0000-0000-0000-000000009201',
                  'other-semantic',
                  'Other Workspace',
                  'project'
                )
                """
            )
            cur.execute(
                """
                INSERT INTO entity(entity_id, workspace_id, canonical_name, entity_type)
                VALUES (
                  '00000000-0000-0000-0000-000000009801',
                  '00000000-0000-0000-0000-000000009201',
                  'Other Workspace Entity',
                  'concept'
                )
                """
            )
        conn.commit()

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with psycopg.connect(integration_db) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memory_entity(memory_id, entity_id, workspace_id, relation_role)
                    VALUES (
                      '00000000-0000-0000-0000-000000000701',
                      '00000000-0000-0000-0000-000000009801',
                      '00000000-0000-0000-0000-000000000201',
                      'about'
                    )
                    """
                )

    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(integration_db) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conflict_record(
                      workspace_id, left_memory_id, right_memory_id, conflict_type, status
                    )
                    VALUES (
                      '00000000-0000-0000-0000-000000000201',
                      '00000000-0000-0000-0000-000000000720',
                      '00000000-0000-0000-0000-000000000712',
                      'uncertain',
                      'open'
                    )
                    """
                )


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


def test_memory_list_defaults_to_active_and_requires_status_all_for_archived(
    integration_client, integration_db: str
) -> None:
    delete_response = integration_client.delete(
        f"/api/memories/{MEMORY_ID}", params={"workspace_id": WORKSPACE_ID}
    )
    assert delete_response.status_code == 200

    default_response = integration_client.get(
        "/api/memories",
        params={"workspace_id": WORKSPACE_ID, "keyword": "Recall should return memory items"},
    )
    assert default_response.status_code == 200
    assert all(item["memory_id"] != MEMORY_ID for item in default_response.json()["items"])

    archived_response = integration_client.get(
        "/api/memories",
        params={
            "workspace_id": WORKSPACE_ID,
            "keyword": "Recall should return memory items",
            "status": "archived",
        },
    )
    assert archived_response.status_code == 200
    assert any(item["memory_id"] == MEMORY_ID for item in archived_response.json()["items"])

    all_response = integration_client.get(
        "/api/memories",
        params={
            "workspace_id": WORKSPACE_ID,
            "keyword": "Recall should return memory items",
            "status": "all",
        },
    )
    assert all_response.status_code == 200
    assert any(item["memory_id"] == MEMORY_ID for item in all_response.json()["items"])


def test_recall_without_agent_id_does_not_return_private_memory(
    integration_client, integration_db: str
) -> None:
    response = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "Private budget",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["result_count"] == 0


def test_recall_as_of_filters_validity_and_records_filter_json(
    integration_client, integration_db: str
) -> None:
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE memory_item
                SET valid_from = '2026-03-01 00:00:00+00',
                    valid_to = '2026-04-01 00:00:00+00'
                WHERE memory_id = %(memory_id)s
                  AND workspace_id = %(workspace_id)s
                """,
                {"memory_id": MEMORY_ID, "workspace_id": WORKSPACE_ID},
            )
        conn.commit()

    in_range = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "Recall should return memory items",
            "as_of": "2026-03-15T00:00:00Z",
            "limit": 5,
        },
    )
    assert in_range.status_code == 200
    assert any(item["memory_id"] == MEMORY_ID for item in in_range.json()["memories"])

    after_range = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "Recall should return memory items",
            "as_of": "2026-05-01T00:00:00Z",
            "limit": 5,
        },
    )
    assert after_range.status_code == 200
    assert all(item["memory_id"] != MEMORY_ID for item in after_range.json()["memories"])

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT filter_json
                FROM recall_log
                WHERE workspace_id = %(workspace_id)s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"workspace_id": WORKSPACE_ID},
            )
            row = cur.fetchone()
    assert row is not None
    assert row[0]["as_of"] == "2026-05-01T00:00:00+00:00"


def test_agent_visible_memories_endpoint_filters_private(
    integration_client, integration_db: str
) -> None:
    response = integration_client.get(
        f"/api/agents/{AGENT_ID}/visible-memories",
        params={"workspace_id": WORKSPACE_ID},
    )

    assert response.status_code == 200
    visible_ids = {item["memory_id"] for item in response.json()["items"]}
    assert "00000000-0000-0000-0000-000000000701" in visible_ids
    assert PRIVATE_MEMORY_ID not in visible_ids


def test_conflict_create_marks_memory_conflicted_and_resolve_restores_active(
    integration_client, integration_db: str
) -> None:
    create_response = integration_client.post(
        "/api/conflicts",
        json={
            "workspace_id": WORKSPACE_ID,
            "left_memory_id": "00000000-0000-0000-0000-000000000701",
            "right_memory_id": "00000000-0000-0000-0000-000000000702",
            "conflict_type": "contradiction",
            "resolution_note": "Integration test conflict.",
            "actor_type": "user",
            "actor_id": REVIEWER_USER_ID,
        },
    )
    assert create_response.status_code == 201
    conflict_id = create_response.json()["conflict_id"]

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT memory_id, status
                FROM memory_item
                WHERE memory_id IN (
                  '00000000-0000-0000-0000-000000000701',
                  '00000000-0000-0000-0000-000000000702'
                )
                ORDER BY memory_id
                """
            )
            statuses = {str(row[0]): row[1] for row in cur.fetchall()}

    assert set(statuses.values()) == {"conflicted"}

    duplicate_response = integration_client.post(
        "/api/conflicts",
        json={
            "workspace_id": WORKSPACE_ID,
            "left_memory_id": "00000000-0000-0000-0000-000000000702",
            "right_memory_id": "00000000-0000-0000-0000-000000000701",
            "conflict_type": "contradiction",
        },
    )
    assert duplicate_response.status_code == 409

    resolve_response = integration_client.patch(
        f"/api/conflicts/{conflict_id}",
        params={"workspace_id": WORKSPACE_ID},
        json={
            "status": "resolved",
            "resolution_note": "Resolved integration conflict.",
            "actor_type": "user",
            "actor_id": REVIEWER_USER_ID,
        },
    )
    assert resolve_response.status_code == 200

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT memory_id, status
                FROM memory_item
                WHERE memory_id IN (
                  '00000000-0000-0000-0000-000000000701',
                  '00000000-0000-0000-0000-000000000702'
                )
                ORDER BY memory_id
                """
            )
            restored = {str(row[0]): row[1] for row in cur.fetchall()}

    assert set(restored.values()) == {"active"}


def test_conflict_resolution_keeps_memory_conflicted_when_another_open_conflict_exists(
    integration_client, integration_db: str
) -> None:
    first = integration_client.post(
        "/api/conflicts",
        json={
            "workspace_id": WORKSPACE_ID,
            "left_memory_id": "00000000-0000-0000-0000-000000000701",
            "right_memory_id": "00000000-0000-0000-0000-000000000702",
            "conflict_type": "contradiction",
        },
    )
    assert first.status_code == 201

    second = integration_client.post(
        "/api/conflicts",
        json={
            "workspace_id": WORKSPACE_ID,
            "left_memory_id": "00000000-0000-0000-0000-000000000701",
            "right_memory_id": "00000000-0000-0000-0000-000000000703",
            "conflict_type": "semantic",
        },
    )
    assert second.status_code == 201

    resolve_first = integration_client.patch(
        f"/api/conflicts/{first.json()['conflict_id']}",
        params={"workspace_id": WORKSPACE_ID},
        json={"status": "resolved", "resolution_note": "Resolved first conflict."},
    )
    assert resolve_first.status_code == 200

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT memory_id, status
                FROM memory_item
                WHERE memory_id IN (
                  '00000000-0000-0000-0000-000000000701',
                  '00000000-0000-0000-0000-000000000702',
                  '00000000-0000-0000-0000-000000000703'
                )
                """,
            )
            statuses = {str(row[0]): row[1] for row in cur.fetchall()}

    assert statuses["00000000-0000-0000-0000-000000000701"] == "conflicted"
    assert statuses["00000000-0000-0000-0000-000000000702"] == "active"
    assert statuses["00000000-0000-0000-0000-000000000703"] == "conflicted"


def test_conflict_triggers_do_not_revive_non_active_memory(
    integration_client, integration_db: str
) -> None:
    expected_statuses = {
        "00000000-0000-0000-0000-000000000701": "archived",
        "00000000-0000-0000-0000-000000000702": "forgotten",
        "00000000-0000-0000-0000-000000000703": "superseded",
    }
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            for memory_id, status_value in expected_statuses.items():
                cur.execute(
                    """
                    UPDATE memory_item
                    SET status = %(status)s
                    WHERE memory_id = %(memory_id)s
                      AND workspace_id = %(workspace_id)s
                    """,
                    {
                        "memory_id": memory_id,
                        "workspace_id": WORKSPACE_ID,
                        "status": status_value,
                    },
                )
        conn.commit()

    conflict = integration_client.post(
        "/api/conflicts",
        json={
            "workspace_id": WORKSPACE_ID,
            "left_memory_id": "00000000-0000-0000-0000-000000000701",
            "right_memory_id": "00000000-0000-0000-0000-000000000702",
            "conflict_type": "semantic",
        },
    )
    assert conflict.status_code == 201

    resolve = integration_client.patch(
        f"/api/conflicts/{conflict.json()['conflict_id']}",
        params={"workspace_id": WORKSPACE_ID},
        json={"status": "resolved", "resolution_note": "Resolved non-active pair."},
    )
    assert resolve.status_code == 200

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT memory_id, status
                FROM memory_item
                WHERE memory_id = ANY(%(memory_ids)s::uuid[])
                """,
                {"memory_ids": list(expected_statuses)},
            )
            statuses = {str(row[0]): row[1] for row in cur.fetchall()}

    assert statuses == expected_statuses


def test_conflict_creation_rejects_cross_workspace_memory(
    integration_client, integration_db: str
) -> None:
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO workspace(workspace_id, slug, name, scope_type, owner_user_id)
                VALUES (
                  '00000000-0000-0000-0000-000000000202',
                  'other-conflict',
                  'Other Workspace',
                  'project',
                  '00000000-0000-0000-0000-000000000101'
                )
                """
            )
            cur.execute(
                """
                INSERT INTO memory_item(
                  memory_id,
                  workspace_id,
                  memory_type,
                  canonical_text,
                  status,
                  access_level
                )
                VALUES (
                  '00000000-0000-0000-0000-000000000790',
                  '00000000-0000-0000-0000-000000000202',
                  'decision',
                  'Other workspace memory.',
                  'active',
                  'project'
                )
                """
            )
        conn.commit()

    response = integration_client.post(
        "/api/conflicts",
        json={
            "workspace_id": WORKSPACE_ID,
            "left_memory_id": "00000000-0000-0000-0000-000000000701",
            "right_memory_id": "00000000-0000-0000-0000-000000000790",
            "conflict_type": "semantic",
        },
    )

    assert response.status_code == 404


def test_conflict_timeline_and_audit_end_to_end(integration_client, integration_db: str) -> None:
    conflict_response = integration_client.get(
        "/api/conflicts", params={"workspace_id": WORKSPACE_ID}
    )
    assert conflict_response.status_code == 200
    assert conflict_response.json()["items"][0]["conflict_id"] == CONFLICT_ID

    no_resolved_response = integration_client.get(
        "/api/conflicts",
        params={"workspace_id": WORKSPACE_ID, "status": "resolved"},
    )
    assert no_resolved_response.status_code == 200
    assert no_resolved_response.json()["total"] == 0

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

    resolved_response = integration_client.get(
        "/api/conflicts",
        params={"workspace_id": WORKSPACE_ID, "status": "resolved"},
    )
    assert resolved_response.status_code == 200
    assert resolved_response.json()["items"][0]["conflict_id"] == CONFLICT_ID

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


def test_audit_lifecycle_statistics_actor_timeline_and_diff(
    integration_client, integration_db: str
) -> None:
    patch_response = integration_client.patch(
        f"/api/memories/{MEMORY_ID}",
        params={"workspace_id": WORKSPACE_ID},
        headers={
            "X-Actor-Type": "user",
            "X-Actor-Id": REVIEWER_USER_ID,
            "X-Revision-Reason": "audit hardening test",
        },
        json={"summary": "Audit hardening summary."},
    )
    assert patch_response.status_code == 200

    diff_response = integration_client.get(
        "/api/audit",
        params={
            "workspace_id": WORKSPACE_ID,
            "target_type": "memory_item",
            "target_id": MEMORY_ID,
            "include_diff": "true",
        },
    )
    assert diff_response.status_code == 200
    assert "summary" in diff_response.json()["items"][0]["diff_json"]

    lifecycle_response = integration_client.get(
        "/api/audit/lifecycle",
        params={
            "workspace_id": WORKSPACE_ID,
            "target_type": "memory_item",
            "target_id": MEMORY_ID,
        },
    )
    assert lifecycle_response.status_code == 200
    kinds = [item["kind"] for item in lifecycle_response.json()["items"]]
    assert "audit" in kinds
    assert "revision" in kinds

    actor_response = integration_client.get(
        f"/api/audit/actors/user/{REVIEWER_USER_ID}/timeline",
        params={"workspace_id": WORKSPACE_ID},
    )
    assert actor_response.status_code == 200
    assert actor_response.json()["total"] >= 1

    statistics_response = integration_client.get(
        "/api/audit/statistics",
        params={"workspace_id": WORKSPACE_ID, "group_by": "action_type"},
    )
    assert statistics_response.status_code == 200
    assert any(
        item["group_key"] == "memory.update"
        for item in statistics_response.json()["items"]
    )

    missing_workspace_response = integration_client.get(
        "/api/audit/lifecycle",
        params={
            "workspace_id": "00000000-0000-0000-0000-000000009999",
            "target_type": "memory_item",
            "target_id": MEMORY_ID,
        },
    )
    assert missing_workspace_response.status_code == 404


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

    repeat_response = integration_client.patch(
        f"/api/forget-requests/{request_id}",
        params={"workspace_id": WORKSPACE_ID},
        json={
            "status": "approved",
            "reviewed_by_user_id": REVIEWER_USER_ID,
        },
    )
    assert repeat_response.status_code == 200

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
            repeated_audit_count = cur.fetchone()[0]
    assert repeated_audit_count == audit_count


def test_forget_request_soft_governs_source_wiki_and_entity(
    integration_client, integration_db: str
) -> None:
    targets = [
        ("source_document", SOURCE_DOC_ID, "source_document"),
        ("wiki_page", WIKI_PAGE_ID, "wiki_page"),
        ("entity", ENTITY_ID, "entity"),
    ]

    for target_type, target_id, table_name in targets:
        create_response = integration_client.post(
            "/api/forget-requests",
            json={
                "workspace_id": WORKSPACE_ID,
                "target_type": target_type,
                "target_id": target_id,
                "requester_user_id": REVIEWER_USER_ID,
                "reason": f"Exercise {target_type} soft governance.",
            },
        )
        assert create_response.status_code == 201
        request_id = create_response.json()["request_id"]

        approve_response = integration_client.patch(
            f"/api/forget-requests/{request_id}",
            params={"workspace_id": WORKSPACE_ID},
            json={"status": "approved", "reviewed_by_user_id": REVIEWER_USER_ID},
        )
        assert approve_response.status_code == 200

        id_column = {
            "source_document": "doc_id",
            "wiki_page": "page_id",
            "entity": "entity_id",
        }[table_name]
        with psycopg.connect(integration_db) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT status, forgotten_at
                    FROM {table_name}
                    WHERE {id_column} = %(target_id)s
                    """,
                    {"target_id": target_id},
                )
                row = cur.fetchone()
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM audit_log
                    WHERE workspace_id = %(workspace_id)s
                      AND target_type = %(target_type)s
                      AND target_id = %(target_id)s
                      AND action_type = %(action_type)s
                    """,
                    {
                        "workspace_id": WORKSPACE_ID,
                        "target_type": target_type,
                        "target_id": target_id,
                        "action_type": f"{target_type}.forget",
                    },
                )
                audit_count = cur.fetchone()[0]
        assert row is not None
        assert row[0] == "forgotten"
        assert row[1] is not None
        assert audit_count == 1

        if target_type == "source_document":
            hidden_detail = integration_client.get(
                f"/api/sources/{target_id}",
                params={"workspace_id": WORKSPACE_ID},
            )
            assert hidden_detail.status_code == 404

            governance_detail = integration_client.get(
                f"/api/sources/{target_id}",
                params={"workspace_id": WORKSPACE_ID, "include_forgotten": "true"},
            )
            assert governance_detail.status_code == 200
            assert governance_detail.json()["status"] == "forgotten"

            default_sources = integration_client.get(
                "/api/sources",
                params={"workspace_id": WORKSPACE_ID, "keyword": "Project Pivot"},
            )
            assert default_sources.status_code == 200
            assert default_sources.json()["total"] == 0

            all_sources = integration_client.get(
                "/api/sources",
                params={
                    "workspace_id": WORKSPACE_ID,
                    "keyword": "Project Pivot",
                    "status": "all",
                },
            )
            assert all_sources.status_code == 200
            assert all_sources.json()["total"] == 1

            with psycopg.connect(integration_db) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM v_memory_with_source
                        WHERE doc_id = %(doc_id)s
                        """,
                        {"doc_id": target_id},
                    )
                    view_count = cur.fetchone()[0]
            assert view_count == 0
        elif target_type == "wiki_page":
            with psycopg.connect(integration_db) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM v_wiki_page_sources
                        WHERE page_id = %(page_id)s
                        """,
                        {"page_id": target_id},
                    )
                    view_count = cur.fetchone()[0]
            assert view_count == 0
        elif target_type == "entity":
            memory_detail = integration_client.get(
                f"/api/memories/{SEMANTIC_MEMORY_ID}",
                params={"workspace_id": WORKSPACE_ID},
            )
            assert memory_detail.status_code == 200
            assert all(
                entity["entity_id"] != ENTITY_ID for entity in memory_detail.json()["entities"]
            )


def test_memory_recall_statistics_view_aggregates_logged_results(
    integration_client, integration_db: str
) -> None:
    for _ in range(2):
        response = integration_client.post(
            "/api/recall",
            json={
                "workspace_id": WORKSPACE_ID,
                "query_text": "Recall should return memory items",
                "limit": 5,
            },
        )
        assert response.status_code == 200
        assert any(item["memory_id"] == MEMORY_ID for item in response.json()["memories"])

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT recall_count, last_recalled_at
                FROM v_memory_recall_statistics
                WHERE workspace_id = %(workspace_id)s
                  AND memory_id = %(memory_id)s
                """,
                {"workspace_id": WORKSPACE_ID, "memory_id": MEMORY_ID},
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0] >= 2
    assert row[1] is not None
