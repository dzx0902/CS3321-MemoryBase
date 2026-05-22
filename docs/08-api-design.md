# API 设计文档

本文档是课程报告用的 API 摘要。后端实现、前端 mock 与集成验收以 `docs/15-api-contract-plan.md` 的执行契约为准。

## 1. Health

### GET /api/health

返回后端状态。

## 2. Source API

### POST /api/sources

导入 Markdown / txt 文档。`inline_agent_note` 是 Agent Runtime 写回时由后端自动创建的虚拟 source 类型，不作为普通人工导入入口。

请求：

```json
{
  "workspace_id": "uuid",
  "title": "discussion_01",
  "doc_type": "markdown",
  "raw_text": "..."
}
```

返回：

```json
{
  "doc_id": "uuid",
  "chunk_count": 8
}
```

### GET /api/sources

查询 source 列表。默认只返回 `active` source；治理/管理视角可传 `status=all` 查看 forgotten source。

### GET /api/sources/{id}

查询 source 详情和 chunks。默认隐藏 forgotten source；治理/管理视角可传 `include_forgotten=true` 按 `doc_id` 读取已遗忘 source 的详情。

## 3. Memory API

### POST /api/memories

创建 memory，并绑定 evidence。

```json
{
  "workspace_id": "uuid",
  "memory_type": "decision",
  "canonical_text": "最终选择 MemoryBase 作为数据库课程项目。",
  "summary": "项目选题决策",
  "confidence": 0.9,
  "importance": 5,
  "access_level": "project",
  "evidence": [
    {
      "chunk_id": "uuid",
      "evidence_role": "supports",
      "weight": 1.0,
      "note": "Meeting decision source."
    }
  ]
}
```

Agent/CLI 写回可以提交空 `evidence`。当请求头 `X-Actor-Type: agent` 且没有提供 evidence 时，后端会自动创建一个 `inline_agent_note` source document 和 source chunk，再把该 chunk 作为 `source` evidence 绑定到新 memory，保证证据链不断裂。

### GET /api/memories

查询 memory 列表。默认只返回 `status = active` 的 memory；如需审计或管理视角读取归档/遗忘记录，需要显式传入 `status`，其中 `status=all` 表示不做状态过滤。

支持参数：

```text
workspace_id
memory_type
status
access_level
keyword
page
page_size
```

### GET /api/memories/{id}

查询 memory 详情、evidence、revision，以及可选的 entity / scene 关联。

### PATCH /api/memories/{id}

修改 memory，自动生成 revision 和 audit。

### DELETE /api/memories/{id}

软删除 memory。

## 4. Recall API

### POST /api/recall

执行关键词 / 全文检索。`agent_id` 可选；如果传入，则使用 `v_agent_visible_memory` 做 Agent 权限过滤；如果不传，则只允许召回 `public` 和 `project` 范围的 active memory，避免绕过 private/team 权限。`as_of` 可选，用于基于 `valid_from / valid_to` 的时态召回。

```json
{
  "workspace_id": "uuid",
  "agent_id": "uuid",
  "query_text": "为什么放弃校园食堂系统？",
  "memory_type": "decision",
  "access_level": "project",
  "status": "active",
  "as_of": "2026-05-16T12:00:00Z",
  "limit": 10
}
```

返回 memory + evidence + source chunk，并写入 `recall_log`。

## 5. Search API

### POST /api/search

执行 zero-config lexical search。该接口面向 Agent/CLI 的证据发现，返回
chunk / memory / source 级结构化结果；`--show-lines` 这类展示选项只属于 CLI，
不进入 API request。

```json
{
  "workspace_id": "uuid",
  "agent_id": "uuid",
  "query_text": "为什么放弃校园食堂方向",
  "scope": "all",
  "limit": 10
}
```

规则：

- `scope` 支持 `all`、`chunks`、`memories`、`sources`。
- query 先经过 jieba + demo expansion 生成 `tokenized_query`。
- SQL 内部使用 `chunk_fts`、`memory_fts`、`trigram_fuzzy`、`title_boost` 多路召回，并用 RRF 融合排序。
- memory 级结果沿用 recall 权限：无 `agent_id` 时只返回 `public/project` active memory；有 `agent_id` 时使用 `v_agent_visible_memory`。
- chunk/source 级结果按 workspace 和 active source 过滤。

## 6. Wiki API

### POST /api/wiki/export

导出 Markdown Wiki。

返回：

```json
{
  "page_id": "uuid",
  "workspace_id": "uuid",
  "page_slug": "demo-report",
  "title": "Demo Report",
  "page_type": "report",
  "revision_no": 2,
  "body_markdown": "# Demo Report\n...",
  "needs_rebuild": false,
  "output_path": "data/markdown_wiki/demo-report.md",
  "frontmatter_json": {
    "workspace_id": "uuid",
    "page_slug": "demo-report",
    "generated_at": "2026-05-16T12:00:00Z",
    "source_ids": ["uuid"]
  },
  "source_doc_ids": ["uuid"]
}
```

