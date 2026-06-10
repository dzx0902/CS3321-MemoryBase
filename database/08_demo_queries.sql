-- 1. Query active memory
SELECT memory_id, memory_type, canonical_text, access_level, confidence, importance
FROM v_active_memory
ORDER BY importance DESC, updated_at DESC
LIMIT 20;

-- 2. Query memory with source evidence
SELECT memory_id, canonical_text, evidence_role, source_title, chunk_no, start_line, end_line
FROM v_memory_with_source
ORDER BY source_title, chunk_no
LIMIT 20;

-- 3. Query timeline
SELECT timeline_id, event_time, event_type, title, memory_text, source_title
FROM v_project_timeline
ORDER BY event_time DESC
LIMIT 20;

-- 4. Query memory statistics
SELECT workspace_id, memory_type, status, access_level, memory_count, avg_confidence, avg_importance
FROM v_memory_statistics;

-- 5. Query memory visible to the demo retriever agent
-- v_agent_visible_memory materializes visibility for every agent; callers filter explicitly.
SELECT memory_id, memory_type, canonical_text, access_level, confidence
FROM v_agent_visible_memory
WHERE agent_id = '00000000-0000-0000-0000-000000000301'
ORDER BY importance DESC, updated_at DESC
LIMIT 20;

-- 6. Query conflict memory pairs
SELECT conflict_id, conflict_type, status AS conflict_status, left_memory_text, right_memory_text
FROM v_conflict_memory
ORDER BY created_at DESC
LIMIT 20;

-- 7. Query wiki page provenance
SELECT page_slug, page_title, memory_id, source_title, chunk_no, start_line, end_line
FROM v_wiki_page_sources
ORDER BY page_slug, chunk_no
LIMIT 20;

-- 8. Full text search chunks
SELECT doc_id, chunk_no, chunk_text
FROM source_chunk
WHERE search_vector @@ plainto_tsquery('simple', 'MemoryBase');

-- 9. Query memories grouped by the topic decision scene
SELECT
  ms.title AS scene_title,
  msc.cell_role,
  msc.sort_order,
  mi.memory_type,
  mi.canonical_text,
  msc.note
FROM memory_scene ms
JOIN memory_scene_cell msc ON msc.scene_id = ms.scene_id
JOIN memory_item mi ON mi.memory_id = msc.memory_id
WHERE ms.scene_slug = 'topic-decision'
ORDER BY msc.sort_order ASC;

-- 10. Verify seeded Chinese / mixed-language search text is ready for FTS
SELECT memory_id, memory_type, search_text_zh
FROM memory_item
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
  AND search_text_zh IS NOT NULL
ORDER BY importance DESC, updated_at DESC
LIMIT 10;

-- 11. Inspect recent recall logs and their context-pack metadata
SELECT
  recall_id,
  query_text,
  result_count,
  top_memory_ids_json,
  context_pack_json -> 'filters' AS filters,
  created_at
FROM recall_log
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
ORDER BY created_at DESC
LIMIT 10;

-- 12. Review memory lifecycle audit entries with before/after JSON
SELECT
  audit_id,
  action_type,
  target_type,
  target_id,
  before_json,
  after_json,
  created_at
FROM audit_log
WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
  AND target_type IN ('memory_item', 'conflict_record', 'forget_request')
ORDER BY created_at DESC
LIMIT 10;

-- 13. Check forget governance requests and target state without hard deletion
SELECT
  fr.request_id,
  fr.target_type,
  fr.target_id,
  fr.status AS request_status,
  mi.status AS memory_status,
  fr.requested_at,
  fr.resolved_at
FROM forget_request fr
LEFT JOIN memory_item mi
  ON fr.target_type = 'memory_item'
 AND fr.target_id = mi.memory_id
WHERE fr.workspace_id = '00000000-0000-0000-0000-000000000201'
ORDER BY fr.requested_at DESC
LIMIT 10;
