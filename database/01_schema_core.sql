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

CREATE TABLE IF NOT EXISTS workspace (
  workspace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(120) NOT NULL,
  description TEXT,
  scope_type VARCHAR(30) NOT NULL DEFAULT 'project'
    CHECK (scope_type IN ('personal', 'team', 'project')),
  owner_user_id UUID REFERENCES user_account(user_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE TABLE IF NOT EXISTS workspace_member (
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  principal_type VARCHAR(20) NOT NULL CHECK (principal_type IN ('user', 'agent')),
  principal_id UUID NOT NULL,
  member_role VARCHAR(30) NOT NULL DEFAULT 'viewer'
    CHECK (member_role IN ('owner', 'admin', 'editor', 'viewer', 'agent')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, principal_type, principal_id)
);
