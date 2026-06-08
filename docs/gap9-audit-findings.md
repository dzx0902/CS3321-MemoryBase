# Gap 9 — Re-audit Findings (HEAD 2dd0d64)

## Summary

- Files audited: 26
- High-severity issues: 11
- Medium-severity issues: 27
- Low-severity issues: 30
- Files marked "needs rewrite": `docs/07-system-architecture.md`, `docs/13-final-report-outline.md`
- Schema drift summary: The canonical source is the current `database/` SQL at HEAD `2dd0d64`. The largest drift is that early course docs still describe the pre-merge core: no embedding cache, no rule-based candidate extraction, no graph/QA/evaluation endpoints, and older memory enum values. The current schema adds `memory_embedding`, `source_chunk_embedding`, four memory types (`fact`, `constraint`, `policy`, `summary`), and seven memory statuses (`candidate`, `active`, `archived`, `forgotten`, `superseded`, `rejected`, `conflicted`). Some final-report-facing docs have been updated, but older overview/architecture/test/demo docs still need alignment before they can be reused directly.

## Per-file findings

### docs/00-project-overview.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | §8 still lists "LLM automatic extraction" and semantic retrieval as future, but current HEAD has rule-based extraction endpoints (`/api/memory-extraction/from-chunks`) and embedding cache tables/services for hybrid recall. | medium | Rephrase as: rule-based candidate extraction and JSONB embedding cache are delivered; high-quality LLM extraction and ANN/pgvector retrieval remain future work. |
| report-fit | Title narrows the product to "AI Agent collaboration R&D"; final narrative should be broader organization/team memory database. | medium | Change report-facing title to "AI-native, traceable organizational/team memory database system"; keep agent collaboration as a primary use case. |
| polish | P1/P2 labels say some items are "已实现", while P0/P1/P2 taxonomy is no longer clean after PR #70. | low | Replace stage labels with "delivered core", "delivered extension", and "future extension" for final report reuse. |

### docs/01-requirements.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Functional table omits delivered graph explorer, embedding backfill, QA, stats overview, semantic entity/scene APIs, CLI, and evaluation framework. | medium | Add an "extension capabilities" subsection so final report does not understate completed work. |
| report-fit | Requirements still mark Entity/MemoryScene and ForgetRequest as P2 even though they are implemented in schema/API/frontend and demo fixture. | medium | Move them to delivered governance/semantic requirements; reserve Future for pgvector, production LLM extraction, plugins, and sync ecosystem. |
| polish | The "管理员" role claims user management, but there is no user CRUD API; seed users exist, and agent registration exists. | medium | Rewrite as "manage agents, policies, audit, forgetting, and governance state"; do not claim full user management unless implemented. |

### docs/02-data-flow.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Source import 2-level DFD says "写入 AuditLog", but `PostgresSourceRepository.create_source()` only inserts `source_document` and `source_chunk`; no source import audit trigger exists. | high | Either add source import audit in code later, or change DFD to "memory/wiki/governance operations write AuditLog; source import is visible via source_document/imported_at". For final report, avoid claiming source import audit unless implemented. |
| code-consistency | Recall DFD only shows SourceChunk FTS; current recall also supports memory text keyword fallback and optional vector scoring from `memory_embedding`/`source_chunk_embedding`. | medium | Update Recall DFD to keyword/hybrid path: permission filter -> chunk FTS/trigram + memory text match + optional embedding candidates -> context pack -> recall_log. |
| report-fit | Wiki export DFD says export to `data/markdown_wiki/`, which is true, but final report should show DB write (`wiki_page`, `wiki_page_revision`) before file output. | low | Expand one line to make the DB-first design clearer. |

### docs/03-data-dictionary.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | `memory_type` enum omits `fact`, `constraint`, `policy`, and `summary`, all present in `database/02_schema_memory.sql` and `backend/app/models/memory.py`. | high | Align enum with current canonical list: `episodic`, `semantic`, `fact`, `profile`, `procedural`, `decision`, `preference`, `task`, `risk`, `constraint`, `policy`, `summary`. |
| code-consistency | `status` enum omits `candidate` and `rejected`; these are required by candidate extraction. | high | Align with current `memory_item.status`: `candidate`, `active`, `archived`, `forgotten`, `superseded`, `rejected`, `conflicted`. |
| code-consistency | Data structure dictionary omits `memory_embedding` and `source_chunk_embedding`. | medium | Add embedding cache structures and note JSONB vector cache, not pgvector/ANN. |
| polish | `AuditLog` row says `diff`, but table has `before_json` and `after_json`, not a `diff` column. | low | Rename to `before_json / after_json`. |

