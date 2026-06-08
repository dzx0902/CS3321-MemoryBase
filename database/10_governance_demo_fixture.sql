-- ============================================================
-- Governance / Provenance Demo Fixture (Tier 1 #6)
-- ============================================================
-- 最小补充数据集，用于在 demo 中演示三种 governance 生命周期：
--   1) Forgotten memory  - status='forgotten' + forget_request 闭环
--   2) Archived memory   - status='archived' + superseded_by 链
--   3) Resolved conflict - conflict_record(status='resolved') + 解决说明
--   4) Forgotten source  - source_document(status='forgotten') 同步审计
--
-- 设计原则：
--   - 压缩 fixture，不扩成完整 governance 数据集（见 plan）
--   - 全部使用稳定 UUID（0731-0742, 0507, 1002, 1101-1102），避免 demo 不可复现
--   - 利用现有 trigger 自动写 audit_log（不重复手工 insert）
--   - 完全幂等：使用 ON CONFLICT DO NOTHING + IF NOT EXISTS 守卫
--   - 保留现有 open conflict(1001) 不变，新增 resolved conflict(1002) 形成对比
--
-- 复现：
--   psql $DATABASE_URL -f database/10_governance_demo_fixture.sql
--
-- 演示查询：见 docs/governance-demo-walkthrough.md 或 database/08_demo_queries.sql
-- ============================================================

\set ON_ERROR_STOP on

-- 整个脚本作为一个事务运行：
--   1) 保证 SET LOCAL 生效（actor 上下文传给 trigger）
--   2) 保证所有 fixture 原子加载，失败回滚
BEGIN;

DO $$
BEGIN
  -- 幂等守卫：如果第一条 fixture 记录已存在，仅发出 notice；
  -- 后续语句依赖 ON CONFLICT / 条件 UPDATE 保持幂等，不会重复写入有效数据。
  IF EXISTS (SELECT 1 FROM memory_item WHERE memory_id = '00000000-0000-0000-0000-000000000731') THEN
    RAISE NOTICE 'governance demo fixture already loaded, skipping';
  END IF;
END
$$ LANGUAGE plpgsql;

-- 设置 actor 上下文，让 trigger 写出有归属的 audit_log
SET LOCAL app.actor_type = 'user';
SET LOCAL app.actor_id   = '00000000-0000-0000-0000-000000000101';  -- alice
SET LOCAL app.revision_reason = 'governance demo fixture load';


-- ============================================================
-- §1. 案例 A: Forgotten memory（含 forget_request 闭环）
--
-- 故事：alice 早期记录了"使用 Hash 索引做 memory 查找"的决定，
-- 后来团队选择 B+ tree（详见 index-rationale.md），需要 forget 这条
-- 过时记录。流程：先 INSERT active memory；再走 forget_request 走审；
-- 最后 UPDATE status='forgotten' 由 trigger 写 memory.forget audit。
-- ============================================================

INSERT INTO memory_item (
  memory_id, workspace_id, created_from_doc_id,
  memory_type, canonical_text, summary,
  search_text_zh,
  confidence, importance, status, access_level,
  owner_user_id, valid_from
) VALUES (
  '00000000-0000-0000-0000-000000000731',
  '00000000-0000-0000-0000-000000000201',
  NULL,
  'decision',
  'Use PostgreSQL Hash index for memory_item primary key lookup.',
  'Early (wrong) decision: prefer Hash index.',
  'Use PostgreSQL Hash index for memory_item primary key lookup.',
  0.5, 2, 'active', 'project',
  '00000000-0000-0000-0000-000000000101',
  now() - interval '20 days'
)
ON CONFLICT (memory_id) DO NOTHING;

-- 用户提交 forget_request
INSERT INTO forget_request (
  request_id, workspace_id, target_type, target_id,
  requester_user_id, reviewed_by_user_id,
  reason, status, requested_at, resolved_at
) VALUES (
  '00000000-0000-0000-0000-000000001101',
  '00000000-0000-0000-0000-000000000201',
  'memory_item', '00000000-0000-0000-0000-000000000731',
  '00000000-0000-0000-0000-000000000101',  -- alice 申请
  '00000000-0000-0000-0000-000000000102',  -- bob 复核
  'Hash index was the wrong choice; supersede with the B+ tree decision (see docs/index-rationale.md §0 & §2).',
  'done',
  now() - interval '5 days',
  now() - interval '4 days'
)
ON CONFLICT (request_id) DO NOTHING;

-- 复核通过后真正将 memory 标为 forgotten（触发 audit "memory.forget"）
UPDATE memory_item
   SET status = 'forgotten'
 WHERE memory_id = '00000000-0000-0000-0000-000000000731'
   AND status <> 'forgotten';


