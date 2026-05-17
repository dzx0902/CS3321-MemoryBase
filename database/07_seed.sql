INSERT INTO user_account (user_id, username, display_name, email, role_hint)
VALUES
  ('00000000-0000-0000-0000-000000000101', 'alice', 'Alice Chen', 'alice@example.com', 'admin'),
  ('00000000-0000-0000-0000-000000000102', 'bob', 'Bob Li', 'bob@example.com', 'member'),
  ('00000000-0000-0000-0000-000000000103', 'carol', 'Carol Wang', 'carol@example.com', 'member'),
  ('00000000-0000-0000-0000-000000000104', 'demo-agent-owner', 'Demo Agent Owner', 'agent-owner@example.com', 'member')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO workspace (workspace_id, name, description, scope_type, owner_user_id)
VALUES (
  '00000000-0000-0000-0000-000000000201',
  'MemoryBase Demo Workspace',
  'Demo workspace for backend P0/P1 verification.',
  'project',
  '00000000-0000-0000-0000-000000000101'
)
ON CONFLICT (workspace_id) DO NOTHING;

INSERT INTO agent (agent_id, workspace_id, name, agent_type, status, owner_user_id)
VALUES (
  '00000000-0000-0000-0000-000000000301',
  '00000000-0000-0000-0000-000000000201',
  'demo-retriever',
  'retriever',
  'active',
  '00000000-0000-0000-0000-000000000104'
)
ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO workspace_member (workspace_id, principal_type, principal_id, member_role)
VALUES
  ('00000000-0000-0000-0000-000000000201', 'user', '00000000-0000-0000-0000-000000000101', 'owner'),
  ('00000000-0000-0000-0000-000000000201', 'user', '00000000-0000-0000-0000-000000000102', 'editor'),
  ('00000000-0000-0000-0000-000000000201', 'user', '00000000-0000-0000-0000-000000000103', 'viewer'),
  ('00000000-0000-0000-0000-000000000201', 'agent', '00000000-0000-0000-0000-000000000301', 'agent')
ON CONFLICT (workspace_id, principal_type, principal_id) DO NOTHING;

INSERT INTO source_document (
  doc_id, workspace_id, doc_type, title, source_path, raw_text, checksum, imported_by_user_id, imported_at
)
VALUES
  (
    '00000000-0000-0000-0000-000000000401',
    '00000000-0000-0000-0000-000000000201',
    'markdown',
    'discussion_01',
    'data/raw_sources/demo_workspace/discussion_01.md',
    '# 项目启动
我们最先评估的是校园食堂系统选题。
这个范围对课程项目来说太大了。
随后我们提出改做 MemoryBase。',
    'seed-doc-discussion-01',
    '00000000-0000-0000-0000-000000000101',
    '2026-05-10 09:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000402',
    '00000000-0000-0000-0000-000000000201',
    'meeting',
    'meeting_02',
    'data/raw_sources/demo_workspace/meeting_02.md',
    '# 决策会议
团队一致同意放弃校园食堂系统。
MemoryBase 更适合展示数据库中心化和治理能力。',
    'seed-doc-meeting-02',
    '00000000-0000-0000-0000-000000000102',
    '2026-05-11 10:00:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000403',
    '00000000-0000-0000-0000-000000000201',
    'report',
    'notes_private',
    'data/raw_sources/demo_workspace/notes_private.md',
    '# 私有笔记
只有在授权之后，检索 Agent 才能看到这条私有综合结论。',
    'seed-doc-private-notes',
    '00000000-0000-0000-0000-000000000101',
    '2026-05-12 08:30:00+00'
  )
ON CONFLICT (doc_id) DO NOTHING;

INSERT INTO source_chunk (chunk_id, doc_id, chunk_no, chunk_text, start_line, end_line, token_count)
VALUES
  ('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000401', 1, '我们最先评估的是校园食堂系统选题。', 2, 2, 1),
  ('00000000-0000-0000-0000-000000000502', '00000000-0000-0000-0000-000000000401', 2, '这个范围对课程项目来说太大了。随后我们提出改做 MemoryBase。', 3, 4, 2),
  ('00000000-0000-0000-0000-000000000503', '00000000-0000-0000-0000-000000000402', 1, '团队一致同意放弃校园食堂系统。', 2, 2, 1),
  ('00000000-0000-0000-0000-000000000504', '00000000-0000-0000-0000-000000000402', 2, 'MemoryBase 更适合展示数据库中心化和治理能力。', 3, 3, 3),
  ('00000000-0000-0000-0000-000000000505', '00000000-0000-0000-0000-000000000403', 1, '只有在授权之后，检索 Agent 才能看到这条私有综合结论。', 2, 2, 2)
ON CONFLICT (chunk_id) DO NOTHING;

