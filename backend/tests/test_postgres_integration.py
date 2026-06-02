from __future__ import annotations

from pathlib import Path
from uuid import UUID

import psycopg
import pytest
from scripts.backfill_search_terms import backfill_search_terms

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

    lifecycle_policy = integration_client.post(
        "/api/policies",
        json={
            "workspace_id": WORKSPACE_ID,
            "principal_type": "role",
            "resource_type": "wiki_page",
            "resource_scope": "team",
            "effect": "allow",
            "predicate_json": {"purpose": "policy lifecycle test"},
        },
    )
    assert lifecycle_policy.status_code == 201
    policy_id = lifecycle_policy.json()["policy_id"]

    update_policy = integration_client.patch(
        f"/api/policies/{policy_id}",
        params={"workspace_id": WORKSPACE_ID},
        json={"effect": "deny", "predicate_json": {"purpose": "updated"}},
    )
    assert update_policy.status_code == 200
    assert update_policy.json()["effect"] == "deny"

    delete_policy = integration_client.delete(
        f"/api/policies/{policy_id}",
        params={"workspace_id": WORKSPACE_ID},
    )
    assert delete_policy.status_code == 200
    assert delete_policy.json()["deleted"] is True

    policy_audit = integration_client.get(
        "/api/audit",
        params={
            "workspace_id": WORKSPACE_ID,
            "target_type": "access_policy",
            "target_id": policy_id,
            "include_diff": "true",
        },
    )
    assert policy_audit.status_code == 200
    actions = [item["action_type"] for item in policy_audit.json()["items"]]
    assert "policy.update" in actions
    assert "policy.delete" in actions

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


