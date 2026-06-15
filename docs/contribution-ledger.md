# Contribution Ledger

> Scope: this ledger audits commits authored by `hopecommon` / `jflin` identities
> across local and remote branches. It is evidence for the final report section
> "小组分工与个人完成情况". As of the 2026-06-14 refresh, the ledger also
> records Git-backed evidence for the other three observed identities.

## 1. Audit Baseline

Audit date: 2026-06-15 (refreshed from the 2026-06-14 snapshot)

Repository state at audit time:

- Branch: `dev`
- HEAD: `b038e1b docs: organize final submission package`
- Remote refresh command: `git fetch --all --prune`
- Branch status at refresh time: local `dev` == `origin/dev` == `b038e1b` (in sync). All five `Cofstars <2089039907@qq.com>` non-merge commits (`c2b8cd9`, `ee623c7`, `89ca761`, `899530e`, `fa6ecd3`) are now on `origin/dev`.

Refs considered:

- Local: `dev`, `main`
- Remote: `origin/dev`, `origin/main`, `origin/jflin`, `origin/feat/evaluation-benchmark-framework`, `origin/feat/entity-memory-scene`, `origin/frontend-api-integration`, `origin/backend-p0`, `origin/fix/backend-api-contract-demo`, `origin/fix/db-cli-windows-encoding`

Author identities included:

| Identity | Treatment |
|---|---|
| `hopecommon <1841778349@qq.com>` | Primary direct author identity; 65 non-merge commits in the refreshed all-ref audit |
| `evanlin257 <143060834+hopecommon@users.noreply.github.com>` | GitHub noreply identity tied to hopecommon; 14 merge / PR-integration commits plus 2 authored merge-style delivery commits in the refreshed all-ref audit |

Important counting rule:

- Non-merge commits are treated as direct implementation / documentation contributions.
- Merge commits and PR integration commits are tracked separately as integration evidence.
- The large evaluation branch merge is counted as integration/curation unless individual files are authored by hopecommon commits. This avoids overstating original implementation ownership of teammate work.
- Raw commit audit is stored in `docs/contribution-audit-hopecommon.tsv`.

## 2. Reproducible Commands

```bash
git fetch --all --prune

git log --all \
  --regexp-ignore-case \
  --author='hopecommon\|1841778349' \
  --format='%H%x09%h%x09%aI%x09%aN <%aE>%x09%s'

git log --all \
  --regexp-ignore-case \
  --author='hopecommon\|1841778349' \
  --no-merges \
  --shortstat \
  --format='@@@%H%x09%h%x09%aI%x09%aN <%aE>%x09%s'

git log --all \
  --regexp-ignore-case \
  --author='hopecommon\|1841778349' \
  --merges \
  --format='%h %aI %aN <%aE> %s'
```

Branch-contained direct commit counts:

```text
dev                                                  65
origin/dev                                           65
origin/jflin                                         65
main                                                 46
origin/main                                          52
origin/feat/evaluation-benchmark-framework           52
origin/feat/entity-memory-scene                      23
origin/frontend-api-integration                      23
origin/backend-p0                                    20
```

Aggregate result across all refs:

| Metric | Count / value |
|---|---:|
| Related commits across all refs, de-duplicated | 81 |
| Direct non-merge commits | 65 |
| Merge / PR integration commits | 16 |
| Approx. changed files touched by related commits | 301 |
| Approx. aggregate diff across related commits | +59,100 / -3,000 |

The aggregate diff is a rough audit signal, not a grading claim: merges, generated
assets, docs, and reworked lines can inflate totals. The module-level evidence
below is the safer source for the final report.

Refresh note: compared with the 2026-06-10 ledger snapshot, this refresh now
includes the final report body (`3e5c51f`), final defense slides (`251013e`),
the latest benchmark-integration merge (`dfa7adf`), and the five `Cofstars`
non-merge commits now merged to `origin/dev` (source/LLM extraction plus final
report, slides, and audit-artifact refreshes).

## 3. Module-Level Contribution Summary

