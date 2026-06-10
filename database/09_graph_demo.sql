-- Optional curated graph demo seed.
-- Run after 07_seed.sql when you want a cleaner graph visualization example.

-- Remove the optional graph workspace before re-inserting fixed IDs. This keeps
-- the file re-runnable without touching the main cs3321-demo workspace.
DELETE FROM workspace WHERE workspace_id = '00000000-0000-0000-0000-000000002201';
DELETE FROM user_account
WHERE user_id IN (
  '00000000-0000-0000-0000-000000002101',
  '00000000-0000-0000-0000-000000002102'
);

-- Graph demo uses a separate workspace so screenshots can show a small clean
-- provenance graph instead of the denser main course seed.
INSERT INTO user_account(user_id, username, display_name, email, role_hint)
VALUES
  ('00000000-0000-0000-0000-000000002101', 'graph-alice', 'Graph Demo Alice', 'graph-alice@example.com', 'admin'),
  ('00000000-0000-0000-0000-000000002102', 'graph-bob', 'Graph Demo Bob', 'graph-bob@example.com', 'member');

INSERT INTO workspace(workspace_id, slug, name, description, scope_type, owner_user_id)
VALUES (
  '00000000-0000-0000-0000-000000002201',
  'graph-demo',
  'Graph Demo: Project Knowledge Map',
  'Curated workspace designed to show a clean knowledge graph story.',
  'project',
  '00000000-0000-0000-0000-000000002101'
);

INSERT INTO agent(agent_id, workspace_id, name, agent_type, status, owner_user_id)
VALUES (
  '00000000-0000-0000-0000-000000002301',
  '00000000-0000-0000-0000-000000002201',
  'graph-demo-agent',
  'retriever',
  'active',
  '00000000-0000-0000-0000-000000002101'
);

INSERT INTO workspace_member(workspace_id, principal_type, principal_id, member_role)
VALUES
  ('00000000-0000-0000-0000-000000002201', 'user', '00000000-0000-0000-0000-000000002101', 'owner'),
  ('00000000-0000-0000-0000-000000002201', 'user', '00000000-0000-0000-0000-000000002102', 'editor'),
  ('00000000-0000-0000-0000-000000002201', 'agent', '00000000-0000-0000-0000-000000002301', 'agent');

-- Three source documents form the graph story: topic pivot, architecture split,
-- and governance. The downstream chunks/memories/entities mirror these themes.
INSERT INTO source_document(
  doc_id, workspace_id, doc_type, title, source_path, raw_text, checksum, imported_by_user_id, imported_at
)
VALUES
  (
    '00000000-0000-0000-0000-000000002501',
    '00000000-0000-0000-0000-000000002201',
    'meeting',
    'Graph Demo 01: Topic Pivot',
    'data/raw_sources/graph_demo/topic_pivot.md',
    'The team rejected the cafeteria ordering topic because it mostly demonstrated CRUD. MemoryBase was selected because it creates a richer database story: source chunks, evidence, revisions, policies, audit logs, wiki projection, and graph exploration.',
    'graph-demo-topic-pivot',
    '00000000-0000-0000-0000-000000002101',
    '2026-04-01 09:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000002502',
    '00000000-0000-0000-0000-000000002201',
    'meeting',
    'Graph Demo 02: Architecture Chain',
    'data/raw_sources/graph_demo/architecture_chain.md',
    'PostgreSQL remains the source of truth. Neo4j is introduced as a relationship index for graph exploration. Memories keep provenance by linking back to evidence chunks, and wiki pages derive from scenes or important memories.',
    'graph-demo-architecture-chain',
    '00000000-0000-0000-0000-000000002101',
    '2026-04-03 09:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000002503',
    '00000000-0000-0000-0000-000000002201',
    'meeting',
    'Graph Demo 03: Governance Story',
    'data/raw_sources/graph_demo/governance_story.md',
    'Access policies decide what an agent can see. Audit logs explain who changed a memory and why. Wiki provenance lets a reader trace a page back to memories, evidence chunks, and original source documents.',
    'graph-demo-governance-story',
    '00000000-0000-0000-0000-000000002102',
    '2026-04-05 09:00:00+00'
  );

