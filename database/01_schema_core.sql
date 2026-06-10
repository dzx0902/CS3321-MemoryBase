-- Human users who own workspaces, import sources, review governance actions,
-- and appear as actors in audit records.
CREATE TABLE IF NOT EXISTS user_account (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(80) NOT NULL UNIQUE,
  display_name VARCHAR(120) NOT NULL,
  email VARCHAR(160) UNIQUE,
  role_hint VARCHAR(30) DEFAULT 'user'
    CHECK (role_hint IN ('user', 'admin', 'member', 'guest')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A tenant boundary for all source, memory, governance, and wiki data.
-- Most query indexes start with workspace_id for course-scale multi-tenant isolation.
CREATE TABLE IF NOT EXISTS workspace (
  workspace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug VARCHAR(64) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  description TEXT,
  scope_type VARCHAR(30) NOT NULL DEFAULT 'project'
    CHECK (scope_type IN ('personal', 'team', 'project')),
  owner_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent identities are stored separately from users so visibility policies can
-- target either a specific agent or an agent role/type.
CREATE TABLE IF NOT EXISTS agent (
  agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  name VARCHAR(120) NOT NULL,
  agent_type VARCHAR(40) NOT NULL DEFAULT 'retriever'
    CHECK (agent_type IN ('retriever', 'editor', 'reviewer', 'exporter', 'demo')),
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'disabled')),
  owner_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(workspace_id, name)
);

-- Workspace membership accepts both users and agents. principal_id is generic
-- by design; application/service code validates the matching principal table.
CREATE TABLE IF NOT EXISTS workspace_member (
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  principal_type VARCHAR(20) NOT NULL CHECK (principal_type IN ('user', 'agent')),
  principal_id UUID NOT NULL,
  member_role VARCHAR(30) NOT NULL DEFAULT 'viewer'
    CHECK (member_role IN ('owner', 'admin', 'editor', 'viewer', 'agent')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, principal_type, principal_id)
);
