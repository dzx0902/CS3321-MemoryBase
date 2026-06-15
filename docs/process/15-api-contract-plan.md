# MemoryBase API Contract Plan

本文档用于 PR #44 合并后的后端交接。`docs/08-api-design.md` 保留课程报告用的 API 摘要，本文件作为 I019-I030 后端实现、前端 mock、集成验收的执行契约。

## 1. Scope

### 1.1 覆盖 issue

| Issue | GitHub | Priority | 目标 |
|---|---:|---|---|
| I019 | #20 | P0 | 后端 health、config、DB 连接基础 |
| I020 | #21 | P0 | Markdown / txt 导入、checksum、chunk 切分 |
| I021 | #22 | P0 | SourceDocument / SourceChunk API |
| I022 | #23 | P0 | MemoryItem CRUD 与 Evidence 绑定 |
| I023 | #24 | P0 | MemoryRevision、AuditLog、软删除闭环 |
| I024 | #25 | P0 | Recall API 与 Context Pack |
| I025 | #26 | P1 | RecallLog、排序、演示问题测试 |
| I026 | #27 | P1 | AccessPolicy API 与 Agent 可见性过滤 |
| I027 | #28 | P1 | AuditLog 查询 API |
| I028 | #29 | P1 | ConflictRecord API |
| I029 | #30 | P0 | Wiki Markdown 导出 API |
| I030 | #31 | P1 | TimelineEntry API |

### 1.2 P0 后端闭环

```text
POST /api/sources
  -> source_document + source_chunk
POST /api/memories
  -> memory_item + memory_evidence
PATCH /api/memories/{memory_id}
  -> memory_revision + audit_log by trigger
POST /api/recall
  -> memory + evidence + source chunk + recall_log
POST /api/wiki/export
  -> wiki_page + wiki_page_revision + Markdown file
```

P0 不依赖 LLM、pgvector 或中文分词扩展。Recall 必须用确定性 SQL、关键词和 PostgreSQL FTS 跑通 demo。

## 2. Global Contract

### 2.1 Base path

所有后端 API 使用 `/api` 前缀。当前已有 `GET /api/health`。

### 2.2 JSON conventions

- UUID 使用字符串。
- 时间戳使用 ISO 8601 字符串，后端以 PostgreSQL `TIMESTAMPTZ` 为准。
- 请求和响应字段使用 `snake_case`，与数据库字段保持一致。
- P0 不增加全局 `data` envelope，直接返回资源形状 JSON。
- list API 统一返回：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### 2.3 Pagination and filtering

- `page`: 默认 `1`，最小 `1`。
- `page_size`: 默认 `20`，最大 `100`。
- `workspace_id` 是所有业务查询和写入的必传参数。
- 列表 API 的 `workspace_id` 放 query string。
- 创建 API 的 `workspace_id` 放 request body。
- 详情 API 使用 `/{id}` 加 `workspace_id` query，避免跨 workspace 泄露。

### 2.4 Error response

业务错误使用 FastAPI `HTTPException`，`detail` 统一为对象：

```json
{
  "code": "duplicate_source",
  "message": "Source document with the same checksum already exists in this workspace.",
  "fields": {
    "checksum": "..."
  }
}
```

推荐状态码：

| Status | 用途 |
|---:|---|
| 400 | 业务参数非法，如 evidence chunk 不属于同一 workspace |
| 404 | 资源不存在，或资源不属于指定 workspace |
| 409 | checksum、policy、conflict 等唯一约束冲突 |
| 422 | Pydantic 请求体验证失败 |
| 500 | 未预期服务端错误 |

### 2.5 Actor and trigger session variables

Memory / Wiki 相关写操作需要让数据库 trigger 能记录 actor 和 revision reason。后端统一支持这些可选 header：

| Header | Values | 用途 |
|---|---|---|
| `X-Actor-Type` | `user` / `agent` / `system` | 写入 `memory_revision.editor_type` 和 `audit_log.actor_type` |
| `X-Actor-Id` | UUID | 写入 `editor_id` / `actor_id` |
| `X-Revision-Reason` | text | 写入 `memory_revision.revision_reason` |

后端在同一个 DB transaction 内设置：

```sql
SELECT set_config('app.actor_type', $1, true);
SELECT set_config('app.actor_id', $2, true);
SELECT set_config('app.revision_reason', $3, true);
```

