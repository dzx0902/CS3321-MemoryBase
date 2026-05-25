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

CREATE INDEX IF NOT EXISTS idx_memory_embedding_memory
  ON memory_embedding(memory_id);

CREATE INDEX IF NOT EXISTS idx_memory_embedding_workspace_model
  ON memory_embedding(workspace_id, provider, model);

CREATE INDEX IF NOT EXISTS idx_source_chunk_embedding_chunk
  ON source_chunk_embedding(chunk_id);

CREATE INDEX IF NOT EXISTS idx_source_chunk_embedding_workspace_model
  ON source_chunk_embedding(workspace_id, provider, model);

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