## 6. Audit API

### GET /api/audit

查询审计日志。

支持参数：

```text
workspace_id
actor_type
actor_id
action_type
target_type
target_id
start_time
end_time
sort
include_diff
page
page_size
```

返回：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### GET /api/audit/lifecycle

查询某个目标对象的全生命周期事件，聚合 `audit_log`、`memory_revision`、`conflict_record` 和 `forget_request`。

支持参数：`workspace_id`、`target_type`、`target_id`。

### GET /api/audit/actors/{actor_type}/{actor_id}/timeline

按 actor 查询操作时间线，支持 `workspace_id`、`page`、`page_size`。

### GET /api/audit/statistics

按 `action_type`、`actor_type` 或 `target_type` 聚合审计事件。

## 7. Policy API

### POST /api/policies

创建权限策略。

### GET /api/policies

查询权限策略，支持 `workspace_id`、`principal_type`、`principal_id`、`resource_type`、`effect`、`page`、`page_size`。

### GET /api/agents/{agent_id}/visible-memories

基于 `v_agent_visible_memory` 查询指定 Agent 在工作区中可见的 memory，支持 `workspace_id`、`page`、`page_size`。未知 Agent UUID 返回空列表。

## 8. Conflict API

### POST /api/conflicts

手动创建冲突记录。后端会规范化 memory 左右顺序，避免反向重复；数据库触发器会把 open conflict 两端的 active memory 自动标记为 `conflicted`。

```json
{
  "workspace_id": "uuid",
  "left_memory_id": "uuid",
  "right_memory_id": "uuid",
  "conflict_type": "contradiction",
  "resolution_note": "Two decisions conflict.",
  "actor_type": "user",
  "actor_id": "uuid"
}
```

### GET /api/conflicts

查询冲突记录及左右两侧 memory，支持 `workspace_id`、`status`、`page`、`page_size`。

### PATCH /api/conflicts/{id}

更新 conflict 状态。状态变为 `resolved` 或 `ignored` 后，数据库触发器会在两端 memory 没有其他 open conflict 时自动恢复为 `active`。

```json
{
  "status": "resolved",
  "resolution_note": "accepted MemoryBase direction",
  "actor_type": "user",
  "actor_id": "uuid"
}
```

## 9. ForgetRequest API

### POST /api/forget-requests

提交遗忘请求，不物理删除数据。

```json
{
  "workspace_id": "uuid",
  "target_type": "memory_item",
  "target_id": "uuid",
  "requester_user_id": "uuid",
  "reason": "Private memory should be forgotten for the demo."
}
```

### GET /api/forget-requests

查询遗忘请求，支持 `workspace_id`、`status`、`target_type`、`page`、`page_size`。

### PATCH /api/forget-requests/{id}

审批遗忘请求。`approved` 或 `done` 会对支持的目标执行软治理：`memory_item` 标记为 `forgotten` 并设置 `valid_to`；`source_document`、`wiki_page`、`entity` 标记为 `forgotten` 并设置 `forgotten_at`。所有路径都保留原始记录并写入审计日志。
`pending` 状态下传入的 `reviewed_by_user_id` 会被忽略并保持为空；终态审批需要 reviewer。

```json
{
  "status": "approved",
  "reviewed_by_user_id": "uuid"
}
```

## 10. Timeline API

### GET /api/timeline

查询时间线，支持 `workspace_id` 参数。

### POST /api/timeline

新增时间线事件。

```json
{
  "workspace_id": "uuid",
  "title": "补齐 P0/P1 后端闭环",
  "event_type": "revision",
  "event_time": "2026-05-16T12:00:00Z",
  "description": "完成 recall、policy、conflict 和 wiki export 的后端收口。",
  "importance": 5,
  "memory_id": "uuid",
  "doc_id": "uuid"
}
```

## 11. Agent Runtime API

### POST /api/sessions

创建 Agent 会话。`channel` 支持 `meeting`、`chat`、`import`、`manual`、`cli`。

```json
{
  "workspace_id": "uuid",
  "agent_id": "uuid",
  "title": "feature work",
  "channel": "cli"
}
```

### GET /api/sessions

按 `workspace_id` 和可选 `agent_id` 查询会话列表。

### GET /api/sessions/{session_id}

查询单个会话。

### POST /api/observe

写入单条 message。

```json
{
  "session_id": "uuid",
  "sender_type": "user",
  "role": "user",
  "content": "..."
}
```

### POST /api/observe/batch

批量写入 messages。单次最多 100 条，后端在一个 transaction 中写入；任一 message 校验失败时整批回滚。