注意：`true` 只能在同一 transaction 内生效。不要在 autocommit 跨语句场景依赖它。

Recall / visibility 查询需要设置：

```sql
SELECT set_config('app.agent_id', $1, true);
```

然后在同一 transaction / connection 中查询 `v_agent_visible_memory`。

### 2.6 Database access rules

- 使用 parameterized SQL，不拼接用户输入。
- 每个写 API 使用 transaction。
- 创建 memory 和 evidence 必须同事务提交。
- 更新 memory 不手写 `memory_revision`；由 trigger 生成。
- 删除 memory 的 API 层使用 `UPDATE memory_item SET status = 'archived', valid_to = coalesce(valid_to, now())`。数据库的 `BEFORE DELETE` soft-delete trigger 是安全网，不作为 API 主路径。
- Schema 变更必须先和项目 owner 确认，不在后端 issue 中顺手改表。

## 3. Backend File Plan

建议文件结构：

```text
backend/app/
  main.py
  api/
    health.py
    sources.py
    memories.py
    recall.py
    wiki.py
    audit.py
    policies.py
    conflicts.py
    timeline.py
  core/
    config.py
    db.py
    errors.py
  services/
    ingest_service.py
    memory_service.py
    recall_service.py
    wiki_export_service.py
  models/
    schemas.py
```

可按 issue 分批创建。不要一次性实现所有 router；先完成 #20 的 DB 基础，再逐个接入。

## 4. Health and DB Foundation

### GET /api/health

Purpose: 校验 FastAPI 和数据库连接。

Response:

```json
{
  "status": "ok",
  "service": "memorybase",
  "database": {
    "status": "ok"
  }
}
```

Acceptance:

```sql
SELECT 1;
```

## 5. Source API

### POST /api/sources

导入 Markdown / txt / meeting / chat / note / report 文档。

Request:

```json
{
  "workspace_id": "00000000-0000-0000-0000-000000000201",
  "title": "Discussion 01: Project Pivot",
  "doc_type": "markdown",
  "raw_text": "# Discussion 01\n\n...",
  "source_path": "data/raw_sources/demo_workspace/discussion_01_project_pivot.md",
  "session_id": null,
  "imported_by_user_id": "00000000-0000-0000-0000-000000000101"
}
```

Rules:

- `doc_type` 必须属于 `markdown`, `txt`, `meeting`, `chat`, `note`, `report`。
  `inline_agent_note` 只由 Agent Runtime 写回路径自动创建，不作为普通导入入口。
- `checksum` 使用 raw_text 的 SHA-256 hex。
- 同一 workspace 内重复 checksum 返回 `409 duplicate_source`，不要重复写 source/chunk。
- 跨 workspace 相同 checksum 允许。
- P0 chunk 算法必须确定性：规范化 CRLF 为 LF，按空行分隔非空文本块，`chunk_no` 从 1 开始，记录 `start_line` / `end_line`，`token_count` 使用空白分词计数。

Response:

```json
{
  "doc_id": "uuid",
  "workspace_id": "uuid",
  "title": "Discussion 01: Project Pivot",
  "doc_type": "markdown",
  "checksum": "sha256-hex",
  "chunk_count": 8,
  "imported_at": "2026-05-16T00:00:00Z"
}
```

Tables:

- `source_document`
- `source_chunk`

Acceptance SQL:

```sql
SELECT count(*) FROM source_document WHERE workspace_id = :workspace_id;
SELECT count(*) FROM source_chunk WHERE doc_id = :doc_id;
```

### GET /api/sources

Query:

```text
workspace_id=uuid
keyword=optional text
status=active|forgotten|all
page=1
page_size=20
```

Rules:

- If `status` is omitted, return only `active` source documents.
- `status=all` is an explicit governance/admin view and disables source status filtering.

Response item:

```json
{
  "doc_id": "uuid",
  "workspace_id": "uuid",
  "title": "Discussion 01: Project Pivot",
  "doc_type": "meeting",
  "source_path": "data/raw_sources/demo_workspace/discussion_01_project_pivot.md",
  "status": "active",
  "checksum": "demo-discussion-01",
  "imported_at": "2026-03-02T10:00:00Z",
  "chunk_count": 4
}
```

### GET /api/sources/{doc_id}

Query:

