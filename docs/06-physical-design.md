# 物理结构设计

## 1. 数据库选择

主方案采用 PostgreSQL，保底方案保留 SQLite。

| 维度 | PostgreSQL | SQLite |
|---|---|---|
| 部署难度 | 中等，需要服务或 Docker | 极低 |
| 展示数据库能力 | 强，支持复杂视图、JSONB、GIN、触发器 | 中等 |
| 全文检索 | tsvector + GIN | FTS5 |
| 多人协作 | 强 | 弱 |
| 课程表现 | 更正式 | 更稳定保底 |

最终推荐：

```text
主方案：PostgreSQL
保底方案：SQLite + FTS5
```

## 2. 数据库名称

```text
memorybase_db
```

## 3. Schema 设计

课程项目可直接使用 `public` schema，避免过度复杂化。

如果后续扩展，可拆成：

```text
memorybase_core
memorybase_governance
memorybase_export
```

## 4. 存储路径设计

```text
project-root/
  data/
    raw_sources/
    uploads/
    markdown_wiki/
    exports/
    backups/
    logs/
```

## 5. 索引策略

| 场景 | 索引 |
|---|---|
| workspace 下查询 source | source_document(workspace_id, imported_at DESC) |
| 会话列表 | agent_session(workspace_id, started_at DESC) |
| 会话消息 | message(session_id, created_at) |
| workspace 下查询 memory | memory_item(workspace_id, status) |
| 按类型筛选 | memory_item(workspace_id, memory_type, status) |
| 时间线 | timeline_entry(workspace_id, event_time DESC) |
| 全文检索 | source_chunk USING GIN(search_vector) |
| 实体召回 | memory_entity(entity_id, memory_id) |
| 审计回放 | audit_log(workspace_id, created_at DESC) |
| 权限过滤 | access_policy(workspace_id, principal_type, principal_id) |
| role/global 权限去重 | access_policy partial UNIQUE indexes for NULL / non-NULL principal_id |
| 冲突列表 | conflict_record(workspace_id, status, created_at DESC) |
| 遗忘请求列表 | forget_request(workspace_id, status, requested_at DESC) |

## 6. 视图策略

| 视图 | 用途 |
|---|---|
| v_active_memory | 查询 active 且仍在有效期内的 memory，使用显式列名避免 schema 漂移 |
| v_memory_with_source | 串联 memory、evidence、source chunk 和 source document，支持来源追溯与行号展示 |
| v_agent_visible_memory | 基于 `app.agent_id` 和 AccessPolicy 过滤 Agent 可见 memory，未设置 agent 时默认不返回数据 |
| v_project_timeline | 串联 timeline、memory 和 source，支持项目决策演进展示 |
| v_conflict_memory | 展开 conflict_record 两端 memory，支持冲突页面和 SQL 演示 |
| v_wiki_page_sources | 追溯 WikiPage 由 memory 到 evidence/source chunk 的来源链路 |
| v_memory_statistics | 按 workspace、类型、状态、访问级别统计 memory |

## 7. 备份与恢复

| 对象 | 备份方式 | 恢复方式 |
|---|---|---|
| PostgreSQL 数据库 | pg_dump | psql 导入 |
| SQLite 数据库 | 复制 .db 文件 | 替换 .db 文件 |
| Markdown Wiki | zip 或 git commit | 解压或 git checkout |
| 上传文件 | 复制 uploads | 还原目录 |
| SQL 结果 | 保存 exports/sql_results | 用于报告截图 |
