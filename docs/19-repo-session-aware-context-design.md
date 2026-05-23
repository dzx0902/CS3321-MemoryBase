# PR5 Design: Repo and Session Aware `mb context`

## Background

Dogfooding PR4b proved that the `mb` runtime can support a complete agent loop:

```text
configure -> sessions create -> observe -> context/search -> remember
```

The main friction is that `mb context` only renders database recall results. That
works for historical project memory, but it is weak for active coding work:

- it cannot see the current git branch, diff, or changed files;
- it cannot read the current repo files that the agent is about to edit;
- it cannot include the current `agent_session` messages just observed through
  `mb observe`;
- when no database memory matches the task, it exits with code 4 instead of
  still giving the agent useful repo/session context.

The v1 runtime promise is that a shell-capable agent can use MemoryBase smoothly
during real development. PR5 should make `mb context` useful for the "start work
on this repo now" path, not just the "recall old database facts" path.

## Goals

1. Keep `mb context "task"` as the main low-choice command for agents.
2. Combine three context sources into one token-limited Markdown pack:
   - MemoryBase recall (`POST /api/recall/context-pack`)
   - lexical search fallback (`POST /api/search`) when recall returns no memory
   - local repository state and snippets
   - recent session messages from `agent_session` / `message`
3. Preserve the existing stdout/stderr contract:
   - Markdown context to stdout
   - metadata, warnings, and source counts to stderr
4. Make repo context CLI-local. Do not upload local source files to the backend.
5. Make session context backend-backed, because session messages already live in
   PostgreSQL.
6. Avoid LLM dependencies, embeddings, MCP, or long-running background workers.

## Non-goals

- No automatic code summarization by LLM.
- No repo-wide embedding index.
- No persistent file index in PostgreSQL.
- No MCP adapter.
- No replacement for `rg`, `git`, or local agent file-reading tools.
- No automatic memory creation from session messages.

## Proposed UX

Default command:

```bash
mb context "implement wiki batch export" --workspace cs3321-demo --agent codex
```

Default behavior after PR5:

```text
memory recall: enabled
repo context: auto if current directory is inside a git repo
session context: auto if --session is provided or config has active_session
```

Explicit controls:

```bash
mb context "implement wiki batch export" \
  --workspace cs3321-demo \
  --agent codex \
  --session <session-id> \
  --include-repo \
  --include-session \
  --repo-root . \
  --max-tokens 4000

mb context "fix search ranking" --no-repo
mb context "summarize current discussion" --session <id> --no-memory
mb context "what changed locally" --repo-only
```

Recommended option set:

| Option | Default | Meaning |
|---|---:|---|
| `--include-repo / --no-repo` | auto | Include local git/file context. |
| `--include-session / --no-session` | auto | Include recent messages from a session. |
| `--session <uuid>` | none | Session to include. |
| `--repo-root <path>` | auto git root | Root for local repo inspection. |
| `--repo-query <text>` | same as query | Optional separate query for repo file matching. |
| `--repo-limit <n>` | 8 | Maximum local snippets. |
| `--session-limit <n>` | 20 | Maximum recent messages. |
| `--repo-only` | false | Skip memory recall and session context. |
| `--no-memory` | false | Skip MemoryBase recall. |

Do not expose retrieval strategy flags on `mb context`. The command should stay
low-choice; implementation can internally use recall, search, session, and repo
sources.

## Context Pack Shape

`mb context` should render one Markdown document:

```md
# MemoryBase Context

## Current Task
- query: implement wiki batch export
- workspace: cs3321-demo
- agent: codex
- branch: jflin

## Repository State
- branch: jflin
- base: dev
- changed files:
  - backend/app/services/wiki_service.py
  - backend/tests/test_wiki.py

## Session Notes
- [S1] user: ...
- [S2] assistant: ...

## Relevant Memories
- [M1] ...

## Search Results
- [Q1] data/raw_sources/demo.md:10-12 ...

## Repo Snippets
- [R1] backend/app/services/wiki_service.py:30-90
  ...

## Evidence
- [E1] ...

## Known Conflicts / Risks
- ...

## Do Not Assume
- ...

## Metadata
- sources: memory=5, repo=4, session=8
- token_count: 2870
```

The section order is intentional. For active development, current repo/session
state should appear before long-term memory because it is fresher and usually
more actionable.

## Data Sources

### 1. Memory Recall

