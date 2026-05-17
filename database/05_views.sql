CREATE OR REPLACE VIEW v_active_memory AS
SELECT *
FROM memory_item
WHERE status = 'active'
  AND valid_from <= now()
  AND (valid_to IS NULL OR valid_to > now());

CREATE OR REPLACE VIEW v_memory_with_source AS
SELECT
  mi.workspace_id,
  mi.memory_id,
  mi.memory_type,
  mi.canonical_text,
  mi.status,
  mi.confidence,
  sd.doc_id,
  sd.title AS source_title,
  sd.source_path,
  sc.chunk_id,
  sc.chunk_no,
  sc.start_line,
  sc.end_line,
  me.evidence_role,
  me.weight
FROM memory_item mi
JOIN memory_evidence me ON me.memory_id = mi.memory_id
JOIN source_chunk sc ON sc.chunk_id = me.chunk_id
JOIN source_document sd ON sd.doc_id = sc.doc_id;

CREATE OR REPLACE VIEW v_project_timeline AS
SELECT
  te.workspace_id,
  te.timeline_id,
  te.memory_id,
  te.doc_id,
  te.event_time,
  te.event_type,
  te.title,
  te.description,
  te.importance,
  mi.memory_type,
  mi.canonical_text AS memory_text,
  sd.title AS source_title
FROM timeline_entry te
LEFT JOIN memory_item mi ON mi.memory_id = te.memory_id
LEFT JOIN source_document sd ON sd.doc_id = te.doc_id;

CREATE OR REPLACE VIEW v_memory_statistics AS
SELECT
  workspace_id,
  memory_type,
  status,
  access_level,
  count(*) AS memory_count,
  avg(confidence) AS avg_confidence,
  avg(importance) AS avg_importance
FROM memory_item
GROUP BY workspace_id, memory_type, status, access_level;

CREATE OR REPLACE VIEW v_agent_visible_memory AS
SELECT
  a.agent_id,
  mi.memory_id,
  mi.workspace_id,
  mi.memory_type,
  mi.canonical_text,
  mi.summary,
  mi.confidence,
  mi.importance,
  mi.status,
  mi.access_level,
  mi.updated_at
FROM agent a
JOIN memory_item mi
  ON mi.workspace_id = a.workspace_id
WHERE mi.status = 'active'
  AND mi.valid_from <= now()
  AND (mi.valid_to IS NULL OR mi.valid_to > now())
  AND NOT EXISTS (
    SELECT 1
    FROM access_policy ap
    WHERE ap.workspace_id = mi.workspace_id
      AND ap.resource_type = 'memory_item'
      AND ap.effect = 'deny'
      AND (
        (ap.principal_type = 'agent' AND ap.principal_id = a.agent_id)
        OR (
          ap.principal_type = 'role'
          AND coalesce(ap.predicate_json->>'agent_type', '') = a.agent_type
        )
      )
      AND (ap.resource_scope = 'all' OR ap.resource_scope = mi.access_level)
  )
  AND (
    mi.access_level IN ('public', 'project', 'team')
    OR EXISTS (
      SELECT 1
      FROM access_policy ap
      WHERE ap.workspace_id = mi.workspace_id
        AND ap.resource_type = 'memory_item'
        AND ap.effect = 'allow'
        AND (
          (ap.principal_type = 'agent' AND ap.principal_id = a.agent_id)
          OR (
            ap.principal_type = 'role'
            AND coalesce(ap.predicate_json->>'agent_type', '') = a.agent_type
          )
        )
        AND (ap.resource_scope = 'all' OR ap.resource_scope = mi.access_level)
    )
  );

CREATE OR REPLACE VIEW v_conflict_memory AS
SELECT
  cr.conflict_id,
  cr.workspace_id,
  cr.conflict_type,
  cr.status,
  cr.resolution_note,
  cr.resolved_by_actor_type,
  cr.resolved_by_actor_id,
  cr.resolved_at,
  cr.created_at,
  cr.updated_at,
  left_memory.memory_id AS left_memory_id,
  left_memory.memory_type AS left_memory_type,
  left_memory.canonical_text AS left_memory_text,
  left_memory.summary AS left_memory_summary,
  right_memory.memory_id AS right_memory_id,
  right_memory.memory_type AS right_memory_type,
  right_memory.canonical_text AS right_memory_text,
  right_memory.summary AS right_memory_summary
FROM conflict_record cr
JOIN memory_item left_memory ON left_memory.memory_id = cr.left_memory_id
JOIN memory_item right_memory ON right_memory.memory_id = cr.right_memory_id;
