# Gap 9 — Audit Review (claude pass on codex findings)

**Reviewer**: claude
**Auditee**: codex (`docs/gap9-audit-findings.md`)
**HEAD**: `2dd0d64`
**Verdict**: **APPROVED — accurate findings, ready for fix execution after addressing supplements below.**

## 1. Spot-check verification (7 high-severity claims)

| Finding | Verified against | Status |
|---|---|---|
| `v_agent_visible_memory` joins `agent`, requires caller-side `WHERE agent_id` | `database/05_views.sql:179-230` | ✓ confirmed |
| `memory_type` has 12 values incl. fact/constraint/policy/summary | `database/02_schema_memory.sql:61-77` | ✓ confirmed |
| `memory_item.status` has 7 values incl. candidate/rejected/conflicted | `database/02_schema_memory.sql:86-97` | ✓ confirmed |
| docs/07 references obsolete `routers/` + ingest_/policy_/audit_service | `ls backend/app/` shows `api/` + `source_service/governance_service/...` | ✓ confirmed |
| `source_service.py` does NOT write audit_log | `grep audit_log backend/app/services/source_service.py` = empty | ✓ confirmed |
| `trg_memory_before_update` (not after) maintains `current_revision_no` | `database/06_triggers.sql:107,116` | ✓ confirmed |
| `database/08_demo_queries.sql` query #5 misuses view | docs/08 + view definition | ✓ confirmed |

All 7 hold.

## 2. Push-back / nuance

### 2.1 `docs/explain-analyze.md` Case 3.2 — re-classify high → medium

Codex flags Case 3.2 (`idx_audit_target_time` trailing-column scan) as **high**. The doc itself is honest about the composite index structure and acknowledges the planner choice at small scale (lines 247, 295-301). The real risk is just that the pasted EXPLAIN may have come from a different DB state. **Action**: re-run Case 3 on fresh `npm run db:setup` before final-report inclusion — not a "rewrite" item. Re-classify as **medium with "verify before report inclusion" tag**.

### 2.2 `docs/03-data-dictionary.md` — extend sweep beyond two enum rows

Codex flags `memory_type` and `status` enum rows. Spot-check confirms drift, but codex's row-level fix doesn't mandate a full doc sweep. The doc is 80+ lines; other rows (e.g., data structure summary, AuditLog column names already flagged) likely have similar drift. **Action**: gap 9 fix pass on docs/03 must sweep entire doc, not just enum rows.

## 3. Supplements — what codex did not call out

### S1. SQL inline comment density is materially deficient

Teacher slide explicitly requires **"具有注释的源程序，包括高级语言、SQL 语言等"**. Codex marked all SQL files "no issues found" on code-consistency, but did not assess comment density. I counted leading-whitespace `--` comment lines per file:

| File | lines | comment lines | density |
|---|---|---|---|
| 01_schema_core.sql | ? | **0** | ⚠ |
| 02_schema_memory.sql | 221 | **0** | ⚠ |
| 03_schema_governance.sql | ? | **0** | ⚠ |
| 04_indexes.sql | ? | 18 | OK |
| 05_views.sql | ? | **0** | ⚠ |
| 06_triggers.sql | 337 | **0** | ⚠ |
| 07_seed.sql | ? | 3 | thin |
| 08_demo_queries.sql | ? | 13 | OK |
| 10_governance_demo_fixture.sql | ? | 66 | OK |

**Five core SQL files (schema_core / schema_memory / schema_governance / views / triggers) have zero line comments.** For the SQL-program-with-comments appendix requirement, these must be annotated before submission. **Add to gap 8 task scope: SQL annotation pass on the five files above.** Bare minimum: `--` block above each CREATE TABLE / INDEX / VIEW / TRIGGER explaining its purpose, business meaning, and any non-obvious design choice.

### S2. Report-readiness disposition map (no such overview in findings)

Codex's per-file findings (26 files × 2-4 rows) are dense. Stanley needs an at-a-glance view of "what to do with each file before report assembly":

| File | Disposition | Pre-report action |
|---|---|---|
| docs/00 | reusable + edit | retitle to broader org/team memory; relabel P0/P1/P2 |
| docs/01 | reusable + edit | add extension capabilities; reclassify Entity/Scene/Forget; trim admin role |
| docs/02 | reusable + edit | fix source-import audit claim; update Recall DFD with hybrid path |
| docs/03 | partial rewrite | full-doc sweep for enum/type drift; add embedding cache |
| docs/04 | source OK, render needed | Mermaid is good; claude renders to PNG/SVG in gap 5 |
| docs/05 | reusable + edit | add embedding cache section; fill ConflictRecord missing fields |
| docs/06 | reusable + edit | fix v_agent_visible_memory description; mark SQLite as design-only |
| docs/07 | **REWRITE** | full re-author against current `backend/app/`; add CLI/graph/embed/QA |
| docs/08 | reusable + edit | add extension API families (graph/embeddings/QA/stats/semantic) |
| docs/09 | partial rewrite | add Extraction/Search/CLI/Graph/Embedding/QA/Stats/Semantic/Eval modules |
| docs/10 | partial rewrite | rebuild coverage matrix against actual `backend/tests/test_*.py` |
| docs/11 | reusable + edit | reconcile seed-vs-import for 6 records; verify 3 wiki pages exist post-setup |
| docs/13 | **REWRITE → final-report.md** | this IS gap 1 |
| docs/normalization.md | reusable + edit | fix `trg_memory_before/after` wording (§1.4) |
| docs/index-rationale.md | reusable + edit | "8 类" → "9 类" |
| docs/explain-analyze.md | re-verify | re-run Case 3 + 4 on current DB; refresh plans |
| db/00-07 + 10 | no SQL change for gap 9 | use as canonical for doc fixes; **gap 8 will add comments** |
| db/08_demo_queries.sql | small fix | query #5 `WHERE agent_id = ...` |