```text
workspace_id=uuid
include_forgotten=false
```

Rules:

- Default behavior hides forgotten sources.
- `include_forgotten=true` is a governance/admin read path for an already-known `doc_id`.

Response:

```json
{
  "doc_id": "uuid",
  "workspace_id": "uuid",
  "title": "Discussion 01: Project Pivot",
  "doc_type": "meeting",
  "source_path": "...",
  "raw_text": "...",
  "checksum": "demo-discussion-01",
  "imported_at": "2026-03-02T10:00:00Z",
  "chunks": [
    {
      "chunk_id": "uuid",
      "chunk_no": 1,
      "chunk_text": "...",
      "start_line": 6,
      "end_line": 8,
      "token_count": 24
    }
  ]
}
```

## 6. Memory and Evidence API

### POST /api/memories

Request:

```json
{
  "workspace_id": "uuid",
  "created_from_doc_id": "uuid",
  "memory_type": "decision",
  "canonical_text": "The team abandoned the campus cafeteria system because it was too CRUD-heavy.",
  "summary": "Reason cafeteria topic was rejected.",
  "confidence": 0.95,
  "importance": 5,
  "access_level": "project",
  "owner_user_id": "uuid",
  "owner_agent_id": null,
  "evidence": [
    {
      "chunk_id": "uuid",
      "evidence_role": "supports",
      "weight": 1.0,
      "note": "Direct reason."
    }
  ]
}
```

Rules:

- `memory_type`: `episodic`, `semantic`, `fact`, `profile`, `procedural`, `decision`, `preference`, `task`, `risk`, `constraint`, `policy`, `summary`。
- `status`: new records may start as `active` or `candidate`. Later changes must follow the lifecycle transitions documented in `docs/22-backend-memory-roadmap.md`.
- `access_level`: `public`, `project`, `team`, `private`。
- `confidence` between 0 and 1.
- `importance` between 1 and 5.
- Every evidence chunk must exist and belong to the same workspace.
- P0 backend implements only the `evidence` object-array form. Do not implement `evidence_chunk_ids` shorthand unless a later issue explicitly adds backward compatibility.
- Agent/CLI write-back may submit `evidence: []`; with `X-Actor-Type: agent`,
  the backend creates an `inline_agent_note` source document and chunk before binding
  a `source` evidence row.
- Insert `memory_item`; trigger creates revision 1 and audit log.

Response:

```json
{
  "memory_id": "uuid",
  "workspace_id": "uuid",
  "current_revision_no": 1,
  "status": "active",
  "evidence_count": 1
}
```

### GET /api/memories

Query:

```text
workspace_id=uuid
memory_type=optional
status=active
access_level=optional
keyword=optional
page=1
page_size=20
```

Rules:

- If `status` is omitted, return only `active` memory.
- `status=all` is an explicit governance/admin view and disables memory status filtering.
- Archived, forgotten, superseded, and conflicted records must not leak into the default list response.

Response item:

```json
{
  "memory_id": "uuid",
  "workspace_id": "uuid",
  "memory_type": "decision",
  "canonical_text": "...",
  "summary": "...",
  "confidence": 0.95,
  "importance": 5,
  "status": "active",
  "access_level": "project",
  "current_revision_no": 2,
  "evidence_count": 1,
  "updated_at": "2026-03-25T00:00:00Z"
}
```

### GET /api/memories/{memory_id}

Query:

```text
workspace_id=uuid
```

Response:

```json
{
  "memory_id": "uuid",
  "workspace_id": "uuid",
  "created_from_doc_id": "uuid",
  "memory_type": "decision",
  "canonical_text": "...",
  "summary": "...",
  "confidence": 0.95,
  "importance": 5,
  "status": "active",
  "access_level": "project",
  "owner_user_id": "uuid",
  "owner_agent_id": null,
  "valid_from": "...",
  "valid_to": null,
  "superseded_by_memory_id": null,
  "current_revision_no": 2,
  "created_at": "...",
  "updated_at": "...",
  "evidence_count": 1,
  "evidence": [
    {
      "evidence_id": "uuid",
      "chunk_id": "uuid",
      "evidence_role": "supports",
      "weight": 1.0,
      "note": "...",
      "doc_id": "uuid",
      "source_title": "Discussion 01: Project Pivot",
      "chunk_no": 2,
      "chunk_text": "...",
      "start_line": 10,
      "end_line": 10
    }
  ],
  "revisions": [
    {
      "revision_no": 1,
      "revision_text": "...",
      "revision_summary": "...",
      "revision_reason": "seed import",
      "editor_type": "system",
      "editor_id": null,
      "created_at": "..."
    }
  ],
  "entities": [
    {
      "entity_id": "uuid",
      "canonical_name": "MemoryBase Project",
      "entity_type": "project",
      "relation_role": "about"
    }
  ],
  "scenes": [
    {
      "scene_id": "uuid",
      "scene_slug": "topic-decision",
      "title": "Topic Decision",
      "cell_role": "decision",
      "sort_order": 20
    }
  ]
}
```