### docs/04-er-design.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | ER entities omit `WorkspaceMember`, `memory_embedding`, and `source_chunk_embedding`, all current schema tables. | medium | Add them or explicitly state the diagram is a simplified core ER view. |
| code-consistency | Mermaid relation `MEMORY_ITEM ||--o{ CONFLICT_RECORD : conflicts` only covers one side, while SQL has `left_memory_id` and `right_memory_id`. | low | Show two relationships or label as left/right conflict endpoints. |
| report-fit | Mermaid ER source is useful but not enough for teacher-required visual flow/ER submission. | medium | Export a PNG/SVG into final assets and keep Mermaid as source. |

### docs/05-logical-design.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Relationship schemas omit `memory_embedding` and `source_chunk_embedding`. | medium | Add a "Embedding cache" subsection matching `database/02_schema_memory.sql`. |
| code-consistency | `ConflictRecord` omits `resolved_by_actor_type`, `resolved_by_actor_id`, and `updated_at`, which exist in `database/03_schema_governance.sql`. | medium | Add the missing fields to keep logical design aligned. |
| report-fit | 3NF section says "大部分表满足 3NF" but does not include the newer nuance already captured in `docs/normalization.md`. | low | In final report, import the stronger wording from `docs/normalization.md`: core tables mainly 3NF/BCNF with controlled denormalization. |

### docs/06-physical-design.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | View table says `v_agent_visible_memory` is based on `app.agent_id` and returns nothing if unset. Actual view joins `agent` and returns rows for all agents; callers filter by `agent_id`. | high | Rewrite as: `v_agent_visible_memory` materializes per-agent visibility; service/API must add `WHERE agent_id = ...`. Also fix `database/08_demo_queries.sql` query #5. |
| code-consistency | §9 says `status`新增 only `candidate` and `rejected`, but current status also includes `conflicted`. | medium | Include `conflicted` in the schema-extension note. |
| code-consistency | "保底方案 SQLite + FTS5" is not implemented in repo scripts/tests. | medium | Mark SQLite as earlier design/fallback idea, not delivered capability, or remove from final report unless a working SQLite path is added. |
| report-fit | Physical design is strong and mostly final-report ready. | low | Minor edit only after fixing the view description and SQLite wording. |

### docs/07-system-architecture.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Backend directory tree is stale: it lists `routers/`, `ingest_service.py`, `policy_service.py`, and `audit_service.py`. Current code uses `backend/app/api/`, `source_service.py`, `governance_service.py`, `graph_service.py`, `embedding_service.py`, `llm_service.py`, and many more. | high | Rewrite this file against current `backend/app` layout. |
| code-consistency | Architecture diagram omits CLI, evaluation framework, graph/Neo4j optional store, embedding provider/cache, and QA path. | medium | Add an updated component diagram for Backend API + CLI + PostgreSQL + optional Neo4j + evaluation runners. |
| report-fit | Needs rewrite before final report. | high | Use this file only as a historical draft until rewritten. |

### docs/08-api-design.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | API summary omits current delivered endpoints for `/api/graph/*`, `/api/embeddings/*`, `/api/qa/answer`, `/api/stats/overview`, `/api/entities`, and `/api/scenes`. | medium | Add a concise "extension APIs" section, or explicitly mark this as a selected core API summary. |
| code-consistency | Source import response example omits `workspace_id`/etc. This is acceptable because actual `SourceImportResponse` only returns `doc_id` and `chunk_count`. | low | No functional fix needed. |
| report-fit | Good core API summary and mostly matches current backend for source/memory/extraction/recall/search/wiki/governance/runtime. | low | Reuse in final report after adding omitted endpoint families. |

