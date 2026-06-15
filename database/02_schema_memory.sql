-- A logical work session for meetings, chats, imports, manual edits, or CLI runs.
-- Messages and imported sources can point back to the session that produced them.
CREATE TABLE IF NOT EXISTS agent_session (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  agent_id UUID REFERENCES agent(agent_id) ON DELETE SET NULL,
  started_by_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  title VARCHAR(200) NOT NULL,
  channel VARCHAR(30) NOT NULL DEFAULT 'meeting'
    CHECK (channel IN ('meeting', 'chat', 'import', 'manual', 'cli')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ
);

-- Conversation message log. It preserves Agent Runtime inputs/outputs without
-- forcing every message to become long-term memory.
CREATE TABLE IF NOT EXISTS message (
  message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES agent_session(session_id) ON DELETE CASCADE,
  sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('user', 'agent', 'system')),
  sender_id UUID,
  role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reply_to_message_id UUID REFERENCES message(message_id) ON DELETE SET NULL
);

-- Raw imported document or inline agent note. Source rows are the provenance
-- root for chunks, memories, evidence, and wiki citations.
CREATE TABLE IF NOT EXISTS source_document (
  doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  session_id UUID REFERENCES agent_session(session_id) ON DELETE SET NULL,
  doc_type VARCHAR(30) NOT NULL DEFAULT 'markdown'
    CHECK (doc_type IN ('markdown', 'txt', 'meeting', 'chat', 'note', 'report', 'inline_agent_note')),
  title VARCHAR(240) NOT NULL,
  source_path TEXT,
  raw_text TEXT NOT NULL,
  checksum VARCHAR(128),
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'forgotten')),
  forgotten_at TIMESTAMPTZ,
  imported_by_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(workspace_id, checksum)
);

-- Searchable chunks derived from a source document. search_vector is generated
-- from pre-tokenized search_text_zh so PostgreSQL GIN can serve lexical recall.
CREATE TABLE IF NOT EXISTS source_chunk (
  chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_id UUID NOT NULL REFERENCES source_document(doc_id) ON DELETE CASCADE,
  chunk_no INT NOT NULL,
  chunk_text TEXT NOT NULL,
  start_line INT,
  end_line INT,
  token_count INT,
  search_text_zh TEXT,
  search_vector TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(search_text_zh, ''))
  ) STORED,
  UNIQUE(doc_id, chunk_no)
);

-- Long-term memory unit. Candidate extraction, access control, validity windows,
-- conflict lifecycle, and revision pointers all converge on this table.
CREATE TABLE IF NOT EXISTS memory_item (
  memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  created_from_doc_id UUID REFERENCES source_document(doc_id) ON DELETE SET NULL,
  memory_type VARCHAR(30) NOT NULL
    CHECK (
      memory_type IN (
        'episodic',
        'semantic',
        'fact',
        'profile',
        'procedural',
        'decision',
        'preference',
        'task',
        'risk',
        'constraint',
        'policy',
        'summary'
      )
    ),
  canonical_text TEXT NOT NULL,
  summary TEXT,
  search_text_zh TEXT,
  search_vector TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(search_text_zh, ''))
  ) STORED,
  confidence NUMERIC(4,3) NOT NULL DEFAULT 0.700 CHECK (confidence >= 0 AND confidence <= 1),
  importance INT NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (
      status IN (
        'candidate',
        'active',
        'archived',
        'forgotten',
        'superseded',
        'rejected',
        'conflicted'
      )
    ),
  access_level VARCHAR(20) NOT NULL DEFAULT 'project'
    CHECK (access_level IN ('public', 'project', 'team', 'private')),
  owner_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  owner_agent_id UUID REFERENCES agent(agent_id) ON DELETE SET NULL,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_to TIMESTAMPTZ,
  superseded_by_memory_id UUID REFERENCES memory_item(memory_id) ON DELETE SET NULL,
  current_revision_no INT NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(memory_id, workspace_id)
);

-- Immutable version history for each memory. Triggers insert revision rows when
-- memory content or governance fields change.
CREATE TABLE IF NOT EXISTS memory_revision (
  memory_id UUID NOT NULL REFERENCES memory_item(memory_id) ON DELETE CASCADE,
  revision_no INT NOT NULL,
  revision_text TEXT NOT NULL,
  revision_summary TEXT,
  revision_reason TEXT,
  editor_type VARCHAR(20) NOT NULL DEFAULT 'system'
    CHECK (editor_type IN ('user', 'agent', 'system')),
  editor_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (memory_id, revision_no)
);