### PATCH /api/memories/{memory_id}

Query:

```text
workspace_id=uuid
```

Request fields are partial:

```json
{
  "canonical_text": "Updated canonical memory text.",
  "summary": "Updated summary.",
  "confidence": 0.98,
  "importance": 5,
  "access_level": "project",
  "status": "active",
  "valid_to": null,
  "superseded_by_memory_id": null
}
```

Rules:

- Set actor session variables before update.
- Do not manually insert `memory_revision`.
- Response must show the new `current_revision_no`.

### DELETE /api/memories/{memory_id}

Query:

```text
workspace_id=uuid
```

Rules:

- Use API-level soft delete:

```sql
UPDATE memory_item
SET status = 'archived',
    valid_to = coalesce(valid_to, now())
WHERE memory_id = :memory_id
  AND workspace_id = :workspace_id
  AND status <> 'archived';
```

- Trigger creates revision/audit for the status change.

Response:

```json
{
  "memory_id": "uuid",
  "status": "archived"
}
```

## 7. Recall API

### POST /api/recall

Request:

```json
{
  "workspace_id": "uuid",
  "agent_id": "uuid",
  "query_text": "为什么放弃校园食堂系统？",
  "memory_type": "decision",
  "access_level": "project",
  "status": "active",
  "as_of": "2026-05-16T12:00:00Z",
  "limit": 5
}
```

Rules:

- If `agent_id` is present, apply `v_agent_visible_memory` in the same DB transaction after setting `app.agent_id`.
- If `agent_id` is absent, search only active memory with `access_level IN ('public', 'project')`; private/team memory must not be returned without an agent identity.
- If `as_of` is present, filter by `valid_from <= as_of` and `(valid_to IS NULL OR valid_to > as_of)`.
- Search joins `memory_item`, `memory_evidence`, `source_chunk`, and active `source_document`.
- Use PostgreSQL FTS on `source_chunk.search_vector`.
- Also use deterministic fallback keyword matching on `memory_item.canonical_text`, `memory_item.summary`, and `source_chunk.chunk_text`.
- For the required demo question, support deterministic bilingual keyword expansion without LLM:
  - `食堂` -> `cafeteria`
  - `校园` -> `campus`
  - `放弃` -> `abandon`, `abandoned`
  - `系统` -> `system`
  - `数据库` -> `database`
- Ranking baseline: FTS rank first, then evidence weight, memory importance, and memory updated_at.
- Insert one `recall_log` row per request with `result_count`, `top_memory_ids_json`, and `context_pack_json`.

Response:

```json
{
  "recall_id": "uuid",
  "query_text": "为什么放弃校园食堂系统？",
  "result_count": 3,
  "memories": [
    {
      "memory_id": "uuid",
      "memory_type": "decision",
      "canonical_text": "...",
      "summary": "...",
      "confidence": 0.95,
      "importance": 5,
      "access_level": "project",
      "score": 0.91,
      "evidence": [
        {
          "evidence_id": "uuid",
          "evidence_role": "supports",
          "weight": 1.0,
          "source_title": "Discussion 01: Project Pivot",
          "chunk_id": "uuid",
          "chunk_no": 2,
          "chunk_text": "...",
          "start_line": 10,
          "end_line": 10
        }
      ]
    }
  ],
  "context_pack": {
    "memory_ids": ["uuid"],
    "source_doc_ids": ["uuid"],
    "chunks": []
  }
}
```

Acceptance SQL:

```sql
SELECT result_count, top_memory_ids_json
FROM recall_log
WHERE recall_id = :recall_id;
```

## 8. Lexical Search API