-- Chunks are deliberately short so Graph Explorer node tooltips and evidence
-- edges remain readable in screenshots.
INSERT INTO source_chunk(chunk_id, doc_id, chunk_no, chunk_text, start_line, end_line, token_count)
VALUES
  ('00000000-0000-0000-0000-000000002601', '00000000-0000-0000-0000-000000002501', 1, 'The team rejected the cafeteria ordering topic because it mostly demonstrated CRUD.', 4, 4, 12),
  ('00000000-0000-0000-0000-000000002602', '00000000-0000-0000-0000-000000002501', 2, 'MemoryBase creates a richer database story: source chunks, evidence, revisions, policies, audit logs, wiki projection, and graph exploration.', 6, 6, 20),
  ('00000000-0000-0000-0000-000000002603', '00000000-0000-0000-0000-000000002502', 1, 'PostgreSQL remains the source of truth.', 4, 4, 6),
  ('00000000-0000-0000-0000-000000002604', '00000000-0000-0000-0000-000000002502', 2, 'Neo4j is introduced as a relationship index for graph exploration.', 6, 6, 10),
  ('00000000-0000-0000-0000-000000002605', '00000000-0000-0000-0000-000000002502', 3, 'Memories keep provenance by linking back to evidence chunks.', 8, 8, 9),
  ('00000000-0000-0000-0000-000000002606', '00000000-0000-0000-0000-000000002502', 4, 'Wiki pages derive from scenes or important memories.', 10, 10, 8),
  ('00000000-0000-0000-0000-000000002607', '00000000-0000-0000-0000-000000002503', 1, 'Access policies decide what an agent can see.', 4, 4, 8),
  ('00000000-0000-0000-0000-000000002608', '00000000-0000-0000-0000-000000002503', 2, 'Wiki provenance lets a reader trace a page back to memories, evidence chunks, and original source documents.', 8, 8, 16);

SELECT set_config('app.actor_type', 'system', false);
SELECT set_config('app.actor_id', '', false);
SELECT set_config('app.revision_reason', 'graph demo seed', false);

-- Memory inserts go through the normal trigger path, creating revision/audit
-- records while also providing the Memory nodes used by the graph preview.
INSERT INTO memory_item(
  memory_id, workspace_id, created_from_doc_id, memory_type, canonical_text, summary,
  confidence, importance, status, access_level, owner_user_id, valid_from
)
VALUES
  ('00000000-0000-0000-0000-000000002701', '00000000-0000-0000-0000-000000002201', '00000000-0000-0000-0000-000000002501', 'decision', 'The cafeteria ordering topic was rejected because it mostly demonstrated CRUD.', 'Rejected CRUD-heavy topic', 0.960, 5, 'active', 'project', '00000000-0000-0000-0000-000000002101', '2026-04-01 09:10:00+00'),
  ('00000000-0000-0000-0000-000000002702', '00000000-0000-0000-0000-000000002201', '00000000-0000-0000-0000-000000002501', 'decision', 'MemoryBase was selected because it demonstrates provenance, governance, and graph exploration.', 'Selected MemoryBase', 0.970, 5, 'active', 'project', '00000000-0000-0000-0000-000000002101', '2026-04-01 09:12:00+00'),
  ('00000000-0000-0000-0000-000000002703', '00000000-0000-0000-0000-000000002201', '00000000-0000-0000-0000-000000002502', 'semantic', 'PostgreSQL remains the authoritative source of business data.', 'PostgreSQL as source of truth', 0.950, 5, 'active', 'project', '00000000-0000-0000-0000-000000002101', '2026-04-03 09:10:00+00'),
  ('00000000-0000-0000-0000-000000002704', '00000000-0000-0000-0000-000000002201', '00000000-0000-0000-0000-000000002502', 'semantic', 'Neo4j is used as a relationship index for graph exploration, not as the source of truth.', 'Neo4j as graph index', 0.940, 5, 'active', 'project', '00000000-0000-0000-0000-000000002102', '2026-04-03 09:12:00+00'),
  ('00000000-0000-0000-0000-000000002705', '00000000-0000-0000-0000-000000002201', '00000000-0000-0000-0000-000000002502', 'procedural', 'Memory provenance flows from wiki page to scene, memory, evidence chunk, and source document.', 'Provenance chain', 0.930, 5, 'active', 'project', '00000000-0000-0000-0000-000000002102', '2026-04-03 09:14:00+00'),
  ('00000000-0000-0000-0000-000000002706', '00000000-0000-0000-0000-000000002201', '00000000-0000-0000-0000-000000002503', 'semantic', 'Access policies decide which memories an agent can see.', 'Agent visibility policy', 0.910, 4, 'active', 'project', '00000000-0000-0000-0000-000000002102', '2026-04-05 09:10:00+00'),
  ('00000000-0000-0000-0000-000000002707', '00000000-0000-0000-0000-000000002201', '00000000-0000-0000-0000-000000002503', 'semantic', 'Wiki provenance lets readers trace generated pages back to memories and evidence.', 'Wiki provenance', 0.930, 5, 'active', 'project', '00000000-0000-0000-0000-000000002101', '2026-04-05 09:12:00+00');

