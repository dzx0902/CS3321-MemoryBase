# PR4 Lexical-First Agent Search Design

## 1. Goal and Direction

PR4 should make MemoryBase easier for shell-capable agents to search without
requiring an embedding model, OpenAI API key, Ollama setup, MCP adapter, or
PostgreSQL language extension.

The selected direction is lexical-first search:

- Python `jieba.cut_for_search()` segments Chinese and mixed Chinese/English
  text during write/backfill.
- PostgreSQL stores the segmented text and indexes it with native full-text
  search.
- PostgreSQL `pg_trgm` indexes the original text for typo/fuzzy search.
- Multi-route results are fused with Reciprocal Rank Fusion (RRF) inside SQL.
- Embedding and pgvector remain future optional providers, not PR4 defaults.

This keeps the v1 agent runtime promise: a fresh checkout can be useful through
`mb search`, `mb recall`, and `mb context` with no external model service.

## 2. Command Boundaries

PR4 keeps three command responsibilities separate.

| Command | Level | Purpose | Output shape |
|---|---|---|---|
| `mb search` | Source/chunk-oriented | Grep-like evidence discovery with file path and line ranges | JSON by default; grep-like text with `--show-lines` |
| `mb recall` | Memory-oriented | Return governed `MemoryItem` facts/decisions/rules with evidence | JSON |
| `mb context` | Context-oriented | Render recall results as token-limited Markdown | Markdown |

`--show-lines` is CLI-only. It must not appear in `POST /api/search` because it
is presentation behavior, not retrieval semantics. The API always returns
structured data: `source_path`, `start_line`, `end_line`, `snippet`, `score`,
and `strategies`. The CLI decides whether to render that as JSON or grep-like
text.

`mb context` does not expose `--strategy`. Context generation should remain a
low-choice agent workflow: recall decides how to retrieve, and context renders
the returned memories.

## 3. API Shape

Add `POST /api/search` as a new additive endpoint.

Request:

```json
{
  "workspace_id": "00000000-0000-0000-0000-000000000101",
  "agent_id": "00000000-0000-0000-0000-000000000301",
  "query_text": "为什么放弃校园食堂方向",
  "scope": "all",
  "limit": 10
}
```

Rules:

- `scope` values: `all`, `chunks`, `memories`, `sources`.
- `agent_id` is optional.
- No `show_lines` field.
- No user-selected `strategy` field in v1.

Response:

```json
{
  "query_text": "为什么放弃校园食堂方向",
  "tokenized_query": "为什么 放弃 校园 食堂 方向",
  "result_count": 2,
  "items": [
    {
      "result_type": "chunk",
      "result_id": "00000000-0000-0000-0000-000000000502",
      "source_path": "data/raw_sources/demo_workspace/discussion_01_project_pivot.md",
      "source_title": "Discussion 01: Project Pivot",
      "start_line": 8,
      "end_line": 12,
      "snippet": "The cafeteria system was too CRUD-heavy...",
      "score": 0.0311,
      "strategies": ["chunk_fts", "trigram_fuzzy"]
    }
  ]
}
```

## 4. Search Fields and Storage

Only one new search text field is needed per indexed text-bearing table:
`search_text_zh`.

Do not add `search_terms`. Trigram can index the original text directly, and a
second token-list field would duplicate `search_text_zh` or require a separate
keyword-extraction algorithm that PR4 does not need.

### 4.1 Segmentation Example

Input text:

```text
为什么放弃校园食堂方向
```

Python:

```python
" ".join(jieba.cut_for_search("为什么放弃校园食堂方向"))
```

Illustrative `cut_for_search()` output:

```python
["为什么", "放弃", "校园", "食堂", "方向"]
```

Expected stored shape:

```text
为什么 放弃 校园 食堂 方向
```

Index query:

```sql
WHERE search_vector @@ plainto_tsquery('simple', '校园 食堂')
```

The exact token sequence is owned by `jieba.cut_for_search()`. Tests should
assert behavior through representative containments rather than depending on
every token boundary.

### 4.2 Columns

Use generated `tsvector` columns instead of functional indexes.
`source_chunk` already has a generated `search_vector` column and the
`idx_source_chunk_fts` GIN index. PR4 should upgrade that existing column's
meaning instead of adding a parallel `search_text_zh_tsv` column.