def test_search_endpoint_returns_rrf_results_for_chinese_query(
    integration_client, integration_db: str
) -> None:
    response = integration_client.post(
        "/api/search",
        json={
            "workspace_id": WORKSPACE_ID,
            "agent_id": AGENT_ID,
            "query_text": "为什么放弃校园食堂方向",
            "scope": "all",
            "limit": 8,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_count"] >= 1
    assert "cafeteria" in payload["tokenized_query"]
    assert any(item["result_type"] == "chunk" for item in payload["items"])
    assert any("chunk_fts" in item["strategies"] for item in payload["items"])
    assert any("cafeteria system" in item["snippet"].lower() for item in payload["items"])


def test_search_endpoint_hides_private_memories_without_agent(
    integration_client, integration_db: str
) -> None:
    response = integration_client.post(
        "/api/search",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "private budget",
            "scope": "memories",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert all(item["result_id"] != PRIVATE_MEMORY_ID for item in response.json()["items"])


def test_search_endpoint_uses_trigram_fuzzy_route(integration_client, integration_db: str) -> None:
    response = integration_client.post(
        "/api/search",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "cafeteria systm",
            "scope": "all",
            "limit": 8,
        },
    )

    assert response.status_code == 200
    assert any("trigram_fuzzy" in item["strategies"] for item in response.json()["items"])


def test_chinese_source_recall_uses_segmented_search_text(
    integration_client, integration_db: str
) -> None:
    source_response = integration_client.post(
        "/api/sources",
        json={
            "workspace_id": WORKSPACE_ID,
            "title": "中文检索验证",
            "doc_type": "note",
            "raw_text": "我们需要重审校园食堂方向，并记录新的数据库课设判断。",
            "source_path": "inline://test/chinese-search",
        },
    )
    assert source_response.status_code == 201

    source_detail = integration_client.get(
        f"/api/sources/{source_response.json()['doc_id']}",
        params={"workspace_id": WORKSPACE_ID},
    )
    assert source_detail.status_code == 200
    chunk_id = source_detail.json()["chunks"][0]["chunk_id"]

    memory_response = integration_client.post(
        "/api/memories",
        json={
            "workspace_id": WORKSPACE_ID,
            "created_from_doc_id": source_response.json()["doc_id"],
            "memory_type": "decision",
            "canonical_text": "校园食堂方向需要重审。",
            "summary": "中文分词召回验证",
            "confidence": 0.9,
            "importance": 4,
            "access_level": "project",
            "evidence": [{"chunk_id": chunk_id, "evidence_role": "supports"}],
        },
    )
    assert memory_response.status_code == 201

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sc.search_text_zh,
                       sc.search_vector @@ plainto_tsquery('simple', '食堂 方向')
                FROM source_chunk sc
                WHERE sc.chunk_id = %(chunk_id)s
                """,
                {"chunk_id": chunk_id},
            )
            chunk_row = cur.fetchone()
            cur.execute(
                """
                SELECT search_text_zh,
                       search_vector @@ plainto_tsquery('simple', '食堂 方向')
                FROM memory_item
                WHERE memory_id = %(memory_id)s
                """,
                {"memory_id": memory_response.json()["memory_id"]},
            )
            memory_row = cur.fetchone()

    assert chunk_row is not None
    assert {"食堂", "方向"}.issubset(set(chunk_row[0].split()))
    assert chunk_row[1] is True
    assert memory_row is not None
    assert {"食堂", "方向"}.issubset(set(memory_row[0].split()))
    assert memory_row[1] is True

    recall_response = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "食堂方向",
            "limit": 5,
        },
    )
    assert recall_response.status_code == 200
    assert any(
        item["memory_id"] == memory_response.json()["memory_id"]
        for item in recall_response.json()["memories"]
    )


def test_recall_uses_or_semantics_for_multi_term_agent_queries(
    integration_client, integration_db: str
) -> None:
    source_response = integration_client.post(
        "/api/sources",
        json={
            "workspace_id": WORKSPACE_ID,
            "title": "Recall CLI Bug Notes",
            "doc_type": "note",
            "raw_text": (
                "The CLI recall command must emit parseable JSON pipelines "
                "when no result exists and use exit code 4."
            ),
            "source_path": "inline://test/recall-or-query",
        },
    )
    assert source_response.status_code == 201

    source_detail = integration_client.get(
        f"/api/sources/{source_response.json()['doc_id']}",
        params={"workspace_id": WORKSPACE_ID},
    )
    assert source_detail.status_code == 200
    chunk_id = source_detail.json()["chunks"][0]["chunk_id"]

    memory_response = integration_client.post(
        "/api/memories",
        json={
            "workspace_id": WORKSPACE_ID,
            "created_from_doc_id": source_response.json()["doc_id"],
            "memory_type": "procedural",
            "canonical_text": (
                "CLI recall miss should produce parseable JSON pipelines and exit code 4."
            ),
            "summary": "Recall CLI no-result contract",
            "confidence": 0.9,
            "importance": 4,
            "access_level": "project",
            "evidence": [{"chunk_id": chunk_id, "evidence_role": "supports"}],
        },
    )
    assert memory_response.status_code == 201

    recall_response = integration_client.post(
        "/api/recall",
        json={
            "workspace_id": WORKSPACE_ID,
            "query_text": "JSON pipeline exit code",
            "limit": 5,
        },
    )

    assert recall_response.status_code == 200
    assert any(
        item["memory_id"] == memory_response.json()["memory_id"]
        for item in recall_response.json()["memories"]
    )


def test_seed_search_text_columns_are_populated(integration_db: str) -> None:
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM source_chunk
                WHERE search_text_zh IS NULL
                   OR search_vector IS NULL
                """
            )
            chunk_missing = cur.fetchone()[0]
            cur.execute(
                """
                SELECT count(*)
                FROM memory_item
                WHERE search_text_zh IS NULL
                   OR search_vector IS NULL
                """
            )
            memory_missing = cur.fetchone()[0]
            cur.execute(
                """
                SELECT chunk_text, search_text_zh
                FROM source_chunk
                WHERE chunk_id = '00000000-0000-0000-0000-000000000619'
                """
            )
            seeded_chunk = cur.fetchone()
            cur.execute(
                """
                SELECT canonical_text, search_text_zh
                FROM memory_item
                WHERE memory_id = '00000000-0000-0000-0000-000000000701'
                """
            )
            seeded_memory = cur.fetchone()

    assert chunk_missing == 0
    assert memory_missing == 0
    assert seeded_chunk is not None
    assert seeded_chunk[1] != seeded_chunk[0]
    assert {"cafeteria", "system"}.issubset(set(seeded_chunk[1].split()))
    assert seeded_memory is not None
    assert seeded_memory[1] != seeded_memory[0]
    assert {"cafeteria", "rejected"}.issubset(set(seeded_memory[1].split()))


def test_backfill_search_terms_does_not_create_memory_audit(integration_db: str) -> None:
    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM audit_log
                WHERE target_type = 'memory_item'
                  AND target_id = %(memory_id)s
                """,
                {"memory_id": MEMORY_ID},
            )
            audit_before = cur.fetchone()[0]
            cur.execute("ALTER TABLE memory_item DISABLE TRIGGER USER")
            cur.execute(
                """
                UPDATE memory_item
                SET search_text_zh = NULL
                WHERE memory_id = %(memory_id)s
                """,
                {"memory_id": MEMORY_ID},
            )
            cur.execute("ALTER TABLE memory_item ENABLE TRIGGER USER")
        conn.commit()

    counts = backfill_search_terms(
        integration_db,
        full=False,
        missing_only=True,
        workspace_slug="cs3321-demo",
    )

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT search_text_zh
                FROM memory_item
                WHERE memory_id = %(memory_id)s
                """,
                {"memory_id": MEMORY_ID},
            )
            search_text = cur.fetchone()[0]
            cur.execute(
                """
                SELECT count(*)
                FROM audit_log
                WHERE target_type = 'memory_item'
                  AND target_id = %(memory_id)s
                """,
                {"memory_id": MEMORY_ID},
            )
            audit_after = cur.fetchone()[0]

    assert counts.memories == 1
    assert "recall" in search_text.split()
    assert audit_after == audit_before


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