-- Evidence creates SUPPORTED_BY edges in graph_service.py.
INSERT INTO memory_evidence(memory_id, chunk_id, evidence_role, weight, note)
VALUES
  ('00000000-0000-0000-0000-000000002701', '00000000-0000-0000-0000-000000002601', 'supports', 1.000, 'Topic rejection reason.'),
  ('00000000-0000-0000-0000-000000002702', '00000000-0000-0000-0000-000000002602', 'supports', 1.000, 'Positive selection reason.'),
  ('00000000-0000-0000-0000-000000002703', '00000000-0000-0000-0000-000000002603', 'supports', 1.000, 'Authoritative data source.'),
  ('00000000-0000-0000-0000-000000002704', '00000000-0000-0000-0000-000000002604', 'supports', 1.000, 'Neo4j role.'),
  ('00000000-0000-0000-0000-000000002705', '00000000-0000-0000-0000-000000002605', 'supports', 0.900, 'Memory evidence path.'),
  ('00000000-0000-0000-0000-000000002705', '00000000-0000-0000-0000-000000002606', 'context', 0.800, 'Wiki derivation path.'),
  ('00000000-0000-0000-0000-000000002706', '00000000-0000-0000-0000-000000002607', 'supports', 1.000, 'Policy visibility note.'),
  ('00000000-0000-0000-0000-000000002707', '00000000-0000-0000-0000-000000002608', 'supports', 1.000, 'Traceability note.');

-- Entities and memory_entity rows create MENTIONS edges, making the graph more
-- informative than a source->chunk->memory chain alone.
INSERT INTO entity(entity_id, workspace_id, canonical_name, entity_type, description)
VALUES
  ('00000000-0000-0000-0000-000000002801', '00000000-0000-0000-0000-000000002201', 'Cafeteria Ordering System', 'project', 'Rejected CRUD-heavy project idea.'),
  ('00000000-0000-0000-0000-000000002802', '00000000-0000-0000-0000-000000002201', 'MemoryBase', 'project', 'Selected long-term memory system.'),
  ('00000000-0000-0000-0000-000000002803', '00000000-0000-0000-0000-000000002201', 'PostgreSQL', 'concept', 'Authoritative relational database.'),
  ('00000000-0000-0000-0000-000000002804', '00000000-0000-0000-0000-000000002201', 'Neo4j', 'concept', 'Graph database used for relationship exploration.'),
  ('00000000-0000-0000-0000-000000002805', '00000000-0000-0000-0000-000000002201', 'Wiki Provenance', 'concept', 'Traceability from wiki pages back to evidence and sources.');

INSERT INTO memory_entity(memory_id, entity_id, workspace_id, relation_role)
VALUES
  ('00000000-0000-0000-0000-000000002701', '00000000-0000-0000-0000-000000002801', '00000000-0000-0000-0000-000000002201', 'about'),
  ('00000000-0000-0000-0000-000000002702', '00000000-0000-0000-0000-000000002802', '00000000-0000-0000-0000-000000002201', 'about'),
  ('00000000-0000-0000-0000-000000002703', '00000000-0000-0000-0000-000000002803', '00000000-0000-0000-0000-000000002201', 'about'),
  ('00000000-0000-0000-0000-000000002704', '00000000-0000-0000-0000-000000002804', '00000000-0000-0000-0000-000000002201', 'about'),
  ('00000000-0000-0000-0000-000000002707', '00000000-0000-0000-0000-000000002805', '00000000-0000-0000-0000-000000002201', 'about');