```sql
ALTER TABLE source_chunk
  ADD COLUMN IF NOT EXISTS search_text_zh TEXT,
  DROP COLUMN IF EXISTS search_vector,
  ADD COLUMN search_vector TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('simple', coalesce(search_text_zh, ''))) STORED;

ALTER TABLE memory_item
  ADD COLUMN IF NOT EXISTS search_text_zh TEXT,
  ADD COLUMN IF NOT EXISTS search_vector TSVECTOR
    GENERATED ALWAYS AS (to_tsvector('simple', coalesce(search_text_zh, ''))) STORED;
```

If PR4 expands source/entity/scene search in the same PR, use the same pattern
for the selected table. Avoid introducing a different search representation.

### 4.3 Indexes

`pg_trgm` must be declared in `database/00_init.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_source_chunk_fts
  ON source_chunk USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_memory_fts
  ON memory_item USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_source_chunk_text_trgm
  ON source_chunk USING GIN(chunk_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_memory_canonical_text_trgm
  ON memory_item USING GIN(canonical_text gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_source_document_title_trgm
  ON source_document USING GIN(title gin_trgm_ops);
```

`pg_trgm` is a PostgreSQL contrib module. Current PostgreSQL versions mark it as
a trusted extension, so users with `CREATE` privilege on the database can install
it. PR4 should still fail fast during `npm run db:setup` if the extension cannot
be created, because fuzzy search depends on it.

### 4.4 Migration of Existing `source_chunk.search_vector`

Existing facts:

- `database/02_schema_memory.sql` already defines
  `source_chunk.search_vector` as `to_tsvector('simple', chunk_text)`.
- `database/04_indexes.sql` already defines `idx_source_chunk_fts` on that
  column.
- `backend/app/services/recall_service.py` already uses
  `sc.search_vector @@ websearch_to_tsquery(...)`.

PR4 should choose replacement semantics, not dual columns:

- Add `source_chunk.search_text_zh`.
- Change the existing `source_chunk.search_vector` generated expression to
  `to_tsvector('simple', coalesce(search_text_zh, ''))`.
- Keep the column name `search_vector` and index name `idx_source_chunk_fts`.
- Add the same `search_text_zh` + `search_vector` pair to `memory_item` for
  symmetry.
- Keep recall SQL references to `sc.search_vector`; the SQL path automatically
  points at the upgraded index.
- Replace recall query preprocessing with the shared tokenizer so
  `websearch_to_tsquery` receives spaced tokens such as `校园 食堂`.

For this development-stage project, implementation should update
`database/02_schema_memory.sql` directly and rebuild the demo database with
`npm run db:setup`. The ALTER example above documents the equivalent live
migration shape, not the preferred local implementation path.

For a live migration, the safe sequence is:

1. Add `search_text_zh`.
2. Backfill `search_text_zh`.
3. Drop the generated `search_vector` column; PostgreSQL drops the dependent
   GIN index automatically.
4. Recreate `search_vector` using `search_text_zh`.
5. Recreate the GIN index.

Do not leave both `search_vector` and `search_text_zh_tsv` on `source_chunk`;
that would double storage/index maintenance and make future readers unsure which
column powers recall.

## 5. Indexed Fields and Initial Boosts

| Route | Fields | Indexed as | Initial weight | PR4 in scope |
|---|---|---|---:|---|
| `chunk_fts` | `source_chunk.chunk_text` via `search_text_zh` | `search_vector` | 1.0 | yes |
| `memory_fts` | `memory_item.canonical_text`, `memory_item.summary` via `search_text_zh` | `search_vector` | 1.0 | yes |
| `trigram_fuzzy` | `source_chunk.chunk_text`, `memory_item.canonical_text` | `gin_trgm_ops` on original text | 0.6 | yes |
| `title_boost` | `source_document.title` | `gin_trgm_ops` on original title | 0.5 | yes |
| `source_path_boost` | `source_document.source_path` | trigram only if needed after baseline | 0.4 | optional |
| `entity_boost` | `entity.canonical_name` | optional route | 0.8 | optional |
| `scene_boost` | `memory_scene.title`, `memory_scene.scene_slug`, `memory_scene.summary` | optional route | 0.6 | optional |

The weights are starting points only. PR4 should not become a tuning project.
Metric-driven weight changes belong in a later evaluation-focused PR.

## 6. Access Model

Current `memory_item.access_level` values are:

```text
public, project, team, private
```

Rules for PR4:

- Memory-level results must follow current recall behavior:
  - no `agent_id`: return only `public` and `project` memories;
  - with `agent_id`: filter through `v_agent_visible_memory`.
- `source_document` and `source_chunk` currently have no `access_level` column.
  Chunk/source search is therefore workspace-level, filtered by
  `source_document.workspace_id` and `source_document.status = 'active'`.
