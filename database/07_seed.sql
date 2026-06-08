-- Demo seed data for MemoryBase.
-- This script resets demo tables so it can be re-run in a local/course demo database.
-- Do not run it against a database that already contains non-demo data.

TRUNCATE TABLE
  audit_log,
  forget_request,
  conflict_record,
  access_policy,
  recall_log,
  timeline_entry,
  wiki_page_revision,
  wiki_page,
  memory_scene_cell,
  memory_scene,
  memory_entity,
  entity,
  memory_evidence,
  memory_revision,
  memory_item,
  source_chunk,
  source_document,
  message,
  agent_session,
  workspace_member,
  agent,
  workspace,
  user_account
CASCADE;

-- Users, workspace, agent, membership, and session create a closed demo tenant.
-- Fixed UUIDs make frontend constants, API examples, and SQL screenshots repeatable.
INSERT INTO user_account(user_id, username, display_name, email, role_hint)
VALUES
  ('00000000-0000-0000-0000-000000000101', 'alice', 'Alice Zhang', 'alice@example.com', 'admin'),
  ('00000000-0000-0000-0000-000000000102', 'bob', 'Bob Chen', 'bob@example.com', 'member'),
  ('00000000-0000-0000-0000-000000000103', 'carol', 'Carol Lin', 'carol@example.com', 'member'),
  ('00000000-0000-0000-0000-000000000104', 'guest', 'Demo Guest', 'guest@example.com', 'guest');

INSERT INTO workspace(workspace_id, slug, name, description, scope_type, owner_user_id)
VALUES (
  '00000000-0000-0000-0000-000000000201',
  'cs3321-demo',
  'MemoryBase Course Demo',
  'Closed demo workspace for the CS3321 MemoryBase project.',
  'project',
  '00000000-0000-0000-0000-000000000101'
);

INSERT INTO agent(agent_id, workspace_id, name, agent_type, status, owner_user_id)
VALUES (
  '00000000-0000-0000-0000-000000000301',
  '00000000-0000-0000-0000-000000000201',
  'demo-retriever',
  'retriever',
  'active',
  '00000000-0000-0000-0000-000000000101'
);

INSERT INTO workspace_member(workspace_id, principal_type, principal_id, member_role)
VALUES
  ('00000000-0000-0000-0000-000000000201', 'user', '00000000-0000-0000-0000-000000000101', 'owner'),
  ('00000000-0000-0000-0000-000000000201', 'user', '00000000-0000-0000-0000-000000000102', 'editor'),
  ('00000000-0000-0000-0000-000000000201', 'user', '00000000-0000-0000-0000-000000000103', 'editor'),
  ('00000000-0000-0000-0000-000000000201', 'user', '00000000-0000-0000-0000-000000000104', 'viewer'),
  ('00000000-0000-0000-0000-000000000201', 'agent', '00000000-0000-0000-0000-000000000301', 'agent');

-- The session/message rows show that MemoryBase can preserve runtime dialogue
-- without forcing every message to become a long-term memory.
INSERT INTO agent_session(session_id, workspace_id, agent_id, started_by_user_id, title, channel, started_at)
VALUES (
  '00000000-0000-0000-0000-000000000401',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000301',
  '00000000-0000-0000-0000-000000000101',
  'MemoryBase planning discussions',
  'meeting',
  '2026-03-02 09:00:00+00'
);

INSERT INTO message(message_id, session_id, sender_type, sender_id, role, content, created_at)
VALUES
  (
    '00000000-0000-0000-0000-000000000411',
    '00000000-0000-0000-0000-000000000401',
    'user',
    '00000000-0000-0000-0000-000000000101',
    'user',
    'We should choose a project that demonstrates database modeling, not just CRUD.',
    '2026-03-02 09:05:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000412',
    '00000000-0000-0000-0000-000000000401',
    'agent',
    '00000000-0000-0000-0000-000000000301',
    'assistant',
    'MemoryBase can demonstrate source chunks, evidence, revisions, audit logs, policies, views, and triggers.',
    '2026-03-02 09:06:00+00'
  );