| Area | Evidence count | Representative files | Contribution summary |
|---|---:|---|---|
| Database schema, SQL, views, triggers, seed/demo data | ~26 commits | `database/01_schema_core.sql`, `database/02_schema_memory.sql`, `database/03_schema_governance.sql`, `database/04_indexes.sql`, `database/05_views.sql`, `database/06_triggers.sql`, `database/07_seed.sql`, `database/08_demo_queries.sql`, `database/10_governance_demo_fixture.sql` | Built and hardened the relational foundation: workspace/user/agent ownership, memory/evidence/revision/audit, conflict/forget governance, semantic entities/scenes, views, indexes, triggers, reproducible seed data, and SQL demo queries. |
| Backend API, services, CLI, tests | ~20 commits | `backend/app/services/*`, `backend/app/api/*`, `backend/app/cli/*`, `backend/tests/test_postgres_integration.py`, `backend/tests/test_graph_service.py`, `backend/tests/test_recall_query.py` | Implemented or hardened source/memory/recall/governance/search/runtime/graph service paths, CLI dogfood flows, context pack generation, agent session writeback, and focused backend tests. |
| Frontend UI and demo polish | ~5 commits | `frontend/src/pages/recall/Recall.jsx`, `frontend/src/pages/wiki/WikiExport.jsx`, `frontend/src/pages/graph/*`, `frontend/src/index.css`, `frontend/src/api/client.js` | Delivered theme polish and targeted UX fixes; integrated graph and recall surfaces needed for final demo evidence. The low count is intentional: core multi-page frontend work is mainly credited to other teammates, while this ledger only claims theme/demo polish and final-report screenshot support. |
| Agent runtime and agent-facing database substrate | ~12 commits across backend/database/docs | `agent_session`, `message`, `backend/app/cli/commands/*`, `backend/app/services/context_pack_service.py`, `docs/process/16-agent-runtime-gap-analysis.md`, `docs/process/17-agent-runtime-plan.md` | Added agent registration, sessions/messages, observe/remember writeback, context pack export, and CLI entry points so MemoryBase can be used by both humans and agents. |
| Governance, provenance, and access-control workflows | ~12 commits across SQL/backend/tests/docs | `memory_evidence`, `memory_revision`, `audit_log`, `access_policy`, `forget_request`, `conflict_record`, `v_agent_visible_memory`, governance API/tests/docs | Implemented the project’s main differentiator: evidence-backed memories, revision/audit trail, conflict/forget governance, and agent-aware visibility. |
| Graph explorer / graph sync hardening | ~1 large feature commit | `backend/app/services/graph_service.py`, `backend/app/api/graph.py`, `frontend/src/pages/graph/*`, `backend/tests/test_graph_service.py` | Added agent-aware graph visibility, Neo4j driver singleton lifecycle, batch `UNWIND` sync, sync audit attribution, frontend graph module split, and graph tests. |
| Search, recall, and context-pack retrieval | ~8 commits | `backend/app/services/recall_service.py`, `backend/app/services/search_service.py`, `backend/app/cli/commands/eval.py`, `data/eval/*`, `frontend/src/pages/recall/Recall.jsx` | Added lexical search infrastructure, recall API/CLI, context pack formatter, retrieval/evaluation seed data, and UI evidence for recall and QA. |
| Evaluation / benchmark integration | Integration plus limited earlier eval CLI work | `backend/app/cli/commands/eval.py`, `data/eval/*`, merged `evaluation/` assets | Teammate-owned area. Hopecommon's contribution is limited to early eval CLI/gold-data support plus final review, merge, conflict resolution, and alignment into the main demo/report story. |
| Final-report materials and evidence assets | ~36 commits | `docs/research-landscape.md`, `docs/innovation-analysis.md`, `docs/final-assets/diagrams/*`, `docs/final-assets/screenshots/*`, `docs/source-sql-appendix.md`, `docs/process/audit-findings.md` | Produced final report support materials and evidence packages: research landscape, innovation analysis, ER/sequence diagrams, screenshot inventory, source/SQL appendix map, and deliverable re-audit. |
| Tooling and reproducibility | 6 commits | `scripts/db_cli.py`, `scripts/import_demo_sources.py`, `pyproject.toml`, `uv.lock`, `AGENTS.md` | Improved reproducible database setup/demo execution, CLI packaging, dependency lockfile, and project workflow guardrails. |

## 4. Representative Commit Evidence

### 4.1 Database and SQL Foundations

| Commit | Date | Evidence |
|---|---|---|
| `fb8faba` | 2026-05-15 | Initial GitHub issue breakdown and project work structure. |
| `209c694` | 2026-05-15 | Preserved owned resources on user delete; early referential integrity hardening. |
| `1dfd643` / `1980ee7` / `a9aa40f` / `18eaef9` | 2026-05-15 to 2026-05-16 | Fixed workspace-scoped source checksums, nullable references, source deletion behavior, wiki/timeline/recall references. |
| `fb2f48e` / `50ea7ab` | 2026-05-16 | Added conflict and forget governance schema, then canonicalized conflict pairs. |
| `1f964d3` | 2026-05-16 | Added recall/governance index alignment. |
| `df6cdf3` | 2026-05-16 | Added governance and provenance views. |
| `3787a7f` / `6fa7974` | 2026-05-16 | Added memory audit/revision triggers and cascade-delete compatibility. |
| `872587d` | 2026-05-16 | Added reproducible seed data. |
| `5958ad0` | 2026-05-22 | Hardened P3 governance database foundations. |
| `30852d6` | 2026-05-21 | Added entity and memory scene model. |
| `7754d50` | 2026-06-03 | Added course-alignment SQL artifacts, BRIN/covering index rationale, governance demo fixture. |