### POST /api/search

Purpose: expose zero-config lexical search for agent source/evidence discovery.
This is additive to recall: search is chunk/source-oriented, while recall is
memory-oriented and writes `recall_log`.

Request:

```json
{
  "workspace_id": "uuid",
  "agent_id": "uuid",
  "query_text": "为什么放弃校园食堂方向",
  "scope": "all",
  "limit": 10
}
```

Rules:

- `scope` must be one of `all`, `chunks`, `memories`, `sources`.
- Do not accept presentation-only fields such as `show_lines`; CLI renders
  grep-like rows from structured API results.
- Return `tokenized_query` for debugging and eval reproducibility.
- Use SQL-side RRF over `chunk_fts`, `memory_fts`, `trigram_fuzzy`, and
  `title_boost`.
- Memory results must use the same permission behavior as recall:
  - no `agent_id`: active `public/project` only;
  - with `agent_id`: `v_agent_visible_memory`.
- Chunk/source results are workspace-level and require active source documents.

Response:

```json
{
  "workspace_id": "uuid",
  "query_text": "为什么放弃校园食堂方向",
  "tokenized_query": "为什么 放弃 校园 食堂 方向 cafeteria campus",
  "result_count": 1,
  "items": [
    {
      "result_type": "chunk",
      "result_id": "uuid",
      "doc_id": "uuid",
      "source_path": "data/raw_sources/demo_workspace/discussion_01_project_pivot.md",
      "source_title": "Discussion 01: Project Pivot",
      "start_line": 8,
      "end_line": 12,
      "snippet": "The cafeteria system was too CRUD-heavy...",
      "score": 0.031,
      "strategies": ["chunk_fts", "trigram_fuzzy"]
    }
  ]
}
```

## 9. Wiki Export API

### POST /api/wiki/export

Request:

```json
{
  "workspace_id": "uuid",
  "pages": [
    {
      "page_slug": "why-memorybase",
      "page_type": "synthesis",
      "title": "Why MemoryBase",
      "memory_ids": ["uuid"]
    }
  ],
  "write_files": true
}
```

Rules:

- If `pages` is omitted, export existing `wiki_page` rows for the workspace.
- Create or reuse `wiki_page` by `(workspace_id, page_slug)`.
- Insert a new `wiki_page_revision` every export.
- Trigger updates `wiki_page.current_revision_no` and clears `needs_rebuild`.
- Write Markdown to `data/markdown_wiki/{workspace_id}/{page_slug}.md` when `write_files = true`.
- Markdown must include frontmatter with `workspace_id`, `page_slug`, `page_type`, `title`, `generated_at`, `memory_ids`, and `source_doc_ids`.
- Body must include memory text and source provenance.

Response:

```json
{
  "workspace_id": "uuid",
  "pages": [
    {
      "page_id": "uuid",
      "page_slug": "why-memorybase",
      "revision_no": 2,
      "file_path": "data/markdown_wiki/.../why-memorybase.md",
      "memory_count": 3,
      "source_count": 2
    }
  ]
}
```

## 9. Governance APIs

### GET /api/audit

Query:

```text
workspace_id=uuid
actor_type=optional
actor_id=optional
action_type=optional
target_type=optional
target_id=optional
start_time=optional ISO timestamp
end_time=optional ISO timestamp
sort=desc|asc
include_diff=false
page=1
page_size=20
```

Response item:

```json
{
  "audit_id": "uuid",
  "workspace_id": "uuid",
  "actor_type": "system",
  "actor_id": null,
  "action_type": "memory.update",
  "target_type": "memory_item",
  "target_id": "uuid",
  "before_json": {},
  "after_json": {},
  "diff_json": {
    "summary": {
      "before": "old",
      "after": "new"
    }
  },
  "created_at": "..."
}
```

Rules:

- `include_diff=true` returns a shallow top-level JSON diff between `before_json` and `after_json`.
- `sort` controls event order by `created_at`.

### GET /api/audit/lifecycle

Query:

```text
workspace_id=uuid
target_type=memory_item
target_id=uuid
```

Rules:

- Return a chronological lifecycle view by UNION-ing `audit_log`, `memory_revision`, related `conflict_record`, and related `forget_request`.
- Each item contains `ts`, `kind`, and `payload`; `kind` distinguishes `audit`, `revision`, `conflict`, and `forget_request`.