-- Six source documents simulate a small project history. They are intentionally
-- compact so recall, evidence, wiki export, and SQL screenshots stay explainable.
INSERT INTO source_document(
  doc_id, workspace_id, session_id, doc_type, title, source_path, raw_text, checksum,
  imported_by_user_id, imported_at
)
VALUES
  (
    '00000000-0000-0000-0000-000000000501',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000401',
    'meeting',
    'Discussion 01: Project Pivot',
    'data/raw_sources/demo_workspace/discussion_01_project_pivot.md',
    'The team first considered a campus cafeteria ordering system. The idea was familiar, but it did not show enough database depth for the course. We decided to abandon the cafeteria system because most of its value would be CRUD screens, order status fields, and simple reports. The MemoryBase direction gives us stronger database requirements: source documents, chunks, memory evidence, revisions, audit logs, access policy, recall logs, conflicts, and wiki projection.',
    'demo-discussion-01',
    '00000000-0000-0000-0000-000000000101',
    '2026-03-02 10:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000502',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000401',
    'meeting',
    'Discussion 02: Architecture',
    'data/raw_sources/demo_workspace/discussion_02_architecture.md',
    'MemoryBase uses a file-database dual state model. Human readable Markdown remains useful for review, while PostgreSQL provides query, constraints, views, triggers, and auditability. The core data flow is SourceDocument to SourceChunk to MemoryItem to MemoryEvidence. Revision and AuditLog record changes after memory creation.',
    'demo-discussion-02',
    '00000000-0000-0000-0000-000000000101',
    '2026-03-06 10:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000503',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000401',
    'meeting',
    'Discussion 03: Schema',
    'data/raw_sources/demo_workspace/discussion_03_schema.md',
    'The schema needs clear primary keys, foreign keys, unique constraints, check constraints, indexes, views, and triggers. SourceDocument stores imported files and checksum. SourceChunk stores chunk text, line range, and search vector. MemoryEvidence connects MemoryItem and SourceChunk as a many-to-many relationship.',
    'demo-discussion-03',
    '00000000-0000-0000-0000-000000000102',
    '2026-03-10 10:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000504',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000401',
    'meeting',
    'Discussion 04: Policy and Recall',
    'data/raw_sources/demo_workspace/discussion_04_policy_recall.md',
    'Recall should return memory items with supporting evidence and source chunks. AccessPolicy is needed because AI agents should not read every memory. Project level memory can be visible to a retriever agent, but private memory must stay hidden unless explicitly allowed. RecallLog records query text, filters, result count, top memory IDs, and context pack JSON.',
    'demo-discussion-04',
    '00000000-0000-0000-0000-000000000102',
    '2026-03-15 10:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000505',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000401',
    'meeting',
    'Discussion 05: Wiki and Timeline',
    'data/raw_sources/demo_workspace/discussion_05_wiki_timeline.md',
    'The exported Wiki should make database memory readable by humans. Each WikiPage needs revisions so repeated export can be audited. Wiki pages should include source provenance. TimelineEntry is useful for showing how the project evolved from topic selection to schema design, recall, governance, and final demo.',
    'demo-discussion-05',
    '00000000-0000-0000-0000-000000000103',
    '2026-03-20 10:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000506',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000401',
    'meeting',
    'Discussion 06: Demo Plan',
    'data/raw_sources/demo_workspace/discussion_06_demo_plan.md',
    'The demo must run in five to eight minutes. It should show source import, chunk line numbers, memory evidence, recall, revision, audit, policy filtering, conflict handling, wiki export, and SQL queries. The key recall question is why did we abandon the campus cafeteria system. The expected answer is that the cafeteria system was too CRUD-heavy and did not demonstrate enough database features.',
    'demo-discussion-06',
    '00000000-0000-0000-0000-000000000103',
    '2026-03-25 10:00:00+00'
  );