**Two REWRITE items (docs/07, docs/13) are the highest-leverage edits.** docs/13 is the report itself (gap 1); docs/07 must be rewritten BEFORE report assembly because gap 1 will reference it.

### S3. ER rendering toolchain decision needed

Codex says "export PNG/SVG into final assets" but doesn't specify the toolchain. **Decision needed before gap 5**:

- (a) **`mermaid-cli` (`mmdc`)** — keeps `.mmd` source in repo, deterministic re-render, no manual web steps. Requires Node + Chrome/Puppeteer.
- (b) dbdiagram.io — manual web export, no toolchain
- (c) drawio offline — manual editing
- (d) Mermaid embedded in PDF via Pandoc + mermaid-filter

**Recommend (a)** for source-of-truth in repo + reproducibility. Confirm in gap 5 kickoff.

### S4. `docs/governance-demo-walkthrough.md` — referenced but absent

`database/10_governance_demo_fixture.sql` references `docs/governance-demo-walkthrough.md (如有)` but the file doesn't exist. Codex flags as low; I think it's medium because it interacts with gap 4 screenshots: the walkthrough would list the exact UI steps to capture. **Recommend**: write the walkthrough as part of gap 1's demo section (or as a sibling doc) BEFORE gap 4 screenshots.

### S5. Gap ordering: gap 9 fixes MUST land before gap 4 screenshots

Implication codex didn't make explicit: if we screenshot the demo with docs/02 claim "source import writes AuditLog" still in the report but the system doesn't, the screenshots will visibly contradict the report. **Hard constraint**: complete gap 9 doc-fix pass BEFORE gap 4 starts. The current task dependency graph (`#21 blocks #30 blocks #22/23/24/26/29`) is correct.

### S6. docs/07 rewrite must verify frontend page list

Codex flags docs/07 stale paths and obsolete service names. Cross-checking, `frontend/src/pages/` contains: `Dashboard.jsx, governance/, graph/, memories/, recall/, runtime/, sources/, wiki/`. docs/07's frontend list (Dashboard / Sources / Memories / Recall / Wiki / Timeline / Audit / Conflicts) **omits the new graph/runtime pages and inaccurately splits Timeline/Audit/Conflicts as top-level pages** (they actually live under governance/runtime). When rewriting docs/07, explicitly verify against `ls frontend/src/pages/`.

## 4. Priority ordering for fix execution

Recommend three tiers; execute Tier A first since they block gap 1 + gap 4.

**Tier A (blocks gap 1 report assembly + gap 4 screenshots):**

1. docs/07 full rewrite (against current `backend/app/` + `frontend/src/pages/`)
2. docs/03 enum + embedding full-doc sweep
3. docs/02 source-import audit claim fix
4. docs/06 v_agent_visible_memory description + SQLite wording
5. database/08 query #5 `WHERE agent_id` fix
6. docs/normalization.md `trg_memory_before/after` wording

**Tier B (improves report quality, gap 1 can start in parallel):**

7. docs/00 title + label cleanup
8. docs/01 extension capabilities + Entity/Scene/Forget reclassification + admin role rewrite
9. docs/05 embedding cache + ConflictRecord missing fields
10. docs/08 extension API families
11. docs/09 module table expansion
12. docs/10 test coverage matrix rebuild
13. docs/11 demo seed-vs-import reconciliation + 3-wiki verification

**Tier C (polish, can land anytime before submission):**

14. docs/index-rationale "8 类" → "9 类"
15. docs/explain-analyze re-run Case 3 + Case 4 on fresh DB
16. docs/04 add WorkspaceMember + embeddings or note "simplified core ER"
17. database/10 dangling `docs/governance-demo-walkthrough.md` reference (or write the walkthrough)

**docs/13 → docs/final-report.md is NOT in this list — that IS gap 1 (Task #22), not a gap 9 fix.**

## 5. Execution mode recommendation

Stanley to choose between two modes for Tier A/B:

- **(α) Batch fix → single review**: codex executes all Tier A in one pass, claude reviews entire result, stanley approves. **Recommend for Tier A** — these are mechanical drift fixes with clear canonical sources (`database/*.sql` and `backend/app/*` are the truth). Per-file review on mechanical fixes is overkill.
- **(β) Per-file fix → per-file review**: slower but more careful. **Recommend for docs/07 rewrite specifically** — this is structural rework where claude should review the new outline before codex commits the rewrite.

**Suggested split**: Tier A items 2/3/4/5/6 batch via (α); docs/07 rewrite (item 1) via (β) with structural outline review first.

## 6. Open questions for stanley

1. **mermaid-cli OK for ER rendering?** (vs dbdiagram.io / drawio / pandoc-mermaid)
2. **Write `docs/governance-demo-walkthrough.md`?** (mid-S4)
3. **Execution mode**: accept the (α)+(β) split in §5, or different?
4. **gap 8 scope expansion**: confirm SQL annotation pass on 5 schema files (S1) is added to Task #29 gap 8.

## 7. Approval gate

Gap 9 audit + this review are **complete**. Approval to proceed = stanley answers §6, then codex starts Tier A fixes. Task #21 + #30 can close once stanley approves.
