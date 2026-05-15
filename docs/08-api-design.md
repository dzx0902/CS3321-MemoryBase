# API 设计文档

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
  "evidence_chunk_ids": ["uuid"]
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
  "query_text": "为什么放弃校园食堂系统？"
}
```

返回 memory + evidence + source chunk。

## 5. Wiki API

### POST /api/wiki/export

导出 Markdown Wiki。

## 6. Audit API

### GET /api/audit

查询审计日志。

## 7. Policy API

### POST /api/policies

创建权限策略。

### GET /api/policies

查询权限策略。

## 8. Conflict API

### GET /api/conflicts

查询冲突记忆。