Reuse existing endpoint:

```http
POST /api/recall/context-pack
```

No backend change is required for memory recall.

Behavior change in CLI:

- if memory recall returns no results but repo/session context exists, `mb
  context` should still exit 0 and render those sources;
- if memory recall returns no results, `mb context` should call `POST
  /api/search` and render search hits before falling back to exit 4;
- only exit 4 when all enabled sources are empty.

### 2. Session Messages

Add one backend endpoint:

```http
GET /api/sessions/{session_id}/messages?workspace_id=<uuid>&limit=20
```

Response:

```json
{
  "items": [
    {
      "message_id": "uuid",
      "session_id": "uuid",
      "sender_type": "user",
      "sender_id": null,
      "role": "user",
      "content": "...",
      "created_at": "..."
    }
  ],
  "total": 12,
  "limit": 20
}
```

Rules:

- validate that the session exists;
- if `workspace_id` is provided, validate that the session belongs to it;
- order by `created_at DESC` in SQL for efficient limit, then reverse in service
  so Markdown is chronological;
- do not include messages from other sessions;
- no pagination needed in PR5, only recent messages.

### 3. Repo Context

Repo context is CLI-local and should never go through FastAPI.

Use boring shell commands through Python subprocess wrappers:

```text
git rev-parse --show-toplevel
git status --short
git branch --show-current
git diff --name-only
git diff --stat
git log --oneline -5
rg --files
rg -n <query terms>
```

If `rg` is unavailable, fall back to Python file scanning over a conservative
extension allowlist.

Repo snippets should be selected in this order:

1. files changed in `git status --short`;
2. files matching query terms through `rg -n`;
3. files from `git diff --name-only`;
4. nearby docs (`AGENTS.md`, `README.md`, `docs/16-19`) if query contains
   `agent`, `context`, `memory`, `runtime`, or `workflow`.

Exclude:

```text
.git/
.venv/
node_modules/
dist/
build/
__pycache__/
*.egg-info/
uv.lock
package-lock.json
```

Snippet shape:

```json
{
  "ref": "R1",
  "path": "backend/app/cli/commands/context.py",
  "start_line": 1,
  "end_line": 80,
  "reason": "changed_file",
  "text": "..."
}
```

## Token Budgeting

Use the existing `count_tokens()` logic from `context_pack_service.py`.

Suggested budget split:

| Source | Target Share | Minimum if present |
|---|---:|---:|
| Repository state summary | 10% | 120 tokens |
| Session notes | 20% | 200 tokens |
| Memory recall | 35% | 300 tokens |
| Repo snippets | 30% | 300 tokens |
| Metadata | 5% | 80 tokens |

If total content exceeds `--max-tokens`, trim in this order:

1. repo snippets not from changed files;
2. older session messages;
3. lower-ranked memories;
4. changed-file snippets;
5. metadata last.

Never truncate in the middle of a line-number header. Prefer dropping a whole
snippet over producing an unusable partial file reference.

## Implementation Plan

### PR5a: Session Message Read API and CLI Session Ergonomics

Files:

- `backend/app/models/conversation.py`
- `backend/app/services/conversation_service.py`
- `backend/app/api/sessions.py`
- `backend/app/cli/commands/sessions.py`
- `backend/app/cli/commands/observe.py`
- `backend/tests/test_observe_api.py`
- `backend/tests/test_cli_recall.py` if client protocol changes are needed

Work:

- add `MessageListResponse`;
- add repository/service `list_messages(session_id, workspace_id, limit)`;
- add `GET /api/sessions/{session_id}/messages`;
- add `MemoryBaseClient.get_session_messages()`;
- add `active_session` config support;
- add `mb sessions create --print session_id`; it writes `active_session` by
  default, with `--no-set-active` as opt-out;
- infer `mb observe` sender type from role when `--sender-type` is omitted;
- add tests for chronological response, workspace isolation, and missing
  session 404.

Acceptance:

- creating a session and two messages, then reading messages returns them in
  chronological order;
- passing the wrong workspace returns 404;
- limit is enforced.

### PR5b1: Local Repo Metadata Collector

Files:

- `backend/app/cli/repo_context.py` (new)
- `backend/tests/test_repo_context_metadata.py` (new)

Work:

- detect git root;
- gather branch, status, diff stat, changed file paths, and recent commits;
- do not read file contents yet;
- return structured `RepoMetadata` object;
- expose non-fatal warnings when `git` is unavailable or the cwd is not inside
  a git repository.