INSERT INTO memory_item (
  memory_id, workspace_id, created_from_doc_id, memory_type, canonical_text, summary,
  confidence, importance, status, access_level, owner_user_id, owner_agent_id,
  valid_from, current_revision_no, created_at, updated_at
)
VALUES
  (
    '00000000-0000-0000-0000-000000000601',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000401',
    'decision',
    '团队最初考虑把校园食堂系统作为课程项目。',
    '初始选题设想',
    0.620,
    3,
    'active',
    'project',
    '00000000-0000-0000-0000-000000000101',
    NULL,
    '2026-05-10 09:00:00+00',
    1,
    '2026-05-10 09:05:00+00',
    '2026-05-10 09:05:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000602',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000402',
    'decision',
    '团队放弃了校园食堂系统，正式转向 MemoryBase。',
    '项目方向切换',
    0.950,
    5,
    'active',
    'project',
    '00000000-0000-0000-0000-000000000102',
    NULL,
    '2026-05-11 10:00:00+00',
    1,
    '2026-05-11 10:05:00+00',
    '2026-05-11 10:05:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000603',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000402',
    'risk',
    '继续推进校园食堂系统会超出课程项目范围。',
    '范围风险',
    0.880,
    4,
    'active',
    'project',
    '00000000-0000-0000-0000-000000000102',
    NULL,
    '2026-05-11 10:02:00+00',
    1,
    '2026-05-11 10:06:00+00',
    '2026-05-11 10:06:00+00'
  ),
  (
    '00000000-0000-0000-0000-000000000604',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000403',
    'semantic',
    '私有路线图包含一个不对普通查看者开放的治理演示。',
    '私有规划',
    0.910,
    4,
    'active',
    'private',
    '00000000-0000-0000-0000-000000000101',
    '00000000-0000-0000-0000-000000000301',
    '2026-05-12 08:30:00+00',
    1,
    '2026-05-12 08:35:00+00',
    '2026-05-12 08:35:00+00'
  )
ON CONFLICT (memory_id) DO NOTHING;

INSERT INTO memory_evidence (evidence_id, memory_id, chunk_id, evidence_role, weight, note)
VALUES
  ('00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000601', '00000000-0000-0000-0000-000000000501', 'source', 0.800, 'initial idea'),
  ('00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000602', '00000000-0000-0000-0000-000000000503', 'supports', 1.000, 'decision statement'),
  ('00000000-0000-0000-0000-000000000703', '00000000-0000-0000-0000-000000000602', '00000000-0000-0000-0000-000000000504', 'context', 0.900, 'rationale'),
  ('00000000-0000-0000-0000-000000000704', '00000000-0000-0000-0000-000000000603', '00000000-0000-0000-0000-000000000502', 'supports', 0.850, 'scope risk'),
  ('00000000-0000-0000-0000-000000000705', '00000000-0000-0000-0000-000000000604', '00000000-0000-0000-0000-000000000505', 'supports', 1.000, 'private note')
ON CONFLICT (evidence_id) DO NOTHING;

INSERT INTO access_policy (
  policy_id, workspace_id, principal_type, principal_id, resource_type, resource_scope, effect, predicate_json
)
VALUES
  (
    '00000000-0000-0000-0000-000000000801',
    '00000000-0000-0000-0000-000000000201',
    'agent',
    '00000000-0000-0000-0000-000000000301',
    'memory_item',
    'private',
    'allow',
    '{"reason": "demo private memory access"}'::jsonb
  )
ON CONFLICT (policy_id) DO NOTHING;

INSERT INTO conflict_record (
  conflict_id, workspace_id, left_memory_id, right_memory_id, conflict_type, status,
  resolution_note, created_at, updated_at
)
VALUES
  (
    '00000000-0000-0000-0000-000000000901',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000601',
    '00000000-0000-0000-0000-000000000602',
    'semantic',
    'open',
    NULL,
    '2026-05-11 11:00:00+00',
    '2026-05-11 11:00:00+00'
  )
ON CONFLICT (conflict_id) DO NOTHING;

INSERT INTO timeline_entry (
  timeline_id, workspace_id, memory_id, doc_id, event_type, title, description, event_time, importance
)
VALUES
  (
    '00000000-0000-0000-0000-000000001001',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000601',
    '00000000-0000-0000-0000-000000000401',
    'proposal',
    '考虑校园食堂系统',
    '团队在 kickoff 阶段提出校园食堂系统作为候选题目。',
    '2026-05-10 09:00:00+00',
    3
  ),
  (
    '00000000-0000-0000-0000-000000001002',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000603',
    '00000000-0000-0000-0000-000000000401',
    'meeting',
    '识别范围风险',
    '评估发现校园食堂系统对课程项目来说范围过大。',
    '2026-05-10 09:30:00+00',
    4
  ),
  (
    '00000000-0000-0000-0000-000000001003',
    '00000000-0000-0000-0000-000000000201',
    '00000000-0000-0000-0000-000000000602',
    '00000000-0000-0000-0000-000000000402',
    'decision',
    '切换到 MemoryBase',
    '团队正式放弃校园食堂系统并改做 MemoryBase。',
    '2026-05-11 10:00:00+00',
    5
  )
ON CONFLICT (timeline_id) DO NOTHING;