### docs/09-module-ipo.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | IPO table omits delivered modules: Memory Extraction, Search, Sessions/Observe CLI runtime, Graph, Embeddings, QA, Stats, Semantic entities/scenes, and Evaluation. | medium | Expand table or add a second "extension module IPO" table. |
| report-fit | Too short for final report as-is. | medium | Use as a seed, but rewrite into a fuller module-design section. |

### docs/10-test-plan.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Test plan omits most current test suites: graph, embeddings, evaluation, QA, semantic, stats, CLI context/recall/sessions/writeback, search API, workspace slug, context pack. | medium | Add a coverage matrix keyed to actual `backend/tests/test_*.py`. |
| report-fit | Understates real test coverage and will make the project look weaker. | medium | Rewrite/extend before final report; include latest validation evidence. |
| polish | Expected "delete memory -> archived" is correct for soft delete, but should mention trigger path and audit. | low | Add trigger/audit verification rows. |

### docs/11-demo-script.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | `npm run db:setup` claim is correct: `scripts/db_cli.py reset` loads 00-06, 07 seed, search backfill, 10 fixture, then 08 queries. | low | No issue found for setup command. |
| cross-doc consistency | Demo flow says "进入 Sources 页面，导入 6 份讨论记录", but `db:setup` already seeds the 6 discussion records. | medium | Decide final demo mode: either show pre-seeded Sources, or import a seventh/new source live. Update script accordingly. |
| code-consistency | Required demo data says at least 3 Wiki pages, but this audit did not verify that seed + setup creates 3 wiki pages before app actions. | medium | Verify with `npm run db:setup`/SQL before final screenshots, or change to "create/export 3 wiki pages during demo". |

### docs/13-final-report-outline.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| report-fit | Only a 40-line outline; it is not an integrated final report. | high | Rewrite into `docs/final-report.md` with full chapters, screenshots, diagrams, citations, source/SQL appendix, and member contribution section. |
| report-fit | Title is still narrow ("AI Agent 协作研发"). | medium | Use the broader organization/team memory database title agreed in the roundtable. |
| code-consistency | Innovation list omits evaluation framework, hybrid retrieval with transparent fallback, rule-based candidate extraction, graph explorer, and DB course depth (BRIN/covering/EXPLAIN). | medium | Expand innovation list using current code and supporting docs. |

### docs/normalization.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Mostly aligned with current schema: includes expanded memory enums and embedding tables. | low | No blocking issue found. |
| polish | §1.4 says `current_revision_no` is maintained by `trg_memory_after_update`; actual implementation increments in `trg_memory_before_update`, with after trigger inserting revision. | medium | Adjust wording to `trg_memory_before_update` increments, `trg_memory_after_update` writes revision/audit. |
| report-fit | Strong final-report source; may need shortening. | low | Use as a condensed subsection, with full doc as appendix/reference. |

### docs/index-rationale.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Mostly aligned with `database/04_indexes.sql`; includes embedding indexes, BRIN, covering, B+ tree/B-link explanation. | low | No blocking issue found. |
| polish | §1 says "8 类" but table lists 9 categories after BRIN/Covering were added. | low | Change "8 类" to "9 类". |
| report-fit | Strong final-report source; keep B+ tree/B-link explanation because it directly answers the course concern. | low | Use condensed version in report. |

### docs/explain-analyze.md

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Case 3.2 claims planner can use `idx_audit_target_time = (workspace_id, target_type, target_id, created_at DESC)` for a predicate only on trailing `created_at`. That is suspicious for PostgreSQL B-tree because leading columns are unconstrained; the pasted plan may be from a different index state or needs re-verification. | high | Re-run Case 3 on current DB and either paste the real plan or rewrite as "competing B-tree path only when leading columns are constrained"; keep BRIN demonstration honest. |
| code-consistency | Index coverage summary references `memory_item_memory_id_workspace_id_key`; this unique constraint exists via `UNIQUE(memory_id, workspace_id)`, but `database/04_indexes.sql` does not name it. | low | Clarify it is an auto-created unique index from `database/02_schema_memory.sql`, not a manual index. |
| report-fit | Good but should be treated as evidence only after re-running plans on final demo DB. | medium | Re-validate before screenshot/PDF inclusion. |