### GET /api/audit/actors/{actor_type}/{actor_id}/timeline

Query:

```text
workspace_id=optional uuid
page=1
page_size=20
```

Rules:

- Return the actor's audit timeline using the same response envelope as `GET /api/audit`.

### GET /api/audit/statistics

Query:

```text
workspace_id=optional uuid
group_by=action_type|actor_type|target_type
```

Rules:

- Return `group_key`, `event_count`, and `last_event_at` for each group.

### POST /api/policies

Request:

```json
{
  "workspace_id": "uuid",
  "principal_type": "agent",
  "principal_id": "uuid",
  "resource_type": "memory_item",
  "resource_scope": "project",
  "effect": "allow",
  "predicate_json": {}
}
```

Rules:

- Duplicate policy returns `409 duplicate_policy`.
- `principal_id = null` is allowed for role/global policies.
- P1 follow-up: add `DELETE /api/policies/{policy_id}` when the UI needs policy removal. It is not required for the P0 recall demo.

### GET /api/policies

Query:

```text
workspace_id=uuid
principal_type=optional
principal_id=optional
resource_type=optional
effect=optional
page=1
page_size=20
```

### GET /api/agents/{agent_id}/visible-memories

Query:

```text
workspace_id=uuid
page=1
page_size=20
```

Rules:

- Query `v_agent_visible_memory` after setting `app.agent_id`.
- Unknown agent UUIDs are allowed and return an empty page.
- Deny policies override allow policies; project-only agents must not see private memory.

### DELETE /api/policies/{policy_id}

P1 deferred endpoint. Not required for the P0 backend handoff, but keep this contract so policy removal is not forgotten.

Query:

```text
workspace_id=uuid
```

Response:

```json
{
  "policy_id": "uuid",
  "deleted": true
}
```

Rules:

- Delete only the matching policy in the given workspace.
- Return 404 if the policy does not exist or does not belong to the workspace.
- If later audit coverage is required, write `audit_log` from the API layer because no policy trigger exists.

### POST /api/conflicts

Manual conflict creation endpoint.

Request:

```json
{
  "workspace_id": "uuid",
  "left_memory_id": "uuid",
  "right_memory_id": "uuid",
  "conflict_type": "uncertain",
  "resolution_note": "Clarify whether LLM extraction belongs to MVP.",
  "actor_type": "user",
  "actor_id": "uuid"
}
```

Rules:

- Validate both memories exist in the same workspace.
- Normalize the pair before insert so `left_memory_id < right_memory_id`; callers should not need to know UUID ordering.
- Duplicate conflict returns `409 duplicate_conflict`.
- `conflict_type`: `semantic`, `temporal`, `policy`, `duplicate`, `contradiction`, `supersession`, `uncertain`.
- Initial status is `open`.
- The service sets actor session variables before insert.
- Database triggers mark related active memories as `conflicted`; the existing memory update trigger then writes revision/audit rows.

Response:

```json
{
  "conflict_id": "uuid",
  "workspace_id": "uuid",
  "left_memory_id": "uuid",
  "right_memory_id": "uuid",
  "conflict_type": "uncertain",
  "status": "open"
}
```

### GET /api/conflicts

Query:

```text
workspace_id=uuid
status=open
page=1
page_size=20
```

Use `v_conflict_memory` or equivalent join.

### PATCH /api/conflicts/{conflict_id}

Query:

```text
workspace_id=uuid
```

Request:

```json
{
  "status": "resolved",
  "resolution_note": "MVP does not require LLM automatic extraction."
}
```

Rules:

- `status`: `open`, `resolved`, `ignored`.
- If status becomes `resolved` or `ignored`, set `resolved_at = now()`.
- The service writes `conflict.update` audit and sets actor session variables.
- Database triggers restore related memories to `active` when no other open conflict remains.

### POST /api/forget-requests

P1 governance endpoint. The schema exists in the database foundation, and the backend implements
the lightweight memory forgetting workflow.

Request:

```json
{
  "workspace_id": "uuid",
  "target_type": "memory_item",
  "target_id": "uuid",
  "requester_user_id": "uuid",
  "reason": "Private memory should be archived for the demo."
}
```

Rules:

- `target_type`: `memory_item`, `source_document`, `wiki_page`, `entity`.
- Initial status is `pending`.
- Validate the requester exists when provided.
- Validate target existence for all supported target tables.