- `mb search --scope chunks` may return workspace source text even if some
  private memory later cites that chunk. This is not a new leak created by PR4;
  it follows the current schema where source documents are workspace-visible.
- Fine-grained source/chunk policy is out of PR4 scope. If the project later
  needs private raw sources, add `source_document.access_level` or a source
  policy table before advertising chunk search as private-safe.

## 7. RRF SQL Skeleton

The implementation should prove this query shape during PR4. If this skeleton
does not execute cleanly against the demo database, split implementation into
two PRs: first `jieba` FTS-only search, then multi-route RRF.

```sql
WITH
query_input AS (
  SELECT
    %(workspace_id)s::uuid AS workspace_id,
    %(agent_id)s::uuid AS agent_id,
    %(query_text)s::text AS query_text,
    %(tokenized_query)s::text AS tokenized_query,
    %(websearch_query)s::text AS websearch_query,
    websearch_to_tsquery('simple', %(websearch_query)s) AS token_query
),
chunk_fts AS (
  SELECT
    'chunk'::text AS result_type,
    sc.chunk_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    sc.start_line,
    sc.end_line,
    sc.chunk_text AS body_text,
    'chunk_fts'::text AS strategy,
    ts_rank_cd(sc.search_vector, qi.token_query) AS raw_score,
    1.0::numeric AS route_weight
  FROM query_input qi
  JOIN source_document sd ON sd.workspace_id = qi.workspace_id
  JOIN source_chunk sc ON sc.doc_id = sd.doc_id
  WHERE sd.status = 'active'
    AND sc.search_vector @@ qi.token_query
),
memory_fts_public AS (
  SELECT
    'memory'::text AS result_type,
    mi.memory_id AS result_id,
    mi.created_from_doc_id AS doc_id,
    NULL::text AS source_title,
    NULL::text AS source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    mi.canonical_text AS body_text,
    'memory_fts'::text AS strategy,
    ts_rank_cd(mi.search_vector, qi.token_query) AS raw_score,
    1.0::numeric AS route_weight
  FROM query_input qi
  JOIN memory_item mi ON mi.workspace_id = qi.workspace_id
  WHERE mi.status = 'active'
    AND qi.agent_id IS NULL
    AND mi.access_level IN ('public', 'project')
    AND mi.search_vector @@ qi.token_query
),
memory_fts_agent_visible AS (
  SELECT
    'memory'::text AS result_type,
    mi.memory_id AS result_id,
    mi.created_from_doc_id AS doc_id,
    NULL::text AS source_title,
    NULL::text AS source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    mi.canonical_text AS body_text,
    'memory_fts'::text AS strategy,
    ts_rank_cd(mi.search_vector, qi.token_query) AS raw_score,
    1.0::numeric AS route_weight
  FROM query_input qi
  JOIN memory_item mi ON mi.workspace_id = qi.workspace_id
  WHERE mi.status = 'active'
    AND qi.agent_id IS NOT NULL
    AND mi.search_vector @@ qi.token_query
    AND EXISTS (
      SELECT 1
      FROM v_agent_visible_memory vam
      WHERE vam.agent_id = qi.agent_id
        AND vam.memory_id = mi.memory_id
    )
),
trigram_fuzzy AS (
  SELECT
    'chunk'::text AS result_type,
    sc.chunk_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    sc.start_line,
    sc.end_line,
    sc.chunk_text AS body_text,
    'trigram_fuzzy'::text AS strategy,
    similarity(sc.chunk_text, qi.query_text) AS raw_score,
    0.6::numeric AS route_weight
  FROM query_input qi
  JOIN source_document sd ON sd.workspace_id = qi.workspace_id
  JOIN source_chunk sc ON sc.doc_id = sd.doc_id
  WHERE sd.status = 'active'
    AND sc.chunk_text % qi.query_text
),
title_boost AS (
  SELECT
    'source'::text AS result_type,
    sd.doc_id AS result_id,
    sd.doc_id,
    sd.title AS source_title,
    sd.source_path,
    NULL::int AS start_line,
    NULL::int AS end_line,
    sd.raw_text AS body_text,
    'title_boost'::text AS strategy,
    similarity(sd.title, qi.query_text) AS raw_score,
    0.5::numeric AS route_weight
  FROM query_input qi
  JOIN source_document sd ON sd.workspace_id = qi.workspace_id
  WHERE sd.status = 'active'
    AND sd.title % qi.query_text
),
route_union AS (
  SELECT * FROM chunk_fts
  UNION ALL
  SELECT * FROM memory_fts_public
  UNION ALL
  SELECT * FROM memory_fts_agent_visible
  UNION ALL
  SELECT * FROM trigram_fuzzy
  UNION ALL
  SELECT * FROM title_boost
),
ranked AS (
  SELECT
    *,
    row_number() OVER (
      PARTITION BY strategy
      ORDER BY raw_score DESC, result_id
    ) AS route_rank
  FROM route_union
),
fused AS (
  SELECT
    result_type,
    result_id,
    max(doc_id) AS doc_id,
    max(source_title) AS source_title,
    max(source_path) AS source_path,
    min(start_line) AS start_line,
    max(end_line) AS end_line,
    max(body_text) AS body_text,
    array_agg(strategy ORDER BY strategy) AS strategies,
    sum(route_weight / (60 + route_rank)) AS rrf_score
  FROM ranked
  GROUP BY result_type, result_id
)
SELECT *
FROM fused
ORDER BY rrf_score DESC, result_type, result_id
LIMIT %(limit)s;
```

