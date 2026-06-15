# Screenshot and Evidence Inventory

This directory contains report/PPT-ready screenshots captured from the final demo
workspace on 2026-06-09.

## Runtime Used

- Branch: `jflin`
- Capture baseline commit: `072c376`
- Database setup:
  - `docker compose up -d postgres`
  - `npm run db:setup`
  - `npm run db:run -- database/09_graph_demo.sql`
- Backend: `../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend/`
- Frontend: `npm run dev -- --host 127.0.0.1 --port 5173` from `frontend/`
- Core demo workspace: `00000000-0000-0000-0000-000000000201`
- Graph demo workspace: `00000000-0000-0000-0000-000000002201`

## UI Screenshots

| File | URL / Action | What It Proves | Suggested Use |
|---|---|---|---|
| `ui/01-dashboard.png` | `/` | Demo data is loaded: sources, memories, wiki, recall, policies, conflicts, audit, forget requests. | Report §16 overview; PPT opening demo slide |
| `ui/02-sources-list.png` | `/sources` | Seeded discussion documents are visible as SourceDocument rows. | Source import / data input |
| `ui/03-source-detail-project-pivot.png` | `/sources/00000000-0000-0000-0000-000000000501?workspace_id=...0201` | Source detail shows raw document metadata and chunk line ranges. | Provenance chain |
| `ui/04-memories-list.png` | `/memories` | MemoryItem list exposes type, status, importance, workspace, and updated time. | Memory management |
| `ui/05-memory-detail-evidence-revisions.png` | `/memories/00000000-0000-0000-0000-000000000701?workspace_id=...0201` | A memory can be traced to evidence and revision history. | MemoryEvidence / MemoryRevision demo |
| `ui/06-recall-search-results.png` | `/recall`, query `为什么放弃校园食堂系统？`, Search | Recall returns the expected cafeteria-topic answer with retrieval info and recall id. | Main recall demo |
| `ui/07-recall-context-pack.png` | Same query, Context Pack | Recall results are converted into agent-ready Markdown context. | Agent integration / context pack |
| `ui/08-recall-qa-answer-or-config-state.png` | Same query, Ask with `LLM_PROVIDER=deepseek` | Optional QA path works when an OpenAI-compatible LLM provider is configured; the screenshot shows `deepseek`, `deepseek-v4-flash`, 4 supporting memories, and cited answer text. | Optional QA / LLM integration |
| `ui/09-governance-timeline.png` | `/governance/timeline` | TimelineEntry projects project history into a human-readable view. | Timeline / project evolution |
| `ui/10-governance-audit.png` | `/governance/audit` | AuditLog records memory lifecycle events and actor attribution. | Audit/governance |
| `ui/11-governance-policies.png` | `/governance/policies` | AccessPolicy rows define agent-visible resource scopes. | Agent-aware visibility |
| `ui/12-governance-conflicts.png` | `/governance/conflicts` | ConflictRecord shows open and resolved memory conflicts. | Conflict governance |
| `ui/13-governance-forget-requests.png` | `/governance/forget-requests` | ForgetRequest workflow keeps forgotten targets auditable. | Forget governance |
| `ui/14-wiki-export.png` | `/wiki` | Wiki pages/export settings expose Markdown projection from database memory. | Wiki projection |
| `ui/15-graph-explorer-demo-workspace.png` | `/graph`, click `Use Graph Demo` | PostgreSQL graph preview renders the curated graph workspace; Neo4j is transparently optional/disabled. | Graph Explorer |
| `ui/16-runtime-sessions.png` | `/runtime/sessions` | Agent runtime sessions and messages are persisted. | Agent runtime |
| `ui/17-runtime-messages.png` | `/runtime/messages` | Runtime message recording UI is available. | Agent runtime write path |
| `ui/18-runtime-hybrid-search-results.png` | `/runtime/search`, query `why abandoned cafeteria project`, Run Hybrid Search | Search returns chunk/memory results with RRF-style strategies such as `memory_fts`, `chunk_fts`, `trigram_fuzzy`. | Hybrid search / retrieval |
| `ui/19-llm-not-used.png` | `/sources/{id}`, select 3 chunks, keep `Use LLM` unchecked, Extract Candidates | Default rule-based extraction classifies the demo sentences into `decision` / `task` / `constraint` with lower confidence. | Report AI comparison |
| `ui/19-llm-used.png` | Same page, check `Use LLM`, fill Qwen-compatible provider fields, Extract Candidates | Optional LLM extraction classifies the same sentences into `decision` / `decision` / `policy` with higher confidence while keeping the same candidate-review workflow. | Report AI comparison |

Additional raw pre-interaction captures are kept as `ui/15-graph-explorer.png` and
`ui/18-runtime-hybrid-search.png`; prefer the `*-demo-workspace` and `*-results`
versions for final materials.

## SQL / EXPLAIN Evidence

| File | Source Log | What It Proves | Suggested Use |
|---|---|---|---|
| `sql/01-db-check.png` | `logs/db-check.txt` | `npm run db:check` succeeds; 25 core tables plus demo/graph workspace data are present. | Test/result appendix |
| `sql/02-demo-queries.png` | `logs/demo-queries.txt` | `database/08_demo_queries.sql` runs and returns broad demo query results. | SQL demo appendix |
| `sql/03-explain-analyze.png` | `logs/explain-cases.txt` | EXPLAIN shows `Index Only Scan`, `Heap Fetches: 0`, `BitmapOr`, GIN FTS/trigram, and BRIN paths. | Physical design / index chapter |
| `sql/04-focused-sql-evidence.png` | `logs/focused-sql.txt` | Concise SQL proof for provenance, visibility, governance states, conflict records, and recall logs. | Main report §16 / PPT SQL slide |

The matching `.svg` files are also included for sharper scaling in slides/PDFs.
PNG command-output screenshots are rendered directly from the full files in
`logs/`, with long lines wrapped for readability, so they preserve the complete
command output instead of relying on clipped thumbnail previews.

## Test / Build Evidence

| File | Source Log | What It Proves | Suggested Use |
|---|---|---|---|
| `tests/01-pytest-core.png` | `logs/pytest-core.txt` | Backend focused subset passes: `test_health.py`, `test_recall_query.py`, `test_graph_service.py` (`16 passed`). | Test plan/results chapter |
| `tests/02-frontend-build.png` | `logs/frontend-build.txt` | React/Vite production build succeeds. | Frontend validation |

## Notes and Caveats

- `ui/08-recall-qa-answer-or-config-state.png` was captured with optional DeepSeek
  QA configuration (`LLM_PROVIDER=deepseek`,
  `DEEPSEEK_CHAT_MODEL=deepseek-v4-flash`).
  The API key was supplied out-of-band for the capture and is not stored in this
  repository. Without an LLM provider, the stable demo path remains Recall +
  Context Pack.
- `ui/19-llm-used.png` was captured with an optional Qwen-compatible analysis
  provider (`base_url=https://dashscope.aliyuncs.com/compatible-mode/v1`,
  `model=qwen-plus`, `provider=qwen`).
  The API key was also supplied out-of-band. Without an external provider,
  `ui/19-llm-not-used.png` remains the default stable extraction path.
- Neo4j is disabled in the local capture. This is expected: Graph Explorer falls back
  to PostgreSQL graph preview and displays the disabled state explicitly.
- The `logs/` directory contains the full command outputs. SQL/test PNG files are
  complete direct renderings of those logs; long lines are wrapped instead of
  clipped.
