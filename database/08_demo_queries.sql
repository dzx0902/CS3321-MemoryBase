-- 1. Query active memory
SELECT * FROM v_active_memory LIMIT 20;

-- 2. Query memory with source evidence
SELECT * FROM v_memory_with_source LIMIT 20;

-- 3. Query timeline
SELECT * FROM v_project_timeline ORDER BY event_time DESC LIMIT 20;

-- 4. Query memory statistics
SELECT * FROM v_memory_statistics;

-- 5. Full text search chunks
SELECT doc_id, chunk_no, chunk_text
FROM source_chunk
WHERE search_vector @@ plainto_tsquery('simple', 'MemoryBase');
