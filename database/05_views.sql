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