-- ============================================================
-- §2. 案例 B: Archived memory（含 superseded_by 链）
--
-- 故事：早期"recall 只用 ILIKE"的备忘 (732) 被新的"GIN tsvector 主 +
-- ILIKE fallback" 决定 (733) 取代。732 标 archived 并 superseded_by=733。
-- ============================================================

-- 新的、正确的决定（先 INSERT，因为 superseded_by 要引用它）
INSERT INTO memory_item (
  memory_id, workspace_id, created_from_doc_id,
  memory_type, canonical_text, summary,
  search_text_zh,
  confidence, importance, status, access_level,
  owner_user_id, valid_from
) VALUES (
  '00000000-0000-0000-0000-000000000733',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000504',  -- Discussion 04: Policy and Recall
  'decision',
  'Recall combines GIN tsvector full-text search as the primary path with ILIKE pattern matching as fallback for short queries.',
  'Final recall design: GIN FTS primary + ILIKE fallback.',
  'Recall combines GIN tsvector full-text search as primary path with ILIKE pattern matching as fallback for short queries.',
  0.9, 5, 'active', 'project',
  '00000000-0000-0000-0000-000000000101',
  now() - interval '10 days'
)
ON CONFLICT (memory_id) DO NOTHING;

-- 老的、被取代的决定
INSERT INTO memory_item (
  memory_id, workspace_id, created_from_doc_id,
  memory_type, canonical_text, summary,
  search_text_zh,
  confidence, importance, status, access_level,
  owner_user_id, valid_from, valid_to,
  superseded_by_memory_id
) VALUES (
  '00000000-0000-0000-0000-000000000732',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000504',
  'decision',
  'Recall implementation will use ILIKE pattern matching only.',
  'Early decision: ILIKE only.',
  'Recall implementation will use ILIKE pattern matching only.',
  0.5, 2, 'active', 'project',
  '00000000-0000-0000-0000-000000000101',
  now() - interval '18 days', now() - interval '10 days',
  '00000000-0000-0000-0000-000000000733'
)
ON CONFLICT (memory_id) DO NOTHING;

-- 标 archived（触发 audit "memory.soft_delete"）
UPDATE memory_item
   SET status = 'archived'
 WHERE memory_id = '00000000-0000-0000-0000-000000000732'
   AND status <> 'archived';


-- ============================================================
-- §3. 案例 C: Resolved conflict（保留现有 open conflict 不变作为对比）
--
-- 故事：在某次讨论中两个 agent 同时记录了关于"meeting 频率"的不同
-- memory；后被人审复审，确认其中一条胜出，记录解决说明。
-- 直接 INSERT status='resolved' 跳过 open 状态 → 不污染 memory.status，
-- 也不破坏 trigger fn_conflict_after_insert 的 "open 才 mark conflicted" 语义。
-- ============================================================

INSERT INTO memory_item (
  memory_id, workspace_id, created_from_doc_id,
  memory_type, canonical_text, summary,
  search_text_zh,
  confidence, importance, status, access_level,
  owner_user_id, valid_from
) VALUES (
  '00000000-0000-0000-0000-000000000741',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000501',
  'decision',
  'Team standup is held every Monday morning at 10am.',
  'Standup cadence: weekly Monday.',
  'Team standup is held every Monday morning at 10am.',
  0.85, 3, 'active', 'project',
  '00000000-0000-0000-0000-000000000101',
  now() - interval '40 days'
),
(
  '00000000-0000-0000-0000-000000000742',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000501',
  'decision',
  'Team standup is held twice a week, on Monday and Thursday mornings.',
  'Standup cadence: biweekly Mon/Thu (rejected).',
  'Team standup is held twice a week on Monday and Thursday mornings.',
  0.6, 2, 'active', 'project',
  '00000000-0000-0000-0000-000000000101',
  now() - interval '35 days'
)
ON CONFLICT (memory_id) DO NOTHING;

-- 直接以 resolved 状态插入 conflict（保留 left_memory_id < right_memory_id 约束）
INSERT INTO conflict_record (
  conflict_id, workspace_id,
  left_memory_id, right_memory_id,
  conflict_type, status,
  resolution_note,
  resolved_by_actor_type, resolved_by_actor_id, resolved_at,
  created_at, updated_at
) VALUES (
  '00000000-0000-0000-0000-000000001002',
  '00000000-0000-0000-0000-000000000201',
  '00000000-0000-0000-0000-000000000741',
  '00000000-0000-0000-0000-000000000742',
  'contradiction',
  'resolved',
  'Resolution by carol: weekly Monday cadence wins per team vote 4-1. Memory 0742 kept for audit trail but marked superseded.',
  'user', '00000000-0000-0000-0000-000000000103',  -- carol
  now() - interval '32 days',
  now() - interval '34 days',
  now() - interval '32 days'
)
ON CONFLICT (conflict_id) DO NOTHING;

