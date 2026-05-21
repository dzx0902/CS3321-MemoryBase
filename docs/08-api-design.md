# API 设计文档

本文档是课程报告用的 API 摘要。后端实现、前端 mock 与集成验收以 `docs/15-api-contract-plan.md` 的执行契约为准。

## 1. Health

### GET /api/health

返回后端状态。

## 2. Source API

### POST /api/sources

导入 Markdown / txt 文档。

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

查询 source 列表。

### GET /api/sources/{id}

查询 source 详情和 chunks。

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

### GET /api/memories

查询 memory 列表。

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

查询 memory 详情、evidence、revision。

### PATCH /api/memories/{id}

修改 memory，自动生成 revision 和 audit。

### DELETE /api/memories/{id}

软删除 memory。

## 4. Recall API

### POST /api/recall

执行关键词 / 全文检索。

```json
{
  "workspace_id": "uuid",
  "agent_id": "uuid",
  "query_text": "为什么放弃校园食堂系统？",
  "memory_type": "decision",
  "access_level": "project",
  "status": "active",
  "limit": 10
}
```

返回 memory + evidence + source chunk，并写入 `recall_log`。

## 5. Wiki API

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
action_type
target_type
target_id
start_time
end_time
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

## 7. Policy API

### POST /api/policies

创建权限策略。

### GET /api/policies

查询权限策略。

## 8. Conflict API

### GET /api/conflicts

查询冲突记录及左右两侧 memory。

### PATCH /api/conflicts/{id}

更新 conflict 状态。

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

审批遗忘请求。对 `memory_item` 请求，`approved` 或 `done` 会将目标 memory 标记为
`forgotten` 并写入审计日志。

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