### database/00_init.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Defines `pgcrypto` and `pg_trgm`, matching UUID generation and trigram indexes. | low | No issues found. |

### database/01_schema_core.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Core user/workspace/agent/member schema matches backend models and seed. | low | No issues found. |

### database/02_schema_memory.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Current canonical memory schema includes expanded enums and embedding tables; docs that omit these must be updated. | low | No SQL issue found; use this file as canonical source for doc fixes. |
| polish | `source_chunk_embedding` has `chunk_id`, `doc_id`, and `workspace_id`, but no composite FK ensuring chunk/doc/workspace consistency like `memory_embedding` has for memory/workspace. | medium | Consider adding composite uniqueness/FKs for `source_chunk(chunk_id, doc_id)` and `source_document(doc_id, workspace_id)` if you want DB-level tenant consistency for chunk embeddings. This is not required for final report if documented as current design. |

### database/03_schema_governance.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Governance schema matches current API and fixture. | low | No blocking issue found. |
| polish | `wiki_page.status` remains `active/forgotten`; ensure frontend/docs do not use stale/archived values. | low | Already fixed in frontend per prior review; keep docs aligned. |

### database/04_indexes.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Manual indexes align with `docs/index-rationale.md` and current schema. | low | No blocking issue found. |
| report-fit | Good source for DB-course depth; include BRIN, GIN, covering, partial unique, and B+ tree/B-link in final report. | low | No SQL change needed. |

### database/05_views.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| cross-doc consistency | `v_agent_visible_memory` semantics are misdescribed in `docs/06` and misused in `database/08_demo_queries.sql`; the view itself is per-agent materialized visibility, not session-setting dependent. | high | Keep view, but fix docs/demo query to filter `WHERE agent_id = ...`. |
| code-consistency | Views otherwise align with current schema. | low | No view SQL change required for gap 9. |

### database/06_triggers.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Trigger set aligns with memory/wiki/conflict governance lifecycle. | low | No blocking SQL issue found. |
| cross-doc consistency | `docs/02` implies source import writes audit log, but triggers do not cover source inserts. | high | Fix doc or add source audit later. |
| polish | `fn_memory_soft_delete` says workspace cascade allows hard delete by checking workspace existence; this is a deliberate design, but final report should explain it to avoid "delete trigger blocks cascade" confusion. | low | Add a note in final report if discussing soft delete. |

### database/07_seed.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Seed uses current memory enum values and sets up the course demo workspace. | low | No blocking issue found. |
| report-fit | Seed says LLM extraction is not required for MVP, but current system now has rule-based extraction. | low | In final report, distinguish "LLM not required" from "candidate extraction delivered". |

### database/08_demo_queries.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Query #5 sets `app.agent_id` and then selects from `v_agent_visible_memory` without `WHERE agent_id = ...`; the view does not read `app.agent_id`. This can show all agents' visible memories in multi-agent data. | high | Replace with `WHERE agent_id = '00000000-0000-0000-0000-000000000301'` and remove or explain the unused `set_config`. |
| report-fit | Demo queries do not include the newer embedding/hybrid retrieval, graph, or extraction audit paths. | medium | Add optional final-report/demo queries for `memory_embedding`, `recall_log.context_pack_json->'retrieval_info'`, and `audit_log` extraction run events. |

### database/10_governance_demo_fixture.sql

| Dimension | Issue | Severity | Suggested fix |
|---|---|---|---|
| code-consistency | Fixture is transaction-wrapped, idempotent, and matches current governance schema. | low | No blocking issue found. |
| cross-doc consistency | Comment references `docs/governance-demo-walkthrough.md (如有)`, but that file does not exist. | low | Either add the walkthrough later or remove the reference before final submission. |
| polish | Fixture inserts a resolved conflict directly to avoid marking endpoints conflicted; that is valid but should be described as demo fixture design, not the normal conflict lifecycle. | low | Mention in final report/demo notes if using it as evidence. |

## Cross-doc inconsistencies