-- Source chunks preserve line ranges and become the evidence targets for memory
-- items. search_text_zh is backfilled after seed by backend/scripts/backfill_search_terms.py.
INSERT INTO source_chunk(chunk_id, doc_id, chunk_no, chunk_text, start_line, end_line, token_count)
VALUES
  ('00000000-0000-0000-0000-000000000601', '00000000-0000-0000-0000-000000000501', 1, 'The team first considered a campus cafeteria ordering system. The idea was familiar, but it did not show enough database depth for the course.', 6, 8, 24),
  ('00000000-0000-0000-0000-000000000602', '00000000-0000-0000-0000-000000000501', 2, 'We decided to abandon the cafeteria system because most of its value would be CRUD screens, order status fields, and simple reports.', 10, 10, 22),
  ('00000000-0000-0000-0000-000000000603', '00000000-0000-0000-0000-000000000501', 3, 'The MemoryBase direction gives us stronger database requirements: source documents, chunks, memory evidence, revisions, audit logs, access policy, recall logs, conflicts, and wiki projection.', 12, 12, 24),
  ('00000000-0000-0000-0000-000000000604', '00000000-0000-0000-0000-000000000501', 4, 'The team agreed that the demo question why did we abandon the campus cafeteria system must be answerable from imported discussion records.', 14, 14, 22),
  ('00000000-0000-0000-0000-000000000605', '00000000-0000-0000-0000-000000000502', 1, 'MemoryBase uses a file-database dual state model. Human readable Markdown remains useful for review, while PostgreSQL provides query, constraints, views, triggers, and auditability.', 6, 6, 24),
  ('00000000-0000-0000-0000-000000000606', '00000000-0000-0000-0000-000000000502', 2, 'The core data flow is SourceDocument to SourceChunk to MemoryItem to MemoryEvidence. Revision and AuditLog record changes after memory creation.', 8, 8, 18),
  ('00000000-0000-0000-0000-000000000607', '00000000-0000-0000-0000-000000000502', 3, 'The backend should expose import, source, memory, recall, policy, audit, and wiki export APIs.', 10, 10, 14),
  ('00000000-0000-0000-0000-000000000608', '00000000-0000-0000-0000-000000000503', 1, 'The schema needs clear primary keys, foreign keys, unique constraints, check constraints, indexes, views, and triggers.', 6, 6, 16),
  ('00000000-0000-0000-0000-000000000609', '00000000-0000-0000-0000-000000000503', 2, 'SourceDocument stores imported files and checksum. SourceChunk stores chunk text, line range, and search vector.', 8, 8, 14),
  ('00000000-0000-0000-0000-000000000610', '00000000-0000-0000-0000-000000000503', 3, 'MemoryEvidence connects MemoryItem and SourceChunk. This relationship is many-to-many because one memory can cite several chunks and one chunk can support several memories.', 10, 10, 22),
  ('00000000-0000-0000-0000-000000000611', '00000000-0000-0000-0000-000000000503', 4, 'AuditLog records before and after JSON. MemoryRevision stores immutable memory versions.', 12, 12, 11),
  ('00000000-0000-0000-0000-000000000612', '00000000-0000-0000-0000-000000000504', 1, 'Recall should return memory items with supporting evidence and source chunks. The first version can use keyword search and PostgreSQL full text search.', 6, 6, 21),
  ('00000000-0000-0000-0000-000000000613', '00000000-0000-0000-0000-000000000504', 2, 'AccessPolicy is needed because AI agents should not read every memory. Project level memory can be visible to a retriever agent, but private memory must stay hidden unless explicitly allowed.', 8, 8, 27),
  ('00000000-0000-0000-0000-000000000614', '00000000-0000-0000-0000-000000000504', 3, 'RecallLog records query text, filters, result count, top memory IDs, and context pack JSON.', 12, 12, 13),
  ('00000000-0000-0000-0000-000000000615', '00000000-0000-0000-0000-000000000505', 1, 'The exported Wiki should make database memory readable by humans. Each WikiPage needs revisions so repeated export can be audited.', 6, 8, 18),
  ('00000000-0000-0000-0000-000000000616', '00000000-0000-0000-0000-000000000505', 2, 'Wiki pages should include source provenance. A reader should be able to trace a wiki statement back to MemoryItem, MemoryEvidence, SourceChunk, and SourceDocument.', 10, 10, 22),
  ('00000000-0000-0000-0000-000000000617', '00000000-0000-0000-0000-000000000505', 3, 'TimelineEntry is useful for showing how the project evolved from topic selection to schema design, recall, governance, and final demo.', 12, 12, 20),
  ('00000000-0000-0000-0000-000000000618', '00000000-0000-0000-0000-000000000506', 1, 'The demo must run in five to eight minutes. It should show source import, chunk line numbers, memory evidence, recall, revision, audit, policy filtering, conflict handling, wiki export, and SQL queries.', 6, 6, 31),
  ('00000000-0000-0000-0000-000000000619', '00000000-0000-0000-0000-000000000506', 2, 'The key recall question is why did we abandon the campus cafeteria system. The expected answer is that the cafeteria system was too CRUD-heavy and did not demonstrate enough database features.', 8, 8, 29),
  ('00000000-0000-0000-0000-000000000620', '00000000-0000-0000-0000-000000000506', 3, 'Include one conflict about whether LLM extraction is required for MVP. The MVP should not depend on LLM automatic extraction.', 14, 14, 19);