Implementation notes:

- Keep the first PR route set small enough to validate with `EXPLAIN`.
- Prefer route CTEs that each use one index-friendly predicate.
- If `OR` predicates cause poor plans, split them into separate route CTEs.
- Keep `tokenized_query` as the response/debug shape, but build
  `websearch_query` as an OR expression over tokens, for example
  `校园 OR 食堂 OR cafeteria`. A plain AND tsquery is too strict for bilingual
  expansion because it requires Chinese and English tokens to co-exist in the
  same row.

## 8. CLI Output

Default JSON:

```bash
mb search "为什么放弃校园食堂方向" --workspace cs3321-demo
```

`--show-lines`:

```bash
mb search "决策记录" --workspace cs3321-demo --show-lines
```

stdout:

```text
data/raw_sources/demo_workspace/discussion_01_project_pivot.md:8-12: The cafeteria system was too CRUD-heavy and did not demonstrate enough database features.
data/raw_sources/demo_workspace/discussion_06_demo_plan.md:10-12: The key recall question is "why did we abandon the campus cafeteria system".
```

No-result behavior:

```text
stderr: no results matched query: "..." (scope=chunks, strategies tried: chunk_fts, memory_fts, trigram_fuzzy, title_boost)
exit: 4
stdout: empty
```

## 9. Backfill Script

Add `backend/scripts/backfill_search_terms.py`.

`scripts/db_cli.py seed/reset` should run the full backfill automatically after
`database/07_seed.sql` and before `database/08_demo_queries.sql`, so
`npm run db:setup` leaves lexical search fields ready for both English and
Chinese data.

Modes:

```bash
PYTHONPATH=backend .venv/bin/python backend/scripts/backfill_search_terms.py --full
PYTHONPATH=backend .venv/bin/python backend/scripts/backfill_search_terms.py --missing-only
PYTHONPATH=backend .venv/bin/python backend/scripts/backfill_search_terms.py --workspace-slug cs3321-demo --missing-only
```

Behavior:

- `--full`: recompute all supported rows.
- `--missing-only`: only update rows where `search_text_zh IS NULL`.
- `--workspace-slug`: limit by `workspace.slug`.
- Fail fast if `jieba` is unavailable.
- Print counts by table.
- For `memory_item`, disable user triggers during the derived-field backfill so
  maintenance updates do not create misleading `memory.update` audit entries or
  revisions.

Write paths must use the same tokenizer helper as the backfill script, so import,
inline agent notes, and memory writes all produce consistent `search_text_zh`.

## 10. Adversarial Gold Set

Add a separate PR4 gold file, for example:

```text
data/eval/search_adversarial_gold.json
```

The set should contain 15-20 items. Use existing demo data first. Do not add new
demo source files until the first baseline shows that the current corpus cannot
exercise the intended routes.

Categories:

| Category | Purpose | Count | Pass expectation |
|---|---|---:|---|
| synonym_rewrite | Same meaning, different words | 4-5 | should improve over PR2 keyword expansion |
| missing_keyword | Query is intent, target is conclusion | 4-5 | should hit when lexical overlap exists through evidence/title |
| typo_fuzzy | Misspelling or fuzzy phrase | 4-5 | should hit via `trigram_fuzzy` |
| cross_language | Chinese query for English target, or reverse | 4-5 | not required to pass in PR4 |

Cross-language cases must be honest. With jieba + simple FTS + pg_trgm, Chinese
and English semantic equivalence is mostly unreachable without either a curated
dictionary or embeddings. Mark these rows as:

```json
{
  "expected_strategy": "needs_embedding_or_dict",
  "required_for_pr4_pass": false
}
```

