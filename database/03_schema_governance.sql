-- Human-readable projection of memories or scenes. The page row stores current
-- state, while immutable page contents live in wiki_page_revision.
CREATE TABLE IF NOT EXISTS wiki_page (
  page_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  page_slug VARCHAR(240) NOT NULL,
  page_type VARCHAR(40) NOT NULL
    CHECK (page_type IN ('source', 'entity', 'concept', 'synthesis', 'report', 'timeline', 'handbook')),
  title VARCHAR(240) NOT NULL,
  current_revision_no INT NOT NULL DEFAULT 0,
  generated_from_scene_id UUID REFERENCES memory_scene(scene_id) ON DELETE SET NULL,
  generated_from_memory_id UUID REFERENCES memory_item(memory_id) ON DELETE SET NULL,
  needs_rebuild BOOLEAN NOT NULL DEFAULT TRUE,
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'forgotten')),
  forgotten_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(workspace_id, page_slug)
);

-- Immutable wiki version body. frontmatter_json keeps export metadata such as
-- memory_ids and source_doc_ids without changing the core page schema.
CREATE TABLE IF NOT EXISTS wiki_page_revision (
  page_id UUID NOT NULL REFERENCES wiki_page(page_id) ON DELETE CASCADE,
  revision_no INT NOT NULL,
  frontmatter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  body_markdown TEXT NOT NULL,
  generated_by VARCHAR(30) NOT NULL DEFAULT 'exporter'
    CHECK (generated_by IN ('user', 'agent', 'system', 'exporter')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (page_id, revision_no)
);

-- Project timeline event used by the demo and report to explain decisions over time.
CREATE TABLE IF NOT EXISTS timeline_entry (
  timeline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  memory_id UUID REFERENCES memory_item(memory_id) ON DELETE SET NULL,
  doc_id UUID REFERENCES source_document(doc_id) ON DELETE SET NULL,
  event_type VARCHAR(30) NOT NULL
    CHECK (event_type IN ('meeting', 'proposal', 'decision', 'revision', 'conflict', 'resolution')),
  title VARCHAR(240) NOT NULL,
  description TEXT,
  event_time TIMESTAMPTZ NOT NULL,
  importance INT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Recall invocation log. JSON fields preserve filters, ranked memory snapshots,
-- and generated context packs for later audit and evaluation.
CREATE TABLE IF NOT EXISTS recall_log (
  recall_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  agent_id UUID REFERENCES agent(agent_id) ON DELETE SET NULL,
  user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  query_text TEXT NOT NULL,
  filter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  result_count INT NOT NULL DEFAULT 0,
  top_memory_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  context_pack_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Access policy rule for users, agents, or roles. principal_id may be NULL for
-- global role policies, which is why database/04_indexes.sql adds a partial unique index.
CREATE TABLE IF NOT EXISTS access_policy (
  policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  principal_type VARCHAR(20) NOT NULL CHECK (principal_type IN ('user', 'agent', 'role')),
  principal_id UUID,
  resource_type VARCHAR(40) NOT NULL
    CHECK (resource_type IN ('memory_item', 'source_document', 'wiki_page', 'workspace')),
  resource_scope VARCHAR(20) NOT NULL DEFAULT 'project'
    CHECK (resource_scope IN ('public', 'project', 'team', 'private', 'all')),
  effect VARCHAR(10) NOT NULL CHECK (effect IN ('allow', 'deny')),
  predicate_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(workspace_id, principal_type, principal_id, resource_type, resource_scope, effect)
);

-- Soft-forget governance request. Targets are generic so one workflow can cover
-- memory_item, source_document, wiki_page, and entity.
CREATE TABLE IF NOT EXISTS forget_request (
  request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  target_type VARCHAR(40) NOT NULL
    CHECK (target_type IN ('memory_item', 'source_document', 'wiki_page', 'entity')),
  target_id UUID NOT NULL,
  requester_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  reviewed_by_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  reason TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected', 'done')),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

-- Pairwise memory conflict record. CHECK(left_memory_id < right_memory_id)
-- canonicalizes unordered pairs and prevents A/B plus B/A duplicates.
CREATE TABLE IF NOT EXISTS conflict_record (
  conflict_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  left_memory_id UUID NOT NULL REFERENCES memory_item(memory_id) ON DELETE CASCADE,
  right_memory_id UUID NOT NULL REFERENCES memory_item(memory_id) ON DELETE CASCADE,
  conflict_type VARCHAR(30) NOT NULL DEFAULT 'semantic'
    CHECK (
      conflict_type IN (
        'semantic',
        'temporal',
        'policy',
        'duplicate',
        'contradiction',
        'supersession',
        'uncertain'
      )
    ),
  status VARCHAR(20) NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'resolved', 'ignored')),
  resolution_note TEXT,
  resolved_by_actor_type VARCHAR(20)
    CHECK (resolved_by_actor_type IN ('user', 'agent', 'system')),
  resolved_by_actor_id UUID,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (left_memory_id < right_memory_id),
  UNIQUE(left_memory_id, right_memory_id)
);

-- Append-only audit log for lifecycle events. before_json/after_json preserve
-- record snapshots even if the relational schema evolves later.
CREATE TABLE IF NOT EXISTS audit_log (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  actor_type VARCHAR(20) NOT NULL CHECK (actor_type IN ('user', 'agent', 'system')),
  actor_id UUID,
  action_type VARCHAR(80) NOT NULL,
  target_type VARCHAR(80) NOT NULL,
  target_id UUID,
  before_json JSONB,
  after_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