SELECT set_config('app.actor_type', 'system', false);
SELECT set_config('app.actor_id', '', false);
SELECT set_config('app.revision_reason', 'seed import', false);

-- Memory inserts intentionally go through the normal trigger path. The triggers
-- create memory_revision and audit_log rows, proving the lifecycle logic in seed data.
INSERT INTO memory_item(
  memory_id, workspace_id, created_from_doc_id, memory_type, canonical_text, summary,
  confidence, importance, status, access_level, owner_user_id, owner_agent_id, valid_from
)
VALUES
  ('00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000501', 'decision', 'The team abandoned the campus cafeteria system because it was too CRUD-heavy and did not demonstrate enough database depth.', 'Reason for abandoning the cafeteria topic.', 0.950, 5, 'active', 'project', '00000000-0000-0000-0000-000000000101', NULL, '2026-03-02 10:15:00+00'),
  ('00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000501', 'decision', 'MemoryBase was selected because it demonstrates source chunks, evidence, revisions, audit logs, policies, recall logs, conflicts, and wiki projection.', 'Reason for choosing MemoryBase.', 0.960, 5, 'active', 'project', '00000000-0000-0000-0000-000000000101', NULL, '2026-03-02 10:20:00+00'),
  ('00000000-0000-0000-0000-000000000703', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000501', 'semantic', 'The recall demo must answer why the campus cafeteria system was abandoned.', 'Required demo question.', 0.900, 4, 'active', 'project', '00000000-0000-0000-0000-000000000102', NULL, '2026-03-02 10:25:00+00'),
  ('00000000-0000-0000-0000-000000000704', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000502', 'semantic', 'MemoryBase keeps both human-readable Markdown and database records as a file-database dual state system.', 'File and database dual state.', 0.880, 4, 'active', 'project', '00000000-0000-0000-0000-000000000102', NULL, '2026-03-06 10:10:00+00'),
  ('00000000-0000-0000-0000-000000000705', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000502', 'procedural', 'The core data flow is SourceDocument to SourceChunk to MemoryItem to MemoryEvidence.', 'Core data flow.', 0.920, 5, 'active', 'project', '00000000-0000-0000-0000-000000000103', NULL, '2026-03-06 10:15:00+00'),
  ('00000000-0000-0000-0000-000000000706', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000502', 'task', 'The backend should expose import, source, memory, recall, policy, audit, and wiki export APIs.', 'Backend API scope.', 0.840, 3, 'active', 'project', '00000000-0000-0000-0000-000000000103', NULL, '2026-03-06 10:20:00+00'),
  ('00000000-0000-0000-0000-000000000707', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000503', 'semantic', 'The schema must demonstrate primary keys, foreign keys, unique constraints, check constraints, indexes, views, and triggers.', 'Database course requirements.', 0.930, 5, 'active', 'project', '00000000-0000-0000-0000-000000000101', NULL, '2026-03-10 10:10:00+00'),
  ('00000000-0000-0000-0000-000000000708', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000503', 'semantic', 'SourceDocument stores imported files and checksums; SourceChunk stores chunk text, line ranges, token counts, and search vectors.', 'Source and chunk responsibilities.', 0.900, 4, 'active', 'project', '00000000-0000-0000-0000-000000000102', NULL, '2026-03-10 10:15:00+00'),
  ('00000000-0000-0000-0000-000000000709', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000503', 'semantic', 'MemoryEvidence is the many-to-many bridge between MemoryItem and SourceChunk.', 'Evidence relationship.', 0.940, 5, 'active', 'project', '00000000-0000-0000-0000-000000000103', NULL, '2026-03-10 10:20:00+00'),
  ('00000000-0000-0000-0000-000000000710', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000503', 'semantic', 'AuditLog stores before and after JSON, while MemoryRevision stores immutable memory versions.', 'Audit and revision responsibility.', 0.910, 4, 'active', 'project', '00000000-0000-0000-0000-000000000101', NULL, '2026-03-10 10:25:00+00'),
  ('00000000-0000-0000-0000-000000000711', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000504', 'procedural', 'Recall should return memory items together with supporting evidence and source chunks.', 'Recall output shape.', 0.890, 4, 'active', 'project', '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000301', '2026-03-15 10:10:00+00'),
  ('00000000-0000-0000-0000-000000000712', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000504', 'semantic', 'The first recall implementation can use keyword search and PostgreSQL full text search.', 'Recall implementation baseline.', 0.840, 3, 'active', 'project', '00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000301', '2026-03-15 10:15:00+00'),
  ('00000000-0000-0000-0000-000000000713', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000504', 'risk', 'Private budget or personal coordination notes must stay hidden from a project-only retriever agent unless explicitly allowed.', 'Private permission rule.', 0.900, 4, 'active', 'private', '00000000-0000-0000-0000-000000000101', NULL, '2026-03-15 10:20:00+00'),
  ('00000000-0000-0000-0000-000000000714', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000504', 'semantic', 'RecallLog records query text, filters, result count, top memory IDs, and context pack JSON.', 'RecallLog content.', 0.870, 3, 'active', 'project', '00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000301', '2026-03-15 10:25:00+00'),
  ('00000000-0000-0000-0000-000000000715', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000505', 'semantic', 'Wiki export makes database memory readable as Markdown and WikiPageRevision audits repeated exports.', 'Wiki export purpose.', 0.900, 4, 'active', 'project', '00000000-0000-0000-0000-000000000101', NULL, '2026-03-20 10:10:00+00'),
  ('00000000-0000-0000-0000-000000000716', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000505', 'semantic', 'Wiki statements should trace back to MemoryItem, MemoryEvidence, SourceChunk, and SourceDocument.', 'Wiki provenance chain.', 0.930, 4, 'active', 'project', '00000000-0000-0000-0000-000000000102', NULL, '2026-03-20 10:15:00+00'),
  ('00000000-0000-0000-0000-000000000717', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000505', 'semantic', 'TimelineEntry shows how the project evolved from topic selection to schema design, recall, governance, and final demo.', 'Timeline value.', 0.850, 3, 'active', 'project', '00000000-0000-0000-0000-000000000103', NULL, '2026-03-20 10:20:00+00'),
  ('00000000-0000-0000-0000-000000000718', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000506', 'task', 'The five to eight minute demo should show source import, chunk line numbers, memory evidence, recall, revision, audit, policy filtering, conflict handling, wiki export, and SQL queries.', 'Demo checklist.', 0.920, 5, 'active', 'project', '00000000-0000-0000-0000-000000000101', NULL, '2026-03-25 10:10:00+00'),
  ('00000000-0000-0000-0000-000000000719', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000506', 'decision', 'The demo answer to the cafeteria question is that the cafeteria system was too CRUD-heavy and did not demonstrate enough database features.', 'Demo recall answer.', 0.970, 5, 'active', 'project', '00000000-0000-0000-0000-000000000102', NULL, '2026-03-25 10:15:00+00'),
  ('00000000-0000-0000-0000-000000000720', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000506', 'decision', 'LLM automatic extraction is useful later but is not required for the MVP demo.', 'LLM extraction is future work.', 0.880, 4, 'active', 'project', '00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000301', '2026-03-25 10:20:00+00');

-- Evidence rows are the core provenance bridge: every seeded memory used in the
-- demo can be traced back to a concrete source chunk and evidence role.
INSERT INTO memory_evidence(memory_id, chunk_id, evidence_role, weight, note)
VALUES
  ('00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000602', 'supports', 1.000, 'Direct reason for abandoning cafeteria system.'),
  ('00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000603', 'supports', 1.000, 'Direct reason for choosing MemoryBase.'),
  ('00000000-0000-0000-0000-000000000703', '00000000-0000-0000-0000-000000000604', 'supports', 0.950, 'Demo question requirement.'),
  ('00000000-0000-0000-0000-000000000704', '00000000-0000-0000-0000-000000000605', 'supports', 1.000, 'Dual state architecture note.'),
  ('00000000-0000-0000-0000-000000000705', '00000000-0000-0000-0000-000000000606', 'supports', 1.000, 'Core data flow note.'),
  ('00000000-0000-0000-0000-000000000706', '00000000-0000-0000-0000-000000000607', 'supports', 0.900, 'Backend API scope.'),
  ('00000000-0000-0000-0000-000000000707', '00000000-0000-0000-0000-000000000608', 'supports', 1.000, 'Database course requirements.'),
  ('00000000-0000-0000-0000-000000000708', '00000000-0000-0000-0000-000000000609', 'supports', 0.950, 'Source and chunk table responsibilities.'),
  ('00000000-0000-0000-0000-000000000709', '00000000-0000-0000-0000-000000000610', 'supports', 1.000, 'Evidence many-to-many relationship.'),
  ('00000000-0000-0000-0000-000000000710', '00000000-0000-0000-0000-000000000611', 'supports', 1.000, 'Revision and audit design.'),
  ('00000000-0000-0000-0000-000000000711', '00000000-0000-0000-0000-000000000612', 'supports', 0.950, 'Recall output shape.'),
  ('00000000-0000-0000-0000-000000000712', '00000000-0000-0000-0000-000000000612', 'context', 0.800, 'Baseline recall method.'),
  ('00000000-0000-0000-0000-000000000713', '00000000-0000-0000-0000-000000000613', 'supports', 1.000, 'Permission filtering note.'),
  ('00000000-0000-0000-0000-000000000714', '00000000-0000-0000-0000-000000000614', 'supports', 0.900, 'RecallLog field list.'),
  ('00000000-0000-0000-0000-000000000715', '00000000-0000-0000-0000-000000000615', 'supports', 0.950, 'Wiki export and revision note.'),
  ('00000000-0000-0000-0000-000000000716', '00000000-0000-0000-0000-000000000616', 'supports', 1.000, 'Wiki provenance chain.'),
  ('00000000-0000-0000-0000-000000000717', '00000000-0000-0000-0000-000000000617', 'supports', 0.900, 'Timeline value note.'),
  ('00000000-0000-0000-0000-000000000718', '00000000-0000-0000-0000-000000000618', 'supports', 1.000, 'Demo checklist.'),
  ('00000000-0000-0000-0000-000000000719', '00000000-0000-0000-0000-000000000619', 'supports', 1.000, 'Expected recall answer.'),
  ('00000000-0000-0000-0000-000000000720', '00000000-0000-0000-0000-000000000620', 'supports', 0.950, 'MVP does not require LLM extraction.');

SELECT set_config('app.revision_reason', 'seed correction', false);

-- These updates are deliberate: they exercise revision/audit triggers so the demo
-- database contains non-trivial memory history, not only initial inserts.
UPDATE memory_item
SET summary = 'Reason cafeteria topic was rejected.'
WHERE memory_id = '00000000-0000-0000-0000-000000000701';

UPDATE memory_item
SET confidence = 0.980
WHERE memory_id = '00000000-0000-0000-0000-000000000702';

UPDATE memory_item
SET importance = 5
WHERE memory_id = '00000000-0000-0000-0000-000000000716';

UPDATE memory_item
SET canonical_text = 'LLM automatic extraction is useful later but is not required for the deterministic MVP demo.'
WHERE memory_id = '00000000-0000-0000-0000-000000000720';

-- This team-level memory demonstrates that visibility is not only public/project;
-- recall without an agent and recall with a configured agent can differ.
UPDATE memory_item
SET access_level = 'team'
WHERE memory_id = '00000000-0000-0000-0000-000000000717';

-- Entity and scene rows provide lightweight semantic organization without turning
-- the project into a full knowledge-graph system.
INSERT INTO entity(entity_id, workspace_id, canonical_name, entity_type, description)
VALUES
  (
    '00000000-0000-0000-0000-000000000801',
    '00000000-0000-0000-0000-000000000201',
    'Campus Cafeteria System',
    'project',
    'The original course project idea that the team rejected as too CRUD-heavy.'
  ),
  (
    '00000000-0000-0000-0000-000000000802',
    '00000000-0000-0000-0000-000000000201',
    'MemoryBase Project',
    'project',
    'The selected file-database dual-state long-term memory system.'
  ),
  (
    '00000000-0000-0000-0000-000000000803',
    '00000000-0000-0000-0000-000000000201',
    'Database Course Requirements',
    'concept',
    'The database modeling, constraints, views, indexes, triggers, and audit capabilities required by the course.'
  );

INSERT INTO memory_entity(memory_id, entity_id, workspace_id, relation_role)
VALUES
  ('00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000801', '00000000-0000-0000-0000-000000000201', 'about'),
  ('00000000-0000-0000-0000-000000000719', '00000000-0000-0000-0000-000000000801', '00000000-0000-0000-0000-000000000201', 'about'),
  ('00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000802', '00000000-0000-0000-0000-000000000201', 'about'),
  ('00000000-0000-0000-0000-000000000705', '00000000-0000-0000-0000-000000000802', '00000000-0000-0000-0000-000000000201', 'related_to'),
  ('00000000-0000-0000-0000-000000000707', '00000000-0000-0000-0000-000000000803', '00000000-0000-0000-0000-000000000201', 'about');

INSERT INTO memory_scene(scene_id, workspace_id, scene_slug, title, summary)
VALUES (
  '00000000-0000-0000-0000-000000000901',
  '00000000-0000-0000-0000-000000000201',
  'topic-decision',
  'Topic Decision',
  'Key memories explaining why the team moved from the campus cafeteria system to MemoryBase.'
);

INSERT INTO memory_scene_cell(scene_id, memory_id, workspace_id, cell_role, sort_order, note)
VALUES
  (
    '00000000-0000-0000-0000-000000000901',
    '00000000-0000-0000-0000-000000000701',
    '00000000-0000-0000-0000-000000000201',
    'background',
    10,
    'Explains why the original cafeteria idea was rejected.'
  ),
  (
    '00000000-0000-0000-0000-000000000901',
    '00000000-0000-0000-0000-000000000702',
    '00000000-0000-0000-0000-000000000201',
    'decision',
    20,
    'Records the positive decision to choose MemoryBase.'
  ),
  (
    '00000000-0000-0000-0000-000000000901',
    '00000000-0000-0000-0000-000000000703',
    '00000000-0000-0000-0000-000000000201',
    'context',
    30,
    'Connects the topic decision to the required recall demo question.'
  ),
  (
    '00000000-0000-0000-0000-000000000901',
    '00000000-0000-0000-0000-000000000719',
    '00000000-0000-0000-0000-000000000201',
    'outcome',
    40,
    'Captures the final answer expected in the demo.'
  );

-- Access policies make the seeded retriever agent able to see project memory while
-- explicitly denying private memory. Query #4 in database/08_demo_queries.sql uses this.
INSERT INTO access_policy(workspace_id, principal_type, principal_id, resource_type, resource_scope, effect)
VALUES
  ('00000000-0000-0000-0000-000000000201', 'agent', '00000000-0000-0000-0000-000000000301', 'memory_item', 'project', 'allow'),
  ('00000000-0000-0000-0000-000000000201', 'agent', '00000000-0000-0000-0000-000000000301', 'memory_item', 'private', 'deny');

INSERT INTO conflict_record(
  conflict_id, workspace_id, left_memory_id, right_memory_id, conflict_type, status, resolution_note, created_at
)
VALUES (
  '00000000-0000-0000-0000-000000001001',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000712',
  '00000000-0000-0000-0000-000000000720',
  'uncertain',
  'open',
  'Clarify whether LLM extraction belongs to MVP or future scope.',
  '2026-03-25 11:00:00+00'
);

-- RecallLog is seeded as a historical snapshot. It is intentionally JSONB-heavy
-- because the context pack shape can evolve without changing old audit records.
INSERT INTO recall_log(
  recall_id, workspace_id, agent_id, user_id, query_text, filter_json, result_count,
  top_memory_ids_json, context_pack_json, created_at
)
VALUES (
  '00000000-0000-0000-0000-000000001101',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000301',
  '00000000-0000-0000-0000-000000000101',
  'why did we abandon the campus cafeteria system',
  '{"access_level":["project"]}'::jsonb,
  3,
  '["00000000-0000-0000-0000-000000000701","00000000-0000-0000-0000-000000000719","00000000-0000-0000-0000-000000000702"]'::jsonb,
  '{"answer":"The cafeteria system was too CRUD-heavy and did not demonstrate enough database features."}'::jsonb,
  '2026-03-25 11:10:00+00'
);

-- Timeline and Wiki rows give the frontend/report a human-readable projection of
-- the same memories that the database and Agent APIs use.
INSERT INTO timeline_entry(
  timeline_id, workspace_id, memory_id, doc_id, event_type, title, description, event_time, importance
)
VALUES
  ('00000000-0000-0000-0000-000000001201', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000501', 'decision', 'Abandoned cafeteria system', 'The team rejected the cafeteria topic because it was too CRUD-heavy.', '2026-03-02 10:30:00+00', 5),
  ('00000000-0000-0000-0000-000000001202', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000501', 'decision', 'Selected MemoryBase', 'The team selected MemoryBase for richer database requirements.', '2026-03-02 10:40:00+00', 5),
  ('00000000-0000-0000-0000-000000001203', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000707', '00000000-0000-0000-0000-000000000503', 'proposal', 'Locked schema requirements', 'The schema must show keys, constraints, views, indexes, and triggers.', '2026-03-10 10:30:00+00', 4),
  ('00000000-0000-0000-0000-000000001204', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000711', '00000000-0000-0000-0000-000000000504', 'proposal', 'Defined recall shape', 'Recall should return memory with evidence and source chunks.', '2026-03-15 10:30:00+00', 4),
  ('00000000-0000-0000-0000-000000001205', '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000716', '00000000-0000-0000-0000-000000000505', 'decision', 'Added wiki provenance', 'Wiki statements should trace back to evidence and source chunks.', '2026-03-20 10:30:00+00', 4);

INSERT INTO wiki_page(
  page_id, workspace_id, page_slug, page_type, title,
  generated_from_scene_id, generated_from_memory_id, needs_rebuild
)
VALUES
  ('00000000-0000-0000-0000-000000001301', '00000000-0000-0000-0000-000000000201', 'why-memorybase', 'synthesis', 'Why MemoryBase', '00000000-0000-0000-0000-000000000901', '00000000-0000-0000-0000-000000000702', true),
  ('00000000-0000-0000-0000-000000001302', '00000000-0000-0000-0000-000000000201', 'database-design', 'report', 'Database Design', NULL, '00000000-0000-0000-0000-000000000707', true),
  ('00000000-0000-0000-0000-000000001303', '00000000-0000-0000-0000-000000000201', 'demo-playbook', 'handbook', 'Demo Playbook', NULL, '00000000-0000-0000-0000-000000000718', true);

INSERT INTO wiki_page_revision(page_id, revision_no, frontmatter_json, body_markdown, generated_by, created_at)
VALUES
  (
    '00000000-0000-0000-0000-000000001301',
    1,
    '{"slug":"why-memorybase","source":"seed"}'::jsonb,
    '# Why MemoryBase\n\nMemoryBase was selected because it demonstrates source chunks, evidence, revisions, audit logs, access policy, recall logs, conflicts, and wiki projection.',
    'exporter',
    '2026-03-25 11:20:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000001302',
    1,
    '{"slug":"database-design","source":"seed"}'::jsonb,
    '# Database Design\n\nThe schema demonstrates primary keys, foreign keys, unique constraints, check constraints, indexes, views, and triggers.',
    'exporter',
    '2026-03-25 11:21:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000001303',
    1,
    '{"slug":"demo-playbook","source":"seed"}'::jsonb,
    '# Demo Playbook\n\nThe demo should show source import, chunk line numbers, memory evidence, recall, revision, audit, policy filtering, conflict handling, wiki export, and SQL queries.',
    'exporter',
    '2026-03-25 11:22:00+00'
  );

SELECT set_config('app.actor_type', '', false);
SELECT set_config('app.actor_id', '', false);
SELECT set_config('app.revision_reason', '', false);
