CREATE INDEX IF NOT EXISTS idx_source_document_workspace
  ON source_document(workspace_id, imported_at DESC);

CREATE INDEX IF NOT EXISTS idx_source_document_workspace_status
  ON source_document(workspace_id, status, imported_at DESC);

CREATE INDEX IF NOT EXISTS idx_source_chunk_fts
  ON source_chunk USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_source_chunk_text_trgm
  ON source_chunk USING GIN(chunk_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_agent_session_workspace
  ON agent_session(workspace_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_message_session_time
  ON message(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_memory_workspace_status
  ON memory_item(workspace_id, status);

CREATE INDEX IF NOT EXISTS idx_memory_workspace_type_status
  ON memory_item(workspace_id, memory_type, status);

CREATE INDEX IF NOT EXISTS idx_memory_workspace_status_validity
  ON memory_item(workspace_id, status, valid_from, valid_to);

CREATE INDEX IF NOT EXISTS idx_memory_created_at
  ON memory_item(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_fts
  ON memory_item USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_memory_canonical_text_trgm
  ON memory_item USING GIN(canonical_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_memory_evidence_chunk
  ON memory_evidence(chunk_id);

CREATE INDEX IF NOT EXISTS idx_source_document_title_trgm
  ON source_document USING GIN(title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_entity_workspace_type
  ON entity(workspace_id, entity_type);

CREATE INDEX IF NOT EXISTS idx_entity_workspace_status
  ON entity(workspace_id, status, canonical_name);

CREATE INDEX IF NOT EXISTS idx_memory_entity_entity
  ON memory_entity(entity_id);

CREATE INDEX IF NOT EXISTS idx_memory_entity_workspace
  ON memory_entity(workspace_id);

CREATE INDEX IF NOT EXISTS idx_memory_scene_workspace
  ON memory_scene(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_scene_cell_memory
  ON memory_scene_cell(memory_id);

CREATE INDEX IF NOT EXISTS idx_memory_scene_cell_order
  ON memory_scene_cell(scene_id, sort_order);

CREATE INDEX IF NOT EXISTS idx_timeline_workspace_time
  ON timeline_entry(workspace_id, event_time DESC);

CREATE INDEX IF NOT EXISTS idx_recall_workspace_time
  ON recall_log(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_policy_principal
  ON access_policy(workspace_id, principal_type, principal_id, resource_type, effect);

CREATE UNIQUE INDEX IF NOT EXISTS idx_policy_global_unique
  ON access_policy(workspace_id, principal_type, resource_type, resource_scope, effect)
  WHERE principal_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_audit_workspace_time
  ON audit_log(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_actor_time
  ON audit_log(workspace_id, actor_type, actor_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_target_time
  ON audit_log(workspace_id, target_type, target_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conflict_workspace_status
  ON conflict_record(workspace_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conflict_left_status
  ON conflict_record(left_memory_id, status);

CREATE INDEX IF NOT EXISTS idx_conflict_right_status
  ON conflict_record(right_memory_id, status);

CREATE INDEX IF NOT EXISTS idx_forget_request_workspace_status
  ON forget_request(workspace_id, status, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_forget_request_target
  ON forget_request(workspace_id, target_type, target_id, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_wiki_page_workspace_status
  ON wiki_page(workspace_id, status, updated_at DESC);

-- ============================================================
-- 进阶索引：BRIN + Covering（INCLUDE） + Partial
-- 见 docs/index-rationale.md 的"现代索引补强"章节
-- ============================================================

-- BRIN on audit_log(created_at)
-- audit_log 为 append-only by time，BRIN 用 page range + min/max 元组
-- 替代每行索引，索引大小通常是同语义 B-tree 的 1-2 个数量级以下；
-- 写入开销几乎为零；适合"按时间范围聚合 / 跨 workspace 全量回放"等
-- 分析型查询。与现有 idx_audit_workspace_time（B-tree, workspace 先导）
-- 形成互补：前者擅长"某 workspace 最近 N 条"，BRIN 擅长"全库时间窗口"。
CREATE INDEX IF NOT EXISTS idx_audit_brin_time
  ON audit_log USING BRIN(created_at) WITH (pages_per_range = 32);

-- Covering + Partial + Composite on memory_item
-- 同时演示三种现代 PostgreSQL 索引特性：
--   1) Partial (WHERE status = 'active'): 只索引活跃记录，索引随
--      forgotten/archived 比例增长而显著缩小；
--   2) Composite + DESC: 复合键直接覆盖 ORDER BY importance DESC, updated_at DESC；
--   3) Covering (INCLUDE, PG 11+): 把常被 SELECT 的非 key 列纳入索引叶子，
--      在 visibility map 全干净时可实现 index-only scan，省去 heap fetch。
-- 适配查询：dashboard / 首屏 / wiki 合成"活跃记忆排序短列表"。
CREATE INDEX IF NOT EXISTS idx_memory_active_ranking
  ON memory_item(workspace_id, importance DESC, updated_at DESC)
  INCLUDE (memory_id, memory_type, confidence, access_level)
  WHERE status = 'active';