### 4.2 Backend, API, CLI, and Tests

| Commit | Date | Evidence |
|---|---|---|
| `5d428c0` | 2026-05-19 | Aligned backend API contracts and demo flow across backend/data/database. |
| `91a6b35` | 2026-05-21 | Implemented forget request workflow. |
| `a90152c` / `a707094` | 2026-05-22 | Completed P3 governance API workflows and edge-case tests. |
| `ff59638` / `59f2470` | 2026-05-22 | Added API health detail, agent registration, and `memorybase` console scripts. |
| `f86b0f7` / `c20afcc` | 2026-05-22 | Added recall context pack formatter and CLI recall/context/eval commands. |
| `93eac83` / `610d871` | 2026-05-22 | Added observe sessions and inline evidence writeback API/CLI. |
| `e51a500` / `a49fe14` | 2026-05-22 | Added lexical search infrastructure, API, and CLI. |
| `b382b8b` / `25d1a1b` / `ac3f76f` | 2026-05-23 | Hardened agent runtime contracts, session config, repo/session-aware context packs. |
| `6119d36` | 2026-06-02 | Hardened graph service: visibility, driver singleton, batch sync, audit attribution, tests. |

### 4.3 Frontend and Demo Surfaces

| Commit | Date | Evidence |
|---|---|---|
| `914e85d` | 2026-05-24 | Aligned wiki status filter and added UX polish. |
| `95b5da8` / `bb182b4` | 2026-05-25 | Switched the app to the parchment/navy theme and then refined layered warm surfaces. |
| `6119d36` | 2026-06-02 | Added/refined Graph Explorer frontend module and graph routing. |
| `072c376` | 2026-06-08 | Audited frontend source for annotated source appendix and final report evidence. |

### 4.4 Final Deliverables, Report Evidence, and Review Passes

| Commit | Date | Evidence |
|---|---|---|
| `3e5c51f` / `251013e` | 2026-06-10 | Integrated the final report body and added the 16-page final defense slide deck. |
| `db7c101` | 2026-06-08 | Deliverable re-audit pass aligned deliverables with merged HEAD. |
| `ddf1d93` / `8883161` / `055f89c` | 2026-06-08 | Added and reviewed final ER/sequence diagrams, including SVG renderings and schema/API corrections. |
| `9c2594d` | 2026-06-08 | Added research landscape analysis. |
| `b70f789` | 2026-06-08 | Expanded innovation analysis. |
| `072c376` | 2026-06-08 | Mapped annotated source and SQL appendix. |
| `02e51e8` / `1302a5e` | 2026-06-09 | Added screenshot/evidence inventory and complete command-log renderings for the final evidence inventory. |

### 4.5 Evaluation / Benchmark Integration

| Commit | Date | Evidence |
|---|---|---|
| `c20afcc` / `a49fe14` | 2026-05-22 | Added earlier recall/search evaluation CLI entry points and gold data. |
| `2dd0d64` | 2026-06-03 | Integrated the teammate evaluation branch with hybrid retrieval and memory extraction into the main `jflin`/`dev` line; count this as integration, review, and alignment evidence rather than original authorship of the whole framework. |
| `dfa7adf` / `1e9419e` | 2026-06-10 | Performed the later benchmark merge/update pass and merged refreshed `jflin` work back into `origin/dev`; count as integration/review evidence, not sole authorship of the benchmark stack. |
| `origin/dev` `50609db` / `767eb29` / `965ea4a` | 2026-06-06 to 2026-06-09 | Teammate branch added end-to-end benchmark pipeline, official adapters, semantic judging, and resumable LongMemEval evaluation. Hopecommon's role in this ledger is merge review, conflict resolution, and final-report positioning, not original benchmark implementation. |

## 5. Report-Ready Personal Contribution Statement

Suggested final-report wording for member `hopecommon / jflin`:

| Member | Main responsibility | Delivered artifacts | Course requirement coverage |
|---|---|---|---|
| hopecommon / jflin | Project lead; database schema and governance/provenance design; lexical search / context-pack formatter / CLI dogfood; graph hardening; review/merge/integration; final evidence/report materials | Core SQL schema, views, triggers, indexes, seed/demo data; governance/provenance workflows; lexical search infrastructure; recall context-pack formatter; CLI recall/context/eval/sessions/observe/remember commands; graph visibility/sync/audit hardening over the initial Neo4j integration; ER/sequence diagrams; screenshot/test evidence package; research/innovation/source appendix docs | E-R design, relational schema, integrity constraints, SQL views, triggers, indexes, EXPLAIN validation, governance/provenance implementation, backend/CLI implementation, demo screenshots, member contribution evidence |

Expanded paragraph:

> hopecommon / jflin 主要负责 MemoryBase 的数据库主线、治理/溯源模型、agent-facing backend/CLI 能力和最终集成收尾：设计并迭代 `source_document → source_chunk → memory_item → memory_evidence → memory_revision → audit_log` 的 provenance 链路，补齐 conflict / forget / access policy 等 governance 表、视图、触发器和演示数据；同时完整实现 lexical search infrastructure、recall context-pack formatter、CLI recall/context/eval/sessions/observe/remember 命令链和 agent runtime dogfood 配合，并在 lywzc0419 初版 Neo4j Graph Explorer 集成基础上完成 graph visibility/sync/audit 的工程化补强。recall 路径上的 hybrid memory recall、embedding、QA 和 context-pack metadata 由 dzx0902 主导，本人主要协作对齐 API、CLI 和 demo。对同学主责的前端、评测、QA 等模块，主要承担审查、合并、接口对齐、演示证据和报告材料整理，确保各模块收敛成一个可用 SQL 验证、可审计、可权限裁剪、可演示的数据库系统。

If the report needs a shorter one-line version:

> hopecommon / jflin：负责数据库 schema、治理与溯源链路、lexical search / context-pack formatter / CLI dogfood、Graph hardening、审查合并/集成补强，以及最终报告证据资产。

## 6. Cautions for Final Report

Do not overstate these points:

1. The evaluation framework was integrated into `jflin`/`dev`, but its original implementation should be credited primarily to `dzx0902`. In personal contribution text, count hopecommon's role as integration, review, and alignment unless citing specific hopecommon-authored commits.
2. GitHub merge commits by `evanlin257 <143060834+hopecommon@users.noreply.github.com>` often have no direct file diff relative to the merged branch. They are useful process evidence, not implementation-line evidence.
3. The five `Cofstars` non-merge commits (`c2b8cd9`, `ee623c7`, `89ca761`, `899530e`, `fa6ecd3`) are now merged to `origin/dev`, so they are remote-backed evidence and can be cited directly.
4. This refresh now includes raw Git-backed rows for the other observed members, but their responsibility wording is still lighter-weight than the hopecommon deep audit and should not be over-claimed.
5. GitHub issue state was not re-pulled for this refresh; code/docs artifacts and commit history remain the primary evidence.

## 7. Other Member Audit Notes

The same audit method can be reused for other members by changing the author
pattern and storing one TSV per person:

```bash
git log --all --regexp-ignore-case --author='<name-or-email-pattern>' ...
```

Raw audit files created so far:

| Member identity | Raw audit file | Direct commits | Merge / integration commits | Notes |
|---|---|---:|---:|---|
| `hopecommon <1841778349@qq.com>` / `evanlin257 <143060834+hopecommon@users.noreply.github.com>` | `docs/contribution-audit-hopecommon.tsv` | 65 non-merge | 16 merge / PR integration | Project lead, database/governance/provenance, lexical search/context-pack formatter/CLI dogfood, graph hardening, review/merge/integration, final evidence. |
| `lywzc0419 <lzc050419@sjtu.edu.cn>` | `docs/contribution-audit-lywzc0419.tsv` | 8 non-merge | 0 direct merge | Mainly frontend API integration, runtime/governance UI, Neo4j Graph Explorer integration, graph lint/import fixes. |
| `dzx0902 <3575895791@qq.com>` / `dzx0902 <145189098+dzx0902@users.noreply.github.com>` | `docs/contribution-audit-dzx0902.tsv` | 35 non-merge | 15 merge / PR integration | Project bootstrap, P0 backend/tests, evaluation framework, official benchmark adapters/runners, LongMemEval full-run evidence, embedding/hybrid recall, QA, memory extraction, CI/tooling, and integration merges. |
| `Cofstars <2089039907@qq.com>` | `docs/contribution-audit-cofstars.tsv` | 5 non-merge | 0 direct merge | Added source extraction candidate workflow and optional LLM-backed memory extraction pipeline on top of the existing source/memory path, then refreshed final report, slides, and audit artifacts. |

