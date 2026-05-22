DROP VIEW IF EXISTS v_wiki_page_sources;
DROP VIEW IF EXISTS v_conflict_memory;
DROP VIEW IF EXISTS v_project_timeline;
DROP VIEW IF EXISTS v_agent_visible_memory;
DROP VIEW IF EXISTS v_memory_with_source;
DROP VIEW IF EXISTS v_memory_recall_statistics;
DROP VIEW IF EXISTS v_memory_statistics;
DROP VIEW IF EXISTS v_active_memory;

CREATE OR REPLACE VIEW v_active_memory AS
SELECT
  memory_id,
  workspace_id,
  created_from_doc_id,
  memory_type,
  canonical_text,
  summary,
  confidence,
  importance,
  status,
  access_level,
  owner_user_id,
  owner_agent_id,
  valid_from,
  valid_to,
  superseded_by_memory_id,
  current_revision_no,
  created_at,
  updated_at
FROM memory_item
WHERE status = 'active'
  AND valid_from <= now()
  AND (valid_to IS NULL OR valid_to > now());

CREATE OR REPLACE VIEW v_memory_with_source AS
SELECT
  mi.memory_id,
  mi.workspace_id,
  mi.created_from_doc_id,
  mi.memory_type,
  mi.canonical_text,
  mi.summary,
  mi.status,
  mi.confidence,
  mi.importance,
  mi.access_level,
  me.evidence_id,
  me.evidence_role,
  me.weight,
  me.note AS evidence_note,
  me.created_at AS evidence_created_at,
  sc.chunk_id,
  sc.chunk_no,
  sc.chunk_text,
  sc.start_line,
  sc.end_line,
  sc.token_count,
  sd.doc_id,
  sd.title AS source_title,
  sd.source_path,
  sd.doc_type,
  sd.checksum,
  sd.imported_at
FROM memory_item mi
JOIN memory_evidence me ON me.memory_id = mi.memory_id
JOIN source_chunk sc ON sc.chunk_id = me.chunk_id
JOIN source_document sd ON sd.doc_id = sc.doc_id
WHERE sd.status = 'active';

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
  te.created_at,
  mi.memory_type,
  mi.canonical_text AS memory_text,
  mi.status AS memory_status,
  sd.title AS source_title,
  sd.source_path
FROM timeline_entry te
LEFT JOIN memory_item mi ON mi.memory_id = te.memory_id
LEFT JOIN source_document sd ON sd.doc_id = te.doc_id;

CREATE OR REPLACE VIEW v_wiki_page_sources AS
SELECT
  wp.workspace_id,
  wp.page_id,
  wp.page_slug,
  wp.page_type,
  wp.title AS page_title,
  wp.current_revision_no,
  wp.generated_from_scene_id,
  wp.generated_from_memory_id,
  wp.needs_rebuild,
  ms.scene_slug,
  ms.title AS scene_title,
  page_memory.cell_role AS scene_cell_role,
  page_memory.sort_order AS scene_sort_order,
  mi.memory_id,
  mi.memory_type,
  mi.canonical_text,
  mi.summary AS memory_summary,
  mi.status AS memory_status,
  me.evidence_id,
  me.evidence_role,
  me.weight,
  me.note AS evidence_note,
  sc.chunk_id,
  sc.chunk_no,
  sc.chunk_text,
  sc.start_line,
  sc.end_line,
  sd.doc_id,
  sd.title AS source_title,
  sd.source_path,
  sd.doc_type
FROM wiki_page wp
LEFT JOIN memory_scene ms ON ms.scene_id = wp.generated_from_scene_id
LEFT JOIN LATERAL (
  SELECT
    wp.generated_from_memory_id AS memory_id,
    NULL::VARCHAR(40) AS cell_role,
    NULL::INT AS sort_order
  WHERE wp.generated_from_memory_id IS NOT NULL
    AND NOT EXISTS (
      SELECT 1
      FROM memory_scene_cell direct_scene_cell
      WHERE direct_scene_cell.scene_id = wp.generated_from_scene_id
        AND direct_scene_cell.memory_id = wp.generated_from_memory_id
    )

  UNION

  SELECT
    msc.memory_id,
    msc.cell_role,
    msc.sort_order
  FROM memory_scene_cell msc
  WHERE msc.scene_id = wp.generated_from_scene_id
) page_memory ON TRUE
LEFT JOIN memory_item mi ON mi.memory_id = page_memory.memory_id
LEFT JOIN memory_evidence me ON me.memory_id = mi.memory_id
LEFT JOIN source_chunk sc ON sc.chunk_id = me.chunk_id
LEFT JOIN source_document sd ON sd.doc_id = sc.doc_id
WHERE wp.status = 'active'
  AND (sd.doc_id IS NULL OR sd.status = 'active');

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

CREATE OR REPLACE VIEW v_memory_recall_statistics AS
SELECT
  rl.workspace_id,
  memory_ids.memory_id_text::uuid AS memory_id,
  count(*) AS recall_count,
  max(rl.created_at) AS last_recalled_at
FROM recall_log rl
CROSS JOIN LATERAL jsonb_array_elements_text(rl.top_memory_ids_json) AS memory_ids(memory_id_text)
JOIN memory_item mi ON mi.memory_id = memory_ids.memory_id_text::uuid
WHERE mi.workspace_id = rl.workspace_id
GROUP BY rl.workspace_id, memory_ids.memory_id_text;

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