-- Many-to-many evidence bridge between memories and source chunks. evidence_role
-- distinguishes supporting, refuting, contextual, and inline source evidence.
CREATE TABLE IF NOT EXISTS memory_evidence (
  evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES memory_item(memory_id) ON DELETE CASCADE,
  chunk_id UUID NOT NULL REFERENCES source_chunk(chunk_id) ON DELETE CASCADE,
  evidence_role VARCHAR(20) NOT NULL DEFAULT 'supports'
    CHECK (evidence_role IN ('supports', 'refutes', 'context', 'source')),
  weight NUMERIC(4,3) NOT NULL DEFAULT 1.000 CHECK (weight >= 0 AND weight <= 1),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(memory_id, chunk_id, evidence_role)
);

-- Optional memory-level embedding cache. The project stores vectors in JSONB to
-- avoid a hard pgvector dependency while still supporting hybrid recall demos.
CREATE TABLE IF NOT EXISTS memory_embedding (
  embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES memory_item(memory_id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  provider VARCHAR(80) NOT NULL,
  model VARCHAR(160) NOT NULL,
  dimension INT NOT NULL CHECK (dimension > 0),
  embedding_json JSONB NOT NULL,
  embedding_text_hash VARCHAR(128) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(memory_id, provider, model, embedding_text_hash),
  FOREIGN KEY (memory_id, workspace_id)
    REFERENCES memory_item(memory_id, workspace_id) ON DELETE CASCADE
);

-- Optional source-chunk embedding cache. Chunk embeddings can contribute vector
-- candidates through memory_evidence during hybrid recall.
CREATE TABLE IF NOT EXISTS source_chunk_embedding (
  embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id UUID NOT NULL REFERENCES source_chunk(chunk_id) ON DELETE CASCADE,
  doc_id UUID NOT NULL REFERENCES source_document(doc_id) ON DELETE CASCADE,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  provider VARCHAR(80) NOT NULL,
  model VARCHAR(160) NOT NULL,
  dimension INT NOT NULL CHECK (dimension > 0),
  embedding_json JSONB NOT NULL,
  embedding_text_hash VARCHAR(128) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(chunk_id, provider, model, embedding_text_hash)
);

-- Lightweight semantic entity inside a workspace, used for memory organization
-- and final-report/wiki inspection rather than a full knowledge graph.
CREATE TABLE IF NOT EXISTS entity (
  entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  canonical_name VARCHAR(240) NOT NULL,
  entity_type VARCHAR(40) NOT NULL
    CHECK (entity_type IN ('person', 'project', 'concept', 'document', 'event', 'other')),
  description TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'forgotten')),
  forgotten_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(entity_id, workspace_id),
  UNIQUE(workspace_id, canonical_name)
);

-- Memory-to-entity bridge. workspace_id participates in composite FKs so the
-- database rejects cross-workspace associations.
CREATE TABLE IF NOT EXISTS memory_entity (
  memory_id UUID NOT NULL,
  entity_id UUID NOT NULL,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  relation_role VARCHAR(40) NOT NULL DEFAULT 'about'
    CHECK (relation_role IN ('about', 'mentions', 'authored_by', 'owned_by', 'related_to')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (memory_id, entity_id, relation_role),
  FOREIGN KEY (memory_id, workspace_id)
    REFERENCES memory_item(memory_id, workspace_id) ON DELETE CASCADE,
  FOREIGN KEY (entity_id, workspace_id)
    REFERENCES entity(entity_id, workspace_id) ON DELETE CASCADE
);

-- A named scene groups memories into a topic, decision, or narrative unit for
-- demo pages and wiki projection.
CREATE TABLE IF NOT EXISTS memory_scene (
  scene_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  scene_slug VARCHAR(80) NOT NULL,
  title VARCHAR(240) NOT NULL,
  summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(scene_id, workspace_id),
  UNIQUE(workspace_id, scene_slug)
);

-- Scene membership bridge with ordering and narrative role metadata.
-- Composite FKs enforce that scene and memory belong to the same workspace.
CREATE TABLE IF NOT EXISTS memory_scene_cell (
  scene_id UUID NOT NULL,
  memory_id UUID NOT NULL,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  cell_role VARCHAR(40) NOT NULL DEFAULT 'support'
    CHECK (cell_role IN ('background', 'context', 'support', 'decision', 'outcome')),
  sort_order INT NOT NULL DEFAULT 100,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (scene_id, memory_id),
  FOREIGN KEY (scene_id, workspace_id)
    REFERENCES memory_scene(scene_id, workspace_id) ON DELETE CASCADE,
  FOREIGN KEY (memory_id, workspace_id)
    REFERENCES memory_item(memory_id, workspace_id) ON DELETE CASCADE
);