Recommended responsibility split for the final report:

| Member | Primary part to emphasize | Secondary / support wording |
|---|---|---|
| hopecommon / jflin | Database schema, governance/provenance model, SQL evidence, lexical search + recall context-pack formatter + CLI dogfood, agent-runtime CLI/sessions/observe/remember, graph hardening over lywzc0419's Neo4j integration, final report assets | Reviewed and integrated teammate frontend/evaluation/QA work; strengthened cross-module consistency and demo readiness. |
| dzx0902 / dzx | P0 backend, tests, evaluation benchmark framework including LoCoMo / LongMemEval / MemoryAgentBench adapters and LongMemEval full-run evidence, embedding/hybrid recall, memory extraction, QA, CI/tooling | Also contributed project bootstrap, batch memory writes / supersession support, and integration merges. |
| huiyijian / lywzc0419 / lzc | Frontend API integration, runtime/governance UI, multi-page UI wiring, Neo4j Graph Explorer integration | Also fixed graph lint/Ruff import issues and supporting dependencies/config. |
| Cofstars | Source extraction workflow, chunking/test additions, source UI creation/detail flow, optional LLM-backed candidate extraction and related CLI/API/tests, plus final report / slides / audit-artifact refreshes | Git evidence is five non-merge commits on `origin/dev` (2026-06-14); keep the statement proportional to that visible scope. |

Boundary note: the recall/search path is collaborative. Hopecommon mainly owns
lexical search, the recall context-pack formatter, and CLI/dogfood flows; dzx0902
mainly owns hybrid recall, embedding storage/retrieval, QA, and structured
context-pack metadata.

Report-ready draft for `dzx0902` / `dzx`:

> dzx0902 / dzx 主要负责项目初始脚手架与工程化配置、P0 FastAPI 后端和测试体系，并在后续补充 wiki / stats / semantic / governance lifecycle、embedding、hybrid recall、memory lifecycle validation、conflict detection、forgetting verification、context pack metadata、provider-backed QA、batch memory writes 和 explicit supersession 等后端能力；同时实现 evaluation benchmark 框架，包括 LoCoMo / LongMemEval / MemoryAgentBench adapter、datasets、baselines、metrics、runners、semantic judging、checkpoint/resume 和 report generation，并完成 LongMemEval oracle 500-case 工程评测记录。该评测结果主要作为系统能力和限制分析证据，不作为高分榜单卖点。少量前端贡献集中在 runtime/governance review 修正和 Recall/QA client 联调。

Report-ready draft for `huiyijian` / `lywzc0419` / `lzc`:

> huiyijian / lywzc0419 / lzc 主要负责前端 API 集成与运行时/治理页面建设，包括前端路由依赖、API client、布局、Dashboard、governance、memories、recall、sources、wiki、runtime sessions/messages/hybrid search 等页面联调；同时完成 Neo4j Graph Explorer 的前后端集成相关工作，覆盖 graph API/service/model、Neo4j demo SQL、Docker/依赖配置和 README 说明，并修复 graph integration lint / Ruff import 问题。

Additional caution for `dzx0902`: merge / PR integration commits prove account-level
integration activity, not authorship of every merged line. `origin/feat/evaluation-
benchmark-framework` is a real evaluation contribution, but it also contains backend,
docs, and frontend support changes; do not describe all benchmark branch commits as pure
`evaluation/` code. `eb34e592` is visible only on
`origin/fix/db-cli-windows-encoding`, so treat it as branch-level contribution unless
it is later merged.

Identity note: the teammate previously referred to as `huiyijian` maps to the
Git identity `lywzc0419 <lzc050419@sjtu.edu.cn>` in this repository. As of the
refresh, the previously blank fourth-member slot now has Git-backed evidence
under `Cofstars <2089039907@qq.com>`, covering five non-merge commits now on
`origin/dev`.

## 8. Suggested Appendix Snippet

```text
Evidence command:
git log --all --regexp-ignore-case --author='hopecommon\|1841778349' --no-merges --oneline

Audit result:
65 direct non-merge commits, primarily across database/governance/provenance,
agent-facing backend/CLI, graph hardening, review/integration, and final-report
evidence materials.
16 merge / PR integration commits tracked separately.
```

For the final report, use the module table in §3 and the paragraph in §5 rather
than pasting the entire commit list.