-- Scenes group memories into story units. Graph Explorer uses them to show that
-- MemoryBase can organize memories into narrative views, not just flat search hits.
INSERT INTO memory_scene(scene_id, workspace_id, scene_slug, title, summary)
VALUES
  ('00000000-0000-0000-0000-000000002901', '00000000-0000-0000-0000-000000002201', 'topic-pivot', 'Topic Pivot', 'Why the project moved from cafeteria ordering to MemoryBase.'),
  ('00000000-0000-0000-0000-000000002902', '00000000-0000-0000-0000-000000002201', 'architecture-chain', 'Architecture Chain', 'How PostgreSQL and Neo4j divide responsibilities.'),
  ('00000000-0000-0000-0000-000000002903', '00000000-0000-0000-0000-000000002201', 'governance-story', 'Governance Story', 'How policy and provenance support trustworthy memory.');

INSERT INTO memory_scene_cell(scene_id, memory_id, workspace_id, cell_role, sort_order, note)
VALUES
  ('00000000-0000-0000-0000-000000002901', '00000000-0000-0000-0000-000000002701', '00000000-0000-0000-0000-000000002201', 'background', 10, 'Rejected option.'),
  ('00000000-0000-0000-0000-000000002901', '00000000-0000-0000-0000-000000002702', '00000000-0000-0000-0000-000000002201', 'decision', 20, 'Selected option.'),
  ('00000000-0000-0000-0000-000000002902', '00000000-0000-0000-0000-000000002703', '00000000-0000-0000-0000-000000002201', 'decision', 10, 'Relational source of truth.'),
  ('00000000-0000-0000-0000-000000002902', '00000000-0000-0000-0000-000000002704', '00000000-0000-0000-0000-000000002201', 'support', 20, 'Graph exploration layer.'),
  ('00000000-0000-0000-0000-000000002902', '00000000-0000-0000-0000-000000002705', '00000000-0000-0000-0000-000000002201', 'outcome', 30, 'Provenance path.'),
  ('00000000-0000-0000-0000-000000002903', '00000000-0000-0000-0000-000000002706', '00000000-0000-0000-0000-000000002201', 'support', 10, 'Agent visibility.'),
  ('00000000-0000-0000-0000-000000002903', '00000000-0000-0000-0000-000000002707', '00000000-0000-0000-0000-000000002201', 'outcome', 20, 'Trustworthy wiki output.');

-- Wiki pages are derived from scenes/memories, producing DERIVED_FROM edges in
-- the workspace graph and demonstrating readable projections of database memory.
INSERT INTO wiki_page(page_id, workspace_id, page_slug, page_type, title, generated_from_scene_id, generated_from_memory_id, needs_rebuild)
VALUES
  ('00000000-0000-0000-0000-000000003301', '00000000-0000-0000-0000-000000002201', 'project-pivot-story', 'synthesis', 'Project Pivot Story', '00000000-0000-0000-0000-000000002901', '00000000-0000-0000-0000-000000002702', false),
  ('00000000-0000-0000-0000-000000003302', '00000000-0000-0000-0000-000000002201', 'architecture-map', 'report', 'Architecture Map', '00000000-0000-0000-0000-000000002902', '00000000-0000-0000-0000-000000002704', false),
  ('00000000-0000-0000-0000-000000003303', '00000000-0000-0000-0000-000000002201', 'governance-demo', 'handbook', 'Governance Demo', '00000000-0000-0000-0000-000000002903', '00000000-0000-0000-0000-000000002707', false);

INSERT INTO wiki_page_revision(page_id, revision_no, frontmatter_json, body_markdown, generated_by, created_at)
VALUES
  ('00000000-0000-0000-0000-000000003301', 1, '{"slug":"project-pivot-story","source":"graph-demo"}'::jsonb, '# Project Pivot Story\n\nThe team rejected a CRUD-heavy cafeteria project and selected MemoryBase for a richer database demonstration.', 'exporter', '2026-04-06 10:00:00+00'),
  ('00000000-0000-0000-0000-000000003302', 1, '{"slug":"architecture-map","source":"graph-demo"}'::jsonb, '# Architecture Map\n\nPostgreSQL remains authoritative while Neo4j provides relationship exploration.', 'exporter', '2026-04-06 10:05:00+00'),
  ('00000000-0000-0000-0000-000000003303', 1, '{"slug":"governance-demo","source":"graph-demo"}'::jsonb, '# Governance Demo\n\nAccess policy and wiki provenance make generated memory outputs inspectable.', 'exporter', '2026-04-06 10:10:00+00');

SELECT set_config('app.actor_type', '', false);
SELECT set_config('app.actor_id', '', false);
SELECT set_config('app.revision_reason', '', false);