def test_agent_memory_create_without_evidence_creates_inline_source_and_audit(
    integration_client,
    integration_db: str,
) -> None:
    response = integration_client.post(
        "/api/memories",
        headers={
            "X-Actor-Type": "agent",
            "X-Actor-Id": AGENT_ID,
            "X-Revision-Reason": "cli remember commit",
        },
        json={
            "workspace_id": WORKSPACE_ID,
            "memory_type": "decision",
            "canonical_text": "CLI remember can write an agent note without explicit evidence.",
            "summary": "Inline evidence writeback",
            "confidence": 0.86,
            "importance": 4,
            "access_level": "project",
            "owner_agent_id": AGENT_ID,
            "evidence": [],
        },
    )

    assert response.status_code == 201
    memory_id = response.json()["memory_id"]
    assert response.json()["created_from_doc_id"] is not None
    assert response.json()["evidence_count"] == 1

    detail = integration_client.get(
        f"/api/memories/{memory_id}", params={"workspace_id": WORKSPACE_ID}
    )
    assert detail.status_code == 200
    evidence = detail.json()["evidence"][0]
    assert evidence["source_title"].startswith("agent_note_")
    assert evidence["evidence_role"] == "source"
    assert detail.json()["revisions"][0]["editor_type"] == "agent"
    assert detail.json()["revisions"][0]["editor_id"] == AGENT_ID
    assert detail.json()["revisions"][0]["revision_reason"] == "cli remember commit"

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sd.doc_type, al.action_type, al.actor_type, al.actor_id
                FROM source_document sd
                JOIN audit_log al ON al.target_id = sd.doc_id
                WHERE sd.doc_id = %(doc_id)s
                  AND al.target_type = 'source_document'
                """,
                {"doc_id": response.json()["created_from_doc_id"]},
            )
            row = cur.fetchone()
    assert row is not None
    assert row[0] == "inline_agent_note"
    assert row[1] == "source_document.create"
    assert row[2] == "agent"
    assert str(row[3]) == AGENT_ID


def test_sessions_and_observe_api_write_messages_and_batch_rolls_back(
    integration_client,
    integration_db: str,
) -> None:
    session_response = integration_client.post(
        "/api/sessions",
        json={
            "workspace_id": WORKSPACE_ID,
            "agent_id": AGENT_ID,
            "title": "CLI review session",
            "channel": "cli",
        },
    )

    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]
    assert session_response.json()["channel"] == "cli"

    message_response = integration_client.post(
        "/api/observe",
        json={
            "session_id": session_id,
            "sender_type": "user",
            "role": "user",
            "content": "请记录这个开发会话。",
        },
    )
    assert message_response.status_code == 201
    assert message_response.json()["content"] == "请记录这个开发会话。"

    second_message_response = integration_client.post(
        "/api/observe",
        json={
            "session_id": session_id,
            "sender_type": "agent",
            "role": "assistant",
            "content": "已记录当前开发会话。",
        },
    )
    assert second_message_response.status_code == 201

    messages_response = integration_client.get(
        f"/api/sessions/{session_id}/messages",
        params={"workspace_id": WORKSPACE_ID, "limit": 10},
    )
    assert messages_response.status_code == 200
    messages_payload = messages_response.json()
    assert messages_payload["total"] == 2
    assert [item["content"] for item in messages_payload["items"]] == [
        "请记录这个开发会话。",
        "已记录当前开发会话。",
    ]

    wrong_workspace_messages = integration_client.get(
        f"/api/sessions/{session_id}/messages",
        params={"workspace_id": "00000000-0000-0000-0000-000000009999"},
    )
    assert wrong_workspace_messages.status_code == 404

    list_response = integration_client.get(
        "/api/sessions",
        params={"workspace_id": WORKSPACE_ID, "agent_id": AGENT_ID},
    )
    assert list_response.status_code == 200
    assert any(item["session_id"] == session_id for item in list_response.json()["items"])

    batch_response = integration_client.post(
        "/api/observe/batch",
        json={
            "messages": [
                {
                    "session_id": session_id,
                    "sender_type": "user",
                    "role": "user",
                    "content": "first message should roll back",
                },
                {
                    "session_id": "00000000-0000-0000-0000-000000009999",
                    "sender_type": "agent",
                    "role": "assistant",
                    "content": "missing session forces rollback",
                },
            ]
        },
    )
    assert batch_response.status_code == 404

    with psycopg.connect(integration_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM message
                WHERE session_id = %(session_id)s
                  AND content = 'first message should roll back'
                """,
                {"session_id": session_id},
            )
            count = cur.fetchone()[0]
    assert count == 0