-- 把 0742 显式标为 superseded（resolution 后的人工归档动作）
UPDATE memory_item
   SET status = 'superseded',
       superseded_by_memory_id = '00000000-0000-0000-0000-000000000741',
       valid_to = now() - interval '32 days'
 WHERE memory_id = '00000000-0000-0000-0000-000000000742'
   AND status <> 'superseded';


-- ============================================================
-- §4. 案例 D: Forgotten source document
--
-- 故事：早期一份"初始 scope"讨论稿被替换并不再可参考。
-- 直接以 status='forgotten' 插入 + 同步 forget_request 走审。
-- ============================================================

INSERT INTO source_document (
  doc_id, workspace_id, session_id,
  doc_type, title, source_path, raw_text, checksum,
  status, forgotten_at,
  imported_by_user_id, imported_at
) VALUES (
  '00000000-0000-0000-0000-000000000507',
  '00000000-0000-0000-0000-000000000201',
  NULL,
  'note',
  'Initial Scope Draft (abandoned)',
  'data/raw_sources/initial-scope-draft.md',
  'Initial project scope draft: building a small CRUD cafeteria menu manager. This direction was abandoned after the project-pivot discussion (see Discussion 01).',
  'demo-fixture-checksum-initial-scope-abandoned',
  'forgotten',
  now() - interval '45 days',
  '00000000-0000-0000-0000-000000000101',
  now() - interval '60 days'
)
ON CONFLICT (doc_id) DO NOTHING;

INSERT INTO forget_request (
  request_id, workspace_id, target_type, target_id,
  requester_user_id, reviewed_by_user_id,
  reason, status, requested_at, resolved_at
) VALUES (
  '00000000-0000-0000-0000-000000001102',
  '00000000-0000-0000-0000-000000000201',
  'source_document', '00000000-0000-0000-0000-000000000507',
  '00000000-0000-0000-0000-000000000102',  -- bob 申请
  '00000000-0000-0000-0000-000000000101',  -- alice 复核
  'Initial scope draft was abandoned after project pivot; keep file but mark forgotten to exclude from recall.',
  'done',
  now() - interval '46 days',
  now() - interval '45 days'
)
ON CONFLICT (request_id) DO NOTHING;

-- source_document 表无 trigger 自动写 audit_log，手动补一条让 lifecycle 可见
INSERT INTO audit_log (
  audit_id, workspace_id, actor_type, actor_id,
  action_type, target_type, target_id,
  before_json, after_json, created_at
)
SELECT
  gen_random_uuid(),
  '00000000-0000-0000-0000-000000000201',
  'user',
  '00000000-0000-0000-0000-000000000101',
  'source.forget',
  'source_document',
  '00000000-0000-0000-0000-000000000507',
  jsonb_build_object('status', 'active'),
  jsonb_build_object('status', 'forgotten', 'forgotten_at', (now() - interval '45 days')::text),
  now() - interval '45 days'
WHERE NOT EXISTS (
  SELECT 1 FROM audit_log
   WHERE target_id = '00000000-0000-0000-0000-000000000507'
     AND action_type = 'source.forget'
);


-- ============================================================
-- 完成提示
-- ============================================================

DO $$
DECLARE
  forgotten_mem_count INT;
  archived_mem_count INT;
  superseded_mem_count INT;
  resolved_conf_count INT;
  forgotten_src_count INT;
  forget_req_count INT;
BEGIN
  SELECT count(*) INTO forgotten_mem_count FROM memory_item
   WHERE workspace_id = '00000000-0000-0000-0000-000000000201' AND status = 'forgotten';
  SELECT count(*) INTO archived_mem_count  FROM memory_item
   WHERE workspace_id = '00000000-0000-0000-0000-000000000201' AND status = 'archived';
  SELECT count(*) INTO superseded_mem_count FROM memory_item
   WHERE workspace_id = '00000000-0000-0000-0000-000000000201' AND status = 'superseded';
  SELECT count(*) INTO resolved_conf_count FROM conflict_record
   WHERE workspace_id = '00000000-0000-0000-0000-000000000201' AND status = 'resolved';
  SELECT count(*) INTO forgotten_src_count FROM source_document
   WHERE workspace_id = '00000000-0000-0000-0000-000000000201' AND status = 'forgotten';
  SELECT count(*) INTO forget_req_count    FROM forget_request
   WHERE workspace_id = '00000000-0000-0000-0000-000000000201';

  RAISE NOTICE 'governance fixture loaded:';
  RAISE NOTICE '  forgotten memory: %', forgotten_mem_count;
  RAISE NOTICE '  archived memory:  %', archived_mem_count;
  RAISE NOTICE '  superseded memory:%', superseded_mem_count;
  RAISE NOTICE '  resolved conflict:%', resolved_conf_count;
  RAISE NOTICE '  forgotten source: %', forgotten_src_count;
  RAISE NOTICE '  forget requests:  %', forget_req_count;
END
$$ LANGUAGE plpgsql;

COMMIT;