Acceptance:

- in a temp git repo with changed files, collector returns branch, status, diff
  stat, changed paths, and recent commits;
- no git repo returns a non-fatal warning and empty repo context.

### PR5b2: Local Repo Snippet Collector

Files:

- `backend/app/cli/repo_context.py`
- `backend/tests/test_repo_context_snippets.py` (new)

Work:

- select snippets from changed files and `rg` query hits;
- implement conservative extension allowlist and exclude rules;
- implement binary-looking file detection;
- cap bytes per file and lines per snippet;
- keep snippets structured and line-numbered.

Acceptance:

- changed files are preferred over general query hits;
- `rg` hits include line-numbered snippets;
- excludes `.venv`, `node_modules`, `uv.lock`, generated files, and binary-like
  files;
- per-file cap prevents one large file from dominating the context.

### PR5c: Unified `mb context` Renderer

Files:

- `backend/app/cli/commands/context.py`
- `backend/app/cli/client.py`
- `backend/app/cli/context_renderer.py` (new)
- `backend/tests/test_cli_context.py`
- `docs/17-agent-runtime-plan.md`

Work:

- add options listed in this design;
- call memory recall unless `--no-memory` or `--repo-only`;
- call session messages when `--session` is provided;
- call repo collector when repo context is enabled;
- merge sources into one token-limited Markdown output;
- return exit 0 if at least one source contributes content;
- return exit 4 only if all enabled sources are empty.

Acceptance:

- `mb context "task" --repo-only` works without backend memory results;
- `mb context "task" --session <id>` includes recent messages;
- `mb context "task"` inside a git repo includes changed-file summary;
- stdout contains Markdown only; stderr contains source counts and warnings.

## Dogfood Scenario

After PR5, this should work without fallback to manual `rg`:

```bash
mb configure --workspace cs3321-demo --register-agent codex --type editor
SID=$(mb sessions create --title "wiki batch export" | jq -r .session_id)
mb observe --session "$SID" --role user --content "Implement wiki batch export."
mb context "wiki batch export API implementation" \
  --session "$SID" \
  --max-tokens 4000 > /tmp/ctx.md
```

Expected `/tmp/ctx.md` includes:

- current branch and dirty files;
- recent session request;
- relevant MemoryBase memories;
- snippets from wiki API/service/tests/docs;
- line-numbered repo references.

## Risks

1. **Context bloat**: repo snippets can dominate token budget. Mitigation: strict
   snippet count, max chars per snippet, and source budget split.
2. **False confidence from stale repo context**: local files can change after
   context generation. Mitigation: metadata includes branch and git status.
3. **Privacy / accidental file exposure**: CLI may read secrets. Mitigation:
   default excludes plus never uploading repo snippets to backend. Future work
   can add `.memorybaseignore`.
4. **Too many flags**: agent workflows suffer when commands require strategy
   choices. Mitigation: keep defaults useful; flags are opt-out/diagnostic.
5. **Session mismatch**: stale session ids should fail clearly. Mitigation:
   `GET /sessions/{id}/messages` validates workspace.

## Open Questions

Resolved decisions for PR5:

1. `mb sessions create` should write `active_session` to config by default, with
   `--no-set-active` as the explicit opt-out. Dogfooding showed that extracting
   session ids with `jq`/Python is noisy enough to hurt the default agent path.
2. `mb observe` should infer sender type from message role when no explicit
   `--sender-type` is provided: `role=user` stays `user`; `role=assistant` and
   `role=tool` default to `agent`; `role=system` defaults to `system`.
   Explicit `--sender-type` always wins.
3. `.memorybaseignore` is deferred. PR5 uses hard-coded safe excludes first. Add
   ignore-file support only after a real secret/noise case appears.
4. PR5 context should include repo metadata and file snippets, not raw diff hunks.
   Diff hunks are noisy, token-heavy, and already available through `git diff`
   when the agent needs exact patches.

## Recommendation

Implement PR5a and PR5b1 first. They are independently reviewable and low-risk.
Then implement PR5b2, which is the most complex part because it owns file
selection, fallback scanning, binary detection, and token caps. Finally implement
PR5c as the user-facing change. Do not combine session API, repo metadata, repo
snippets, and context renderer into one large PR unless the team explicitly
prioritizes speed over reviewability.
