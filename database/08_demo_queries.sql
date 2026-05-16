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

-- 5. Query agent-visible memory after the app sets app.agent_id
SELECT set_config('app.agent_id', '00000000-0000-0000-0000-000000000301', false);

SELECT memory_id, memory_type, canonical_text, access_level, confidence
FROM v_agent_visible_memory
ORDER BY importance DESC, updated_at DESC
LIMIT 20;

-- 6. Query conflict memory pairs
SELECT conflict_id, conflict_type, conflict_status, left_memory_text, right_memory_text
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
