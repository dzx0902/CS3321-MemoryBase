CREATE INDEX IF NOT EXISTS idx_source_document_workspace
  ON source_document(workspace_id, imported_at DESC);

CREATE INDEX IF NOT EXISTS idx_source_chunk_fts
  ON source_chunk USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_agent_session_workspace
  ON agent_session(workspace_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_message_session_time
  ON message(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_memory_workspace_status
  ON memory_item(workspace_id, status);

CREATE INDEX IF NOT EXISTS idx_memory_workspace_type_status
  ON memory_item(workspace_id, memory_type, status);

CREATE INDEX IF NOT EXISTS idx_memory_created_at
  ON memory_item(workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_evidence_chunk
  ON memory_evidence(chunk_id);

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

CREATE INDEX IF NOT EXISTS idx_conflict_workspace_status
  ON conflict_record(workspace_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_forget_request_workspace_status
  ON forget_request(workspace_id, status, requested_at DESC);