def test_memory_detail_includes_entities_and_scenes(
    integration_client, integration_db: str
) -> None:
    response = integration_client.get(
        f"/api/memories/{SEMANTIC_MEMORY_ID}", params={"workspace_id": WORKSPACE_ID}
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(
        entity["canonical_name"] == "Campus Cafeteria System" for entity in payload["entities"]
    )
    assert any(scene["scene_slug"] == "topic-decision" for scene in payload["scenes"])


def test_semantic_list_endpoints_return_seed_entities_and_scenes(
    integration_client, integration_db: str
) -> None:
    entities = integration_client.get(
        "/api/entities",
        params={"workspace_id": WORKSPACE_ID, "keyword": "System"},
    )
    scenes = integration_client.get(
        "/api/scenes",
        params={"workspace_id": WORKSPACE_ID, "keyword": "topic"},
    )

    assert entities.status_code == 200
    assert any(
        entity["canonical_name"] == "Campus Cafeteria System" for entity in entities.json()["items"]
    )
    assert scenes.status_code == 200
    assert any(scene["scene_slug"] == "topic-decision" for scene in scenes.json()["items"])


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
    assert any(item["group_key"] == "memory.update" for item in statistics_response.json()["items"])

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


def test_wiki_batch_export_writes_independent_pages_and_respects_write_files(
    integration_client, integration_db: str
) -> None:
    response = integration_client.post(
        "/api/wiki/export",
        json={
            "workspace_id": WORKSPACE_ID,
            "pages": [
                {
                    "page_slug": "batch-no-file-a",
                    "title": "Why MemoryBase",
                    "page_type": "synthesis",
                    "memory_ids": [MEMORY_ID],
                },
                {
                    "page_slug": "batch-no-file-b",
                    "title": "Demo Plan",
                    "page_type": "report",
                    "max_memories": 3,
                },
                {
                    "page_slug": "batch-no-file-c",
                    "title": "Policy and Recall",
                    "page_type": "handbook",
                    "max_memories": 2,
                },
            ],
            "write_files": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == WORKSPACE_ID
    assert [page["page_slug"] for page in payload["pages"]] == [
        "batch-no-file-a",
        "batch-no-file-b",
        "batch-no-file-c",
    ]
    assert all(page["revision_no"] == 1 for page in payload["pages"])
    assert all(
        page["file_path"].startswith(f"data/markdown_wiki/{WORKSPACE_ID}/")
        for page in payload["pages"]
    )
    assert not Path(payload["pages"][0]["file_path"]).exists()

    second = integration_client.post(
        "/api/wiki/export",
        json={
            "workspace_id": WORKSPACE_ID,
            "pages": [
                {
                    "page_slug": "why-memorybase",
                    "title": "Why MemoryBase",
                    "page_type": "synthesis",
                    "memory_ids": [MEMORY_ID],
                }
            ],
            "write_files": True,
        },
    )

    assert second.status_code == 200
    assert second.json()["pages"][0]["revision_no"] == 2
    assert Path(second.json()["pages"][0]["file_path"]).exists()


def test_wiki_read_endpoints_return_seed_page_detail_and_revisions(
    integration_client, integration_db: str
) -> None:
    list_response = integration_client.get(
        "/api/wiki",
        params={"workspace_id": WORKSPACE_ID, "keyword": "MemoryBase"},
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] >= 1
    assert any(page["page_slug"] == "why-memorybase" for page in list_payload["items"])

    detail_response = integration_client.get(
        f"/api/wiki/{WIKI_PAGE_ID}",
        params={"workspace_id": WORKSPACE_ID},
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["page_slug"] == "why-memorybase"
    assert detail_payload["latest_revision"]["revision_no"] == detail_payload["current_revision_no"]
    assert isinstance(detail_payload["memory_ids"], list)
    assert isinstance(detail_payload["source_doc_ids"], list)
    assert detail_payload["memory_count"] >= 0
    assert detail_payload["source_count"] >= 0

    revisions_response = integration_client.get(
        f"/api/wiki/{WIKI_PAGE_ID}/revisions",
        params={"workspace_id": WORKSPACE_ID},
    )
    assert revisions_response.status_code == 200
    revisions_payload = revisions_response.json()
    assert revisions_payload["total"] >= 1
    assert revisions_payload["items"][0]["body_markdown"].startswith("# Why MemoryBase")


def test_stats_overview_returns_seed_workspace_counts(
    integration_client, integration_db: str
) -> None:
    response = integration_client.get(
        "/api/stats/overview",
        params={"workspace_id": WORKSPACE_ID},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == WORKSPACE_ID
    assert payload["source_count"] >= 6
    assert payload["memory_count"] >= 20
    assert payload["active_memory_count"] > 0
    assert payload["wiki_page_count"] >= 3
    assert payload["entity_count"] >= 1
    assert payload["scene_count"] >= 1
    assert any(item["memory_type"] == "decision" for item in payload["memory_statistics"])


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


def test_graph_workspace_filters_private_memory_by_agent_visibility(
    integration_client, integration_db: str
) -> None:
    hidden_response = integration_client.get(
        "/api/graph/workspace",
        params={"workspace_id": WORKSPACE_ID, "limit": 30},
    )
    assert hidden_response.status_code == 200
    hidden_payload = hidden_response.json()
    hidden_node_ids = {node["id"] for node in hidden_payload["nodes"]}
    assert f"memory:{PRIVATE_MEMORY_ID}" not in hidden_node_ids

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
                    'graph-viewer',
                    'retriever',
                    'active',
                    '00000000-0000-0000-0000-000000000104'
                )
                ON CONFLICT (agent_id) DO NOTHING
                """,
                {"workspace_id": WORKSPACE_ID},
            )
        conn.commit()

    still_hidden = integration_client.get(
        "/api/graph/workspace",
        params={
            "workspace_id": WORKSPACE_ID,
            "agent_id": "00000000-0000-0000-0000-000000000302",
            "limit": 30,
        },
    )
    assert still_hidden.status_code == 200
    still_hidden_ids = {node["id"] for node in still_hidden.json()["nodes"]}
    assert f"memory:{PRIVATE_MEMORY_ID}" not in still_hidden_ids

    policy_response = integration_client.post(
        "/api/policies",
        json={
            "workspace_id": WORKSPACE_ID,
            "principal_type": "agent",
            "principal_id": "00000000-0000-0000-0000-000000000302",
            "resource_type": "memory_item",
            "resource_scope": "private",
            "effect": "allow",
            "predicate_json": {"reason": "graph visibility test"},
        },
    )
    assert policy_response.status_code == 201

    visible_response = integration_client.get(
        "/api/graph/workspace",
        params={
            "workspace_id": WORKSPACE_ID,
            "agent_id": "00000000-0000-0000-0000-000000000302",
            "limit": 30,
        },
    )
    assert visible_response.status_code == 200
    visible_payload = visible_response.json()
    visible_node_ids = {node["id"] for node in visible_payload["nodes"]}
    assert f"memory:{PRIVATE_MEMORY_ID}" in visible_node_ids
    assert any(
        edge["source"] == f"memory:{PRIVATE_MEMORY_ID}"
        or edge["target"] == f"memory:{PRIVATE_MEMORY_ID}"
        for edge in visible_payload["edges"]
    )


def test_graph_sync_records_audit_attribution(
    integration_client, integration_db: str, monkeypatch
) -> None:
    from app.api import deps as deps_module
    from app.services.graph_service import Neo4jGraphStore

    original_sync = Neo4jGraphStore.sync
    original_health = Neo4jGraphStore.health

    def fake_health(self):
        from app.models.graph import GraphHealthResponse

        return GraphHealthResponse(
            enabled=True,
            available=True,
            uri=self.settings.neo4j_uri,
            database=self.settings.neo4j_database,
        )

    def fake_sync(self, graph):
        from app.models.graph import GraphSyncResponse

        return GraphSyncResponse(
            workspace_id=graph.workspace_id,
            status="synced",
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
        )

    monkeypatch.setattr(Neo4jGraphStore, "health", fake_health)
    monkeypatch.setattr(Neo4jGraphStore, "sync", fake_sync)
    deps_module.get_graph_service.cache_clear()

    try:
        response = integration_client.post(
            "/api/graph/workspace/sync",
            params={
                "workspace_id": WORKSPACE_ID,
                "agent_id": AGENT_ID,
                "limit": 25,
            },
        )
        assert response.status_code == 200

        with psycopg.connect(integration_db) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT actor_type, actor_id, action_type, target_type, target_id
                    FROM audit_log
                    WHERE workspace_id = %(workspace_id)s
                      AND action_type = 'graph.sync'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    {"workspace_id": WORKSPACE_ID},
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == "agent"
        assert row[1] == UUID(AGENT_ID)
        assert row[2] == "graph.sync"
        assert row[3] == "workspace"
        assert row[4] == UUID(WORKSPACE_ID)
    finally:
        monkeypatch.setattr(Neo4jGraphStore, "health", original_health)
        monkeypatch.setattr(Neo4jGraphStore, "sync", original_sync)
        deps_module.get_graph_service.cache_clear()