They exist to quantify lexical-first limits and justify a later optional
embedding provider, not to make PR4 fail for a known non-goal.

Example rows:

```json
[
  {
    "category": "typo_fuzzy",
    "query": "为什么放弃校园食堂系通",
    "workspace": "cs3321-demo",
    "expected_result_type": "chunk",
    "expected_text_substrings": ["cafeteria system"],
    "expected_source_titles": ["Discussion 01: Project Pivot"],
    "expected_strategy": "trigram_fuzzy",
    "required_for_pr4_pass": true
  },
  {
    "category": "cross_language",
    "query": "为什么放弃校园食堂方向",
    "workspace": "cs3321-demo",
    "expected_result_type": "chunk",
    "expected_text_substrings": ["cafeteria system"],
    "expected_source_titles": ["Discussion 01: Project Pivot"],
    "expected_strategy": "needs_embedding_or_dict",
    "required_for_pr4_pass": false
  }
]
```

## 11. Demo Data Assessment

The current demo corpus appears sufficient for a first PR4 baseline:

- It includes English source files with Chinese-facing expected questions.
- It includes project pivot, architecture, policy/recall, wiki/timeline, and demo
  planning topics.
- It already exercises typo/fuzzy, title matching, source chunk search, and
  memory recall.

Do not add new demo documents in the first PR4 implementation unless the
adversarial baseline cannot cover at least 12 rows with
`required_for_pr4_pass: true` across all of `synonym_rewrite`,
`missing_keyword`, and `typo_fuzzy`. Cross-language rows marked
`required_for_pr4_pass: false` do not count toward this threshold.
If extra data is needed, add only 3-5 targeted lines or one short source file,
not a broad synthetic corpus.

## 12. Implementation Split Recommendation

PR4 should be implemented in two reviewable PRs.

PR4a is the internal infrastructure upgrade:

1. Add `pg_trgm`, `jieba`, generated columns, indexes, tokenizer helper, and
   backfill script.
2. Populate search fields from source import, inline agent note creation, and
   memory create/update.
3. Update recall query preprocessing so existing `sc.search_vector` SQL receives
   tokenized query text.
4. Verify existing recall baseline and search-field population before any new
   public API is added.

PR4b is the user-facing search feature:

1. Add `POST /api/search` with `chunk_fts` and `memory_fts`.
2. Add `trigram_fuzzy`, `title_boost`, and SQL RRF. These two extra routes are
   PR4 must-do items. `source_path_boost`, `entity_boost`, and `scene_boost`
   are optional expansions and should be added only after explicit review if the
   required baseline cannot diagnose enough results without them.
3. Add `mb search`.
4. Add adversarial eval under the existing eval command surface as
   `mb eval recall --gold search` and `mb eval recall --gold all`. This avoids a
   second eval command family while still letting PR4 run the search-oriented
   adversarial set. A separate `mb eval search` command is not needed unless
   search later diverges into a broader benchmark suite.

If PR4b's RRF step cannot be made explainable and index-friendly, stop at
`chunk_fts` + `memory_fts` and split RRF/trigram into a follow-up PR. Do not
hide this behind Python-side ranking.

## 13. Verification

Required commands:

```bash
npm run db:setup
PYTHONPATH=backend .venv/bin/python backend/scripts/backfill_search_terms.py --missing-only
.venv/bin/python -m pytest backend/tests -q
uv run ruff check backend scripts
.venv/bin/python -m compileall backend scripts
git diff --check
```

Manual smoke:

```bash
mb search "为什么放弃校园食堂方向" --workspace cs3321-demo --show-lines
mb search "校园食堂系通" --workspace cs3321-demo --format json
mb recall "为什么放弃校园食堂方向" --workspace cs3321-demo
mb context "为什么放弃校园食堂方向" --workspace cs3321-demo --max-tokens 2000
```

Acceptance:

- Existing PR2/PR3 CLI flows still work.
- `mb search --show-lines` gives grep-like source lines.
- `POST /api/search` has no presentation-only fields.
- Required adversarial cases pass; cross-language non-required cases are
  reported separately.
- No private memory result appears without an allowed `agent_id`.

## 14. References

- PostgreSQL `pg_trgm`: https://www.postgresql.org/docs/17/pgtrgm.html
- PostgreSQL text search types: https://www.postgresql.org/docs/15/datatype-textsearch.html
- PostgreSQL text search functions: https://www.postgresql.org/docs/current/functions-textsearch.html
- jieba Chinese segmentation: https://github.com/fxsjy/jieba
- Azure AI Search RRF overview: https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking
