# 逻辑结构设计

## 1. 关系模式总表

### 用户与工作区

```text
UserAccount(user_id PK, username UNIQUE, display_name, email UNIQUE, role_hint, created_at, updated_at)

Workspace(workspace_id PK, name, description, scope_type, owner_user_id FK, created_at, updated_at)

Agent(agent_id PK, workspace_id FK, name, agent_type, status, owner_user_id FK, created_at)

WorkspaceMember(workspace_id FK, principal_type, principal_id, member_role, joined_at, PK(workspace_id, principal_type, principal_id))
```

### 会话与源文档

```text
AgentSession(session_id PK, workspace_id FK, agent_id FK, started_by_user_id FK, title, channel, started_at, ended_at)

Message(message_id PK, session_id FK, sender_type, sender_id, role, content, created_at, reply_to_message_id FK)

SourceDocument(doc_id PK, workspace_id FK, session_id FK, doc_type, title, source_path, raw_text, checksum, imported_by_user_id FK, imported_at)

SourceChunk(chunk_id PK, doc_id FK, chunk_no, chunk_text, start_line, end_line, token_count, search_vector, UNIQUE(doc_id, chunk_no))
```

### 记忆、版本、证据

```text
MemoryItem(memory_id PK, workspace_id FK, created_from_doc_id FK, memory_type, canonical_text, summary, confidence, importance, status, access_level, owner_user_id FK, owner_agent_id FK, valid_from, valid_to, superseded_by_memory_id FK, current_revision_no, created_at, updated_at)

MemoryRevision(memory_id FK, revision_no, revision_text, revision_summary, revision_reason, editor_type, editor_id, created_at, PK(memory_id, revision_no))

MemoryEvidence(evidence_id PK, memory_id FK, chunk_id FK, evidence_role, weight, note, created_at, UNIQUE(memory_id, chunk_id, evidence_role))
```

### 表达层与治理层

```text
WikiPage(page_id PK, workspace_id FK, page_slug, page_type, title, current_revision_no, generated_from_scene_id FK, generated_from_memory_id FK, needs_rebuild, created_at, updated_at)

WikiPageRevision(page_id FK, revision_no, frontmatter_json, body_markdown, generated_by, created_at, PK(page_id, revision_no))

TimelineEntry(timeline_id PK, workspace_id FK, memory_id FK, doc_id FK, event_type, title, description, event_time, importance, created_at)

RecallLog(recall_id PK, workspace_id FK, agent_id FK, user_id FK, query_text, filter_json, result_count, top_memory_ids_json, context_pack_json, created_at)

AccessPolicy(policy_id PK, workspace_id FK, principal_type, principal_id, resource_type, resource_scope, effect, predicate_json, created_at)

ConflictRecord(conflict_id PK, workspace_id FK, left_memory_id FK, right_memory_id FK, conflict_type, status, resolution_note, created_at, resolved_at, UNIQUE(left_memory_id, right_memory_id, conflict_type))

ForgetRequest(request_id PK, workspace_id FK, target_type, target_id, requester_user_id FK, reviewed_by_user_id FK, reason, status, requested_at, resolved_at)

AuditLog(audit_id PK, workspace_id FK, actor_type, actor_id, action_type, target_type, target_id, before_json, after_json, created_at)
```

## 2. E-R 到关系模型转换

| 概念关系 | 转换结果 |
|---|---|
| Workspace 1:N SourceDocument | source_document.workspace_id |
| SourceDocument 1:N SourceChunk | source_chunk.doc_id |
| MemoryItem 1:N MemoryRevision | memory_revision.memory_id |
| MemoryItem M:N SourceChunk | memory_evidence |
| MemoryScene M:N MemoryItem | memory_scene_cell |
| MemoryItem M:N Entity | memory_entity |
| Entity M:N Entity | entity_relation |
| Workspace M:N User/Agent | workspace_member |

## 3. 3NF 分析

大部分表满足 3NF：

- 每张表有明确主键。
- 非主属性依赖主键。
- 非主属性之间不存在明显传递依赖。
- M:N 关系拆成中间表。
- 版本内容拆到 MemoryRevision。
- 权限策略独立为 AccessPolicy。
- 审计记录独立为 AuditLog。

例如 MemoryItem 不直接保存来源文本，而通过 MemoryEvidence 关联 SourceChunk，避免将证据来源冗余存储在主表中。

## 4. 允许的冗余字段

| 冗余字段 | 所在表 | 原因 |
|---|---|---|
| created_from_doc_id | memory_item | 快速查询主要来源 |
| current_revision_no | memory_item | 快速定位当前版本 |
| current_revision_no | wiki_page | 快速读取当前 Wiki |
| token_count | source_chunk | 避免重复计算 |
| top_memory_ids_json | recall_log | 保留召回快照 |
| alias_json | entity | 别名数量不固定 |
