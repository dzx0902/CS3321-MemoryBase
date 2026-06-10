# MemoryBase Diagrams (gap 5)

Mermaid sources (`.mmd`) and rendered SVG outputs for the final report and PPT.

## How to re-render

```bash
npm install -g @mermaid-js/mermaid-cli
cd docs/final-assets/diagrams
for f in *.mmd; do
  mmdc -i "$f" -o "${f%.mmd}.svg" -t neutral -b white
done
```

Use SVG outputs for PDF/PPT embedding (vector quality). Keep `.mmd` sources
as the source of truth; regenerate SVGs after edits.

## Diagram index

| File | Type | Purpose | Where to use in the report |
|---|---|---|---|
| `01-er-core.{mmd,svg}` | erDiagram | Simplified 8-entity ER with attribute boxes (Workspace / SourceDocument / SourceChunk / MemoryItem / MemoryEvidence / MemoryRevision / WikiPage / AuditLog) | §3 概念结构设计 — opening figure |
| `02-er-full.{mmd,svg}` | erDiagram | Full 25-entity ER with the main persisted and logical relationships covering core + governance + semantic + runtime. Generic principal and polymorphic audit/forget targets are described in text rather than drawn exhaustively. | E-R 完整图 / 附录 |
| `03-source-to-wiki.{mmd,svg}` | sequenceDiagram | End-to-end business sequence: import → chunk → extract candidate → approve → evidence → revision → wiki export. Includes trigger-driven memory revision and wiki revision audit writes. | §4 数据流图 / §6 系统实现章节 |
| `04-recall.{mmd,svg}` | sequenceDiagram | Recall path: caller → permission filter (`v_agent_visible_memory` when `agent_id` is provided, otherwise public/project fallback) → lexical (GIN) + optional vector (JSONB embedding cache) → context pack + provenance → `recall_log` with `retrieval_info` (mode/fallback_reason). | §6 Recall 模块 / §7 创新点 hybrid retrieval |
| `05-governance.{mmd,svg}` | sequenceDiagram | Three governance flows in one diagram: (A) conflict create → trigger flag → resolve/ignore, (B) forget request → approval/done → soft-forget, (C) memory revision via triggers (`trg_memory_before_update`, `trg_memory_after_update`). | §7 创新点 / governance 章节 |
| `06-memory-status.{mmd,svg}` | stateDiagram-v2 | `memory_item.status` lifecycle (7-state CHECK constraint): candidate → active → archived/forgotten/superseded/rejected/conflicted, with service-validated and trigger-driven transitions. | 附录 / status 状态机 |

## Canonical sources

- ER entities and relationships: `database/01_schema_core.sql`, `02_schema_memory.sql`, `03_schema_governance.sql`.
- Recall path: `backend/app/services/recall_service.py` + `database/05_views.sql` (v_agent_visible_memory).
- Governance triggers: `database/06_triggers.sql`.
- Status enum: `database/02_schema_memory.sql` CHECK constraint on `memory_item.status`.

When the schema changes, re-verify diagrams against the SQL canonical source.
