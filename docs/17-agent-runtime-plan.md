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
- Keep agent-visible memory lookup under the `agents` router:
  `GET /api/agents/{agent_id}/visible-memories`.

PR2 eval scope is intentionally a smoke baseline, not a fair retrieval benchmark.
The initial gold set and `data/recall/demo_query_expansions.json` are hand-tuned
for the course demo dataset, so a high P@5 proves the recall/context/eval chain
works but must not be used as the PR4 hybrid-search comparison baseline. Before
hybrid recall or pgvector work starts, rebuild the eval set with adversarial
Chinese queries: semantic rewrites, fuzzy questions, missing keywords, and
negative cases.

`demo_query_expansions.json` is a PR2 stop-gap for deterministic bilingual demo
queries. It is not the production retrieval strategy; PR4 should deprecate this
manual dictionary in favor of embedding-backed or otherwise systematic semantic
recall.

`mb eval recall` reads `data/eval/recall_gold.json` from the repository root in
editable installs. If MemoryBase is later published as a wheel, package this gold
set with `importlib.resources` or explicit package data instead of relying on the
source tree layout.

### PR3: Observe and Safe Write-back

- Add `POST /api/sessions`, `POST /api/observe`, and batch observe.
- Add `mb sessions`, `mb observe`, and `mb remember`.
- Allow CLI/agent memory writes without user-provided evidence by creating an
  `inline_agent_note` source document and source chunk.
- Extend `agent_session.channel` with `cli`.
- Extend `source_document.doc_type` with `inline_agent_note`.

### PR4: Lexical-First Agent Search

PR4 starts with zero-configuration lexical search instead of pgvector. It adds
`jieba`-backed Chinese tokenization, PostgreSQL `pg_trgm` fuzzy indexes, and a
search-field backfill path so `mb recall` can benefit from segmented query text
without requiring an embedding provider. PR4b adds `POST /api/search`,
SQL-side RRF over FTS/trigram/title routes, `mb search`, and an adversarial
search gold set under `mb eval recall --gold search`.

Hybrid recall and pgvector remain later work. They require a fair adversarial
eval baseline and a real embedding provider. pgvector stores vectors, but an
embedding model is still required to generate them.

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
active_session = "00000000-0000-0000-0000-000000000000"
actor_type = "agent"
actor_id = "00000000-0000-0000-0000-000000000301"
database_url = "postgresql://memorybase:memorybase@localhost:5432/memorybase_db"
```

`workspace` accepts a UUID or `workspace.slug`. `agent` accepts a UUID or agent
name scoped to the configured workspace.

### Commands

```bash
mb --version
mb configure --api-base http://localhost:8000 --workspace cs3321-demo
mb configure --workspace cs3321-demo --register-agent codex --type editor
mb health
```

PR2 commands:

```bash
mb recall "query"
mb recall "query" --format json
mb context "query" --max-tokens 3000
mb eval recall --format json
```

PR2 adds `tiktoken` for `cl100k_base` token counting in context packs. This keeps
context budgets closer to what shell-capable coding agents actually consume than
character-count approximations.

PR3 commands:

```bash
mb sessions create --title "feature work"
mb sessions create --title "feature work" --print session_id
mb observe --session <id> --role user --content "..."
mb observe --session <id> --role assistant --content "..." --quiet
mb observe --session <id> --batch messages.jsonl
mb observe --session <id> --batch - < messages.jsonl
mb remember "fact" --type decision --reason "..." --dry-run
mb remember "fact" --type decision --reason "..." --commit
```

`mb remember` is dry-run by default. `--commit` is required to write a memory.
If no explicit evidence chunk is supplied, committed agent writes rely on the
backend `inline_agent_note` path so the memory still has source/evidence
provenance.

`mb sessions create` writes `active_session` to CLI config by default; use
`--no-set-active` to opt out. `mb observe` infers sender type from role when
`--sender-type` is omitted: `user` maps to `user`, `assistant` and `tool` map to
`agent`, and `system` maps to `system`.

PR4 commands:

```bash
mb search "为什么放弃校园食堂方向" --workspace cs3321-demo
mb search "cafeteria systm" --workspace cs3321-demo --show-lines
mb eval recall --gold search --format json
mb eval recall --gold all --format json
```

`mb search` defaults to JSON and returns structured chunk/memory/source results.
`--show-lines` is CLI-only and renders grep-like `source_path:start-end:
snippet` rows without changing the `/api/search` request shape.

PR5 context behavior:

```bash
mb context "current task" --session <id> --repo-root .
mb context "current task" --repo-only
```

`mb context` now merges long-term memory, lexical search fallback, recent session
messages, and local repository metadata/snippets into one Markdown pack. Repo
context is collected locally by the CLI and is not uploaded to the backend.

### Output and Exit Codes

- stdout contains the command result only.
- stderr contains logs, metadata, and errors.
- Use `--format json` for machine-parsed output.
- Agent-facing commands default to machine-friendly output: `mb health`,
  `mb recall`, `mb search`, `mb sessions`, `mb observe`, and `mb remember`
  default to JSON, and `mb context` defaults to Markdown context.
- No-result retrieval commands return exit code 4. `mb recall` still writes a
  parseable JSON object with `result_count: 0` and an empty `memories` array so
  shell pipelines can inspect the result safely.

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