### GET /api/forget-requests

P1 governance endpoint.

Query:

```text
workspace_id=uuid
status=optional
target_type=optional
page=1
page_size=20
```

### PATCH /api/forget-requests/{request_id}

P1 governance endpoint for approval / rejection / completion.

Query:

```text
workspace_id=uuid
```

Request:

```json
{
  "status": "approved",
  "reviewed_by_user_id": "uuid"
}
```

Rules:

- `status`: `pending`, `approved`, `rejected`, `done`.
- `reviewed_by_user_id` is ignored and stored as `null` while status remains `pending`; terminal statuses require a reviewer.
- When status becomes `approved`, `rejected`, or `done`, set `resolved_at = now()` and store `reviewed_by_user_id`.
- When a `memory_item` request is approved or marked done, set the target memory to `forgotten`
  with `valid_to = now()` in the same transaction.
- When a `source_document`, `wiki_page`, or `entity` request is approved or marked done, set the target row to `status = 'forgotten'` with `forgotten_at = now()`.
- Write `forget_request.create` / `forget_request.update` audit entries from the API layer.
- The memory status change also writes the normal `memory.forget` audit entry through the
  existing memory trigger.

### GET /api/timeline

Query:

```text
workspace_id=uuid
order=asc|desc
page=1
page_size=20
```

Use `v_project_timeline`.

### POST /api/timeline

Request:

```json
{
  "workspace_id": "uuid",
  "memory_id": "uuid",
  "doc_id": "uuid",
  "event_type": "decision",
  "title": "Selected MemoryBase",
  "description": "The team selected MemoryBase for richer database requirements.",
  "event_time": "2026-03-02T10:40:00Z",
  "importance": 5
}
```

## 10. P0 Integration Tests

后端同学每完成一个 issue，应至少跑对应 smoke tests。最终 P0 后端合并前必须覆盖：

1. `GET /api/health` returns DB ok.
2. `POST /api/sources` imports one source and creates chunks with line ranges.
3. Duplicate source checksum in same workspace returns 409.
4. `GET /api/sources/{doc_id}` returns chunks.
5. `POST /api/memories` creates memory and evidence in one transaction.
6. Agent/CLI memory write-back creates inline source/evidence when no evidence is supplied.
6. `GET /api/memories/{memory_id}` returns evidence and revisions.
7. `PATCH /api/memories/{memory_id}` increments revision and writes audit.
8. `DELETE /api/memories/{memory_id}` archives memory and writes audit.
9. `POST /api/recall` for `为什么放弃校园食堂系统？` returns cafeteria decision memory and source chunk.
10. Recall writes `recall_log`.
11. Project-only retriever does not see private memory.
12. `POST /api/wiki/export` writes at least three Markdown pages and inserts wiki revisions.

## 11. Handoff Order

Recommended order for the backend owner:

1. I019 (#20): DB connection, config, error helpers, router structure.
2. I020 (#21) + I021 (#22): ingest service and Source API.
3. I022 (#23): Memory CRUD and Evidence binding.
4. I023 (#24): revision/audit/soft delete integration.
5. I024 (#25): Recall API.
6. I029 (#30): Wiki export API.
7. I026-I028 and I030: policy, audit, conflict, timeline P1 APIs.

## 12. Agent Runtime API Addendum

### POST /api/sessions

Create an agent session. `channel` supports `meeting`, `chat`, `import`, `manual`, and
`cli`.

Required body fields: `workspace_id`, `title`. Optional fields: `agent_id`,
`started_by_user_id`, `channel`.

### GET /api/sessions

List sessions by `workspace_id`, with optional `agent_id`, `page`, and `page_size`.

### GET /api/sessions/{session_id}

Read a single session, with optional `workspace_id` query filtering.

### POST /api/observe

Create one message in an existing session.

Required body fields: `session_id`, `role`, `content`. Optional fields:
`sender_type`, `sender_id`, `reply_to_message_id`.

### POST /api/observe/batch

Create up to 100 messages in one transaction. If any message is invalid or references
a missing session, the whole batch rolls back.

The project owner should review each PR against this document, `database/*.sql`, and the relevant issue acceptance criteria. If this document conflicts with SQL or issue body, stop and ask before implementing.
