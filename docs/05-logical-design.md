# 逻辑结构设计

## 1. 关系模式总表

### 用户与工作区

```text
UserAccount(user_id PK, username UNIQUE, display_name, email UNIQUE, role_hint, created_at, updated_at)

Workspace(workspace_id PK, slug UNIQUE, name, description, scope_type, owner_user_id FK, created_at, updated_at)

Agent(agent_id PK, workspace_id FK, name, agent_type, status, owner_user_id FK, created_at)

WorkspaceMember(workspace_id FK, principal_type, principal_id, member_role, joined_at, PK(workspace_id, principal_type, principal_id))
```

### 会话与源文档

```text
AgentSession(session_id PK, workspace_id FK, agent_id FK, started_by_user_id FK, title, channel, started_at, ended_at)

Message(message_id PK, session_id FK, sender_type, sender_id, role, content, created_at, reply_to_message_id FK)

SourceDocument(doc_id PK, workspace_id FK, session_id FK, doc_type, title, source_path, raw_text, checksum, status, forgotten_at, imported_by_user_id FK, imported_at)

SourceChunk(chunk_id PK, doc_id FK, chunk_no, chunk_text, start_line, end_line, token_count, search_text_zh, search_vector, UNIQUE(doc_id, chunk_no))
```

`AgentSession.channel` includes `cli` for Agent Runtime sessions. `SourceDocument.doc_type`
includes `inline_agent_note`, which is reserved for backend-created evidence when an
agent commits a memory without explicit source chunks.

### 记忆、版本、证据

```text
MemoryItem(memory_id PK, workspace_id FK, created_from_doc_id FK, memory_type, canonical_text, summary, search_text_zh, search_vector, confidence, importance, status, access_level, owner_user_id FK, owner_agent_id FK, valid_from, valid_to, superseded_by_memory_id FK, current_revision_no, created_at, updated_at)

MemoryRevision(memory_id FK, revision_no, revision_text, revision_summary, revision_reason, editor_type, editor_id, created_at, PK(memory_id, revision_no))

MemoryEvidence(evidence_id PK, memory_id FK, chunk_id FK, evidence_role, weight, note, created_at, UNIQUE(memory_id, chunk_id, evidence_role))

MemoryEmbedding(embedding_id PK, memory_id FK, workspace_id FK, provider, model, dimension, embedding_json, embedding_text_hash, created_at, UNIQUE(memory_id, provider, model, embedding_text_hash), FK(memory_id, workspace_id))

SourceChunkEmbedding(embedding_id PK, chunk_id FK, doc_id FK, workspace_id FK, provider, model, dimension, embedding_json, embedding_text_hash, created_at, UNIQUE(chunk_id, provider, model, embedding_text_hash))

Entity(entity_id PK, workspace_id FK, canonical_name, entity_type, description, status, forgotten_at, created_at, updated_at, UNIQUE(workspace_id, canonical_name), UNIQUE(entity_id, workspace_id))

MemoryEntity(memory_id FK, entity_id FK, workspace_id FK, relation_role, created_at, PK(memory_id, entity_id, relation_role), FK(memory_id, workspace_id), FK(entity_id, workspace_id))

MemoryScene(scene_id PK, workspace_id FK, scene_slug, title, summary, created_at, updated_at, UNIQUE(workspace_id, scene_slug), UNIQUE(scene_id, workspace_id))

MemorySceneCell(scene_id FK, memory_id FK, workspace_id FK, cell_role, sort_order, note, created_at, PK(scene_id, memory_id), FK(scene_id, workspace_id), FK(memory_id, workspace_id))
```

### 表达层与治理层

```text
WikiPage(page_id PK, workspace_id FK, page_slug, page_type, title, current_revision_no, generated_from_scene_id FK, generated_from_memory_id FK, needs_rebuild, status, forgotten_at, created_at, updated_at)

WikiPageRevision(page_id FK, revision_no, frontmatter_json, body_markdown, generated_by, created_at, PK(page_id, revision_no))

TimelineEntry(timeline_id PK, workspace_id FK, memory_id FK, doc_id FK, event_type, title, description, event_time, importance, created_at)

RecallLog(recall_id PK, workspace_id FK, agent_id FK, user_id FK, query_text, filter_json, result_count, top_memory_ids_json, context_pack_json, created_at)

AccessPolicy(policy_id PK, workspace_id FK, principal_type, principal_id, resource_type, resource_scope, effect, predicate_json, created_at)

ConflictRecord(conflict_id PK, workspace_id FK, left_memory_id FK, right_memory_id FK, conflict_type, status, resolution_note, resolved_by_actor_type, resolved_by_actor_id, resolved_at, created_at, updated_at, CHECK(left_memory_id < right_memory_id), UNIQUE(left_memory_id, right_memory_id))

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
- Entity、MemoryScene 与 MemoryItem 的 M:N 关系通过 MemoryEntity 和 MemorySceneCell 拆分，关系属性 relation_role、cell_role、sort_order 只依赖各自复合主键。
- SourceDocument、WikiPage、Entity 的 `status` / `forgotten_at` 是治理状态，不承载业务内容依赖；默认视图和 API 过滤 `active`，遗忘审批只做软治理。
- MemoryEmbedding、SourceChunkEmbedding 作为 embedding 缓存表保存 provider/model/dimension/hash 与 JSONB 向量值；它们服务 hybrid recall，不把向量维度拆成关系列，也不依赖 pgvector。

例如 MemoryItem 不直接保存来源文本，而通过 MemoryEvidence 关联 SourceChunk，避免将证据来源冗余存储在主表中。

## 4. 允许的冗余字段

| 冗余字段 | 所在表 | 原因 |
|---|---|---|
| created_from_doc_id | memory_item | 快速查询主要来源 |
| current_revision_no | memory_item | 快速定位当前版本 |
| current_revision_no | wiki_page | 快速读取当前 Wiki |
| token_count | source_chunk | 避免重复计算 |
| search_text_zh / search_vector | source_chunk / memory_item | 预计算 jieba 搜索文本和 PostgreSQL FTS 向量，避免查询时重复分词和建向量 |
| embedding_json | memory_embedding / source_chunk_embedding | 缓存可选 embedding provider 的向量结果，避免重复调用模型 |
| top_memory_ids_json | recall_log | 保留召回快照 |
| workspace_id | memory_entity / memory_scene_cell | 支撑 workspace 过滤，并通过复合 FK 保证 M:N 两端属于同一 workspace |
| status / forgotten_at | source_document / wiki_page / entity | 支撑 ForgetRequest 软治理和审计回放 |
