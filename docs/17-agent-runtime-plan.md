# Agent Runtime v1 Plan

## Positioning

MemoryBase Agent Runtime v1 is CLI-first. Shell-capable agents should be able to
configure MemoryBase, check health, recall memory, render context, and later write
back observations without using the web UI.

FastAPI remains the remote and human-review adapter. The v1 CLI uses HTTP by
default so it reuses existing API validation, audit, policy, and trigger behavior.
The service layer is not reorganized in v1.

## PR Plan

### PR1: Backend Packaging and CLI Skeleton

- Package the existing `backend/app` package with root `pyproject.toml`.
- Register `memorybase` and `mb` console scripts.
- Add `mb configure` and `mb health`.
- Add `GET /api/health/detail`.
- Add `POST /api/agents/register` so `mb configure --register-agent` can be
  idempotent over HTTP.
- Add `workspace.slug` for agent-friendly workspace lookup.

### PR2: Recall, Context Formatter, and Mini Eval

- Add `mb recall` and `mb context`.
- Add `POST /api/recall/context-pack`.
- Render recall output as token-limited Markdown with stable citations.
- Add a small recall gold set and `mb eval recall`.

### PR3: Observe and Safe Write-back

- Add `POST /api/sessions`, `POST /api/observe`, and batch observe.
- Add `mb sessions`, `mb observe`, and `mb remember`.
- Allow CLI/agent memory writes without user-provided evidence by creating an
  `inline_agent_note` source document and source chunk.

### PR4: Hybrid Recall Design

Hybrid recall and pgvector are v2 work. They require a recall eval baseline and a
real embedding provider. pgvector stores vectors, but an embedding model is still
required to generate them.

## CLI Contract

### Configuration

Configuration priority:

```text
CLI args > MEMORYBASE_* env vars > ./.memorybase.toml > ~/.config/memorybase/config.toml > defaults
```

Supported fields:

```toml
api_base_url = "http://localhost:8000"
workspace = "cs3321-demo"
agent = "codex"
actor_type = "agent"
actor_id = "00000000-0000-0000-0000-000000000301"
database_url = "postgresql://memorybase:memorybase@localhost:5432/memorybase_db"
```

`workspace` accepts a UUID or `workspace.slug`. `agent` accepts a UUID or agent
name scoped to the configured workspace.

### Commands

```bash
mb configure --api-base http://localhost:8000 --workspace cs3321-demo
mb configure --workspace cs3321-demo --register-agent codex --type editor
mb health --format json
```

Planned follow-up commands:

```bash
mb recall "query" --format json
mb context "query" --max-tokens 3000
mb eval recall
mb sessions create --title "feature work"
mb observe --session <id> --role user --content "..."
mb observe --session <id> --batch < messages.jsonl
mb remember "fact" --type decision --reason "..." --dry-run
mb remember "fact" --type decision --reason "..." --commit
```

### Output and Exit Codes

- stdout contains the command result only.
- stderr contains logs, metadata, and errors.
- `--format json` is mandatory for machine-parsed output.

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | ok |
| 2 | client/config/request error |
| 3 | server/backend error |
| 4 | no result |

## v1 Non-goals

- No FastAPI-to-core refactor.
- No MCP adapter.
- No LLM auto-extraction.
- No `mb maintain` automatic memory maintenance.
- No pgvector or hybrid recall implementation before a recall eval baseline exists.