- `docs/03-data-dictionary.md` lists `memory_type` as `episodic/semantic/profile/procedural/decision/preference/task/risk`, while `docs/08-api-design.md`, `docs/normalization.md`, and `database/02_schema_memory.sql` include `fact/constraint/policy/summary`. Resolution: `database/02_schema_memory.sql` wins; update `docs/03`.
- `docs/03-data-dictionary.md` lists memory `status` as `active/archived/forgotten/superseded/conflicted`, while `docs/08-api-design.md`, `docs/normalization.md`, and `database/02_schema_memory.sql` include `candidate` and `rejected`. Resolution: current schema wins; update `docs/03`.
- `docs/06-physical-design.md` and `database/08_demo_queries.sql` treat `v_agent_visible_memory` as `app.agent_id`-driven, while `database/05_views.sql`, `recall_service.py`, `search_service.py`, `graph_service.py`, and `governance_service.py` all explicitly filter `agent_id`. Resolution: services/current view semantics win; update doc and demo query.
- `docs/02-data-flow.md` says Source import writes `AuditLog`, while `backend/app/services/source_service.py` and `database/06_triggers.sql` do not implement source import audit. Resolution: either implement source audit in a later gap or remove that claim from DFD/final report.
- `docs/00-project-overview.md` and `docs/01-requirements.md` frame LLM/semantic extraction as future-only; `docs/08-api-design.md` and `memory_extraction_service.py` now deliver rule-based candidate extraction. Resolution: final report should say rule-based v1 is delivered; high-quality LLM extraction/v2 analysis tables remain planned.
- `docs/07-system-architecture.md` lists obsolete backend paths (`routers/`, `ingest_service.py`, `policy_service.py`, `audit_service.py`), while current code lives under `backend/app/api/` and consolidated services such as `source_service.py`, `governance_service.py`, `graph_service.py`, `embedding_service.py`, and `llm_service.py`. Resolution: rewrite `docs/07`.
- `docs/11-demo-script.md` says the demo imports 6 discussion records after `npm run db:setup`, while `database/07_seed.sql` already seeds those records. Resolution: final demo should choose pre-seeded display or a live extra import.
- `docs/10-test-plan.md` covers only early Source/Memory/Recall/Wiki/Audit tests, while `backend/tests/` now covers graph, embeddings, evaluation, QA, semantic, stats, CLI, search, and context pack. Resolution: expand test plan from actual test files.

## Schema drift

Canonical source wins in this order for final report claims: `database/*.sql` for schema/index/view/trigger facts, `backend/app/models` and `backend/app/api` for API contract facts, `backend/app/services` for behavioral facts, and `backend/tests` for test coverage facts.

Drift to fix before final report:

- Memory enums: use the current 12 memory types and 7 memory statuses from `database/02_schema_memory.sql`.
- Embedding cache: include `memory_embedding` and `source_chunk_embedding` in logical/physical/data-dictionary docs.
- Agent visibility: describe `v_agent_visible_memory` as a per-agent view requiring caller-side `agent_id` filtering, not as a view reading `app.agent_id`.
- Candidate extraction: document `memory_item(status='candidate')` + `memory_evidence` + run-level `audit_log` as delivered v1; keep three-table LLM analysis design as future only.
- Architecture/API scope: add graph, embeddings, QA, stats, semantic, CLI, and evaluation as delivered extensions or clearly mark API docs as selected core summary.
- Source audit: either add source import audit later or remove current DFD claim.

## Files marked "needs rewrite"

### docs/07-system-architecture.md

This file is too stale to enter the final report. It points to non-existent `routers/` and service filenames and omits major delivered modules. Proposed outline: (1) current component architecture, (2) backend API/service/repository layout, (3) frontend pages, (4) CLI runtime, (5) PostgreSQL + optional Neo4j graph sync, (6) embedding/QA/evaluation extension paths, (7) data/control flow across these layers.

### docs/13-final-report-outline.md

This file is only an outline, not a deliverable report. It also under-represents the latest merged work. Proposed rewrite outline: full report with database-first mixed narrative, teacher checklist, requirements, related work, schema/ER/logical/physical design, normalization, index/EXPLAIN, API/module design, implementation, governance/provenance/evaluation innovations, screenshots, tests, member contributions, and source/SQL appendices.
