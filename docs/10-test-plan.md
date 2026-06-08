# 测试计划

本文档按当前 `backend/tests/test_*.py` 与前端构建脚本整理测试覆盖。最终报告中
应把这里作为测试方案来源，并在提交前补充最新一次命令输出截图。

## 1. 后端 API 与服务测试

| 测试文件 | 覆盖目标 | 关键断言 |
|---|---|---|
| `test_health.py` | health API | 服务与数据库状态返回正确 |
| `test_sources.py` | Source API | 导入、列表、详情、forgotten source 过滤 |
| `test_memories.py` | Memory API | 创建、详情、更新、软删除、evidence/revision |
| `test_postgres_integration.py` / `test_evaluation_baselines.py` | Candidate extraction | candidate 创建、approve/reject 生命周期、run-level audit |
| `test_recall_query.py` | Recall query | keyword/hybrid recall、权限过滤、retrieval_info |
| `test_context_pack.py` | Context pack | token budget、citation、excluded/risk/conflict metadata |
| `test_recall_wiki.py` | Recall + Wiki | recall 结果与 wiki provenance 结合 |
| `test_search_api.py` | Lexical search | chunk/memory/source scope、tokenized_query、权限过滤 |
| `test_governance.py` | Governance | policy、audit、conflict、forget request、verification |
| `test_agent_registration.py` | Agent API | 注册 Agent、可见 memory |
| `test_semantic.py` | Entity / Scene API | entity 和 scene 查询 |
| `test_stats.py` | Stats overview | dashboard count 与 breakdown |
| `test_graph_api.py` | Graph API | health、preview、load、sync contract |
| `test_graph_service.py` | Graph service | PostgreSQL graph build、Neo4j batch sync、visibility filter |
| `test_embeddings.py` | Embedding service/API | local hashing、memory/chunk embedding、backfill |
| `test_embedding_schema.py` | Embedding schema | cache 表结构与约束 |
| `test_qa.py` | QA API | recall context + optional LLM answer path |
| `test_workspace_slug_schema.py` | Workspace schema | slug 唯一和 workspace contract |
| `test_postgres_integration.py` | PostgreSQL integration | schema / seed / trigger 基础集成 |

## 2. CLI / Agent Runtime 测试

| 测试文件 | 覆盖目标 | 关键断言 |
|---|---|---|
| `test_cli_skeleton.py` | CLI 命令骨架 | `mb` / `memorybase` 命令可发现 |
| `test_cli_context.py` | Context render | CLI context 输出结构和 token 控制 |
| `test_cli_recall.py` | CLI recall | 参数映射到 recall API |
| `test_cli_sessions.py` | CLI sessions | 创建/列出 session |
| `test_cli_writeback.py` | CLI remember / observe | Agent 写回 memory 和 inline evidence |
| `test_repo_context.py` | Repo context | 工作区上下文发现 |

## 3. Evaluation Framework 测试

| 测试文件 | 覆盖目标 | 关键断言 |
|---|---|---|
| `test_evaluation_adapters.py` | BEAM / BEIR / LoCoMo / LongMemEval / MemoryAgentBench adapters | 外部 benchmark case 能转换为统一格式 |
| `test_evaluation_baselines.py` | baseline runner | baseline 输出结构稳定 |
| `test_evaluation_report.py` | report generation | 指标可聚合成报告 |

## 4. 数据库演示测试

| 命令 | 预期 |
|---|---|
| `npm run db:setup` | drop/recreate public schema，加载 00-06、07 seed、search backfill、10 governance fixture、08 demo queries |
| `npm run db:check` | 输出 workspace、memory、conflict、timeline 基础状态 |
| `psql $DATABASE_URL -f database/08_demo_queries.sql` | 13 个课程演示查询可执行 |

重点 SQL 验证：

- memory delete 走 `trg_memory_soft_delete`，状态变为 `archived`。
- memory insert/update 触发 `memory_revision` 与 `audit_log`。
- open conflict 触发相关 active memory 变为 `conflicted`。
- forget request 审批后 target 被软治理，verification 写入 `audit_log`。
- `v_agent_visible_memory` 查询必须显式按 `agent_id` 过滤。

## 5. 前端验证

| 命令 | 预期 |
|---|---|
| `cd frontend && npm run lint` | React 代码 lint 通过 |
| `cd frontend && npm run build` | Vite production build 通过 |

最终截图前还需要人工/浏览器验证这些页面：

- Dashboard
- Source list/detail
- Memory list/detail/edit
- Recall + retrieval_info fallback badge
- Wiki export/list/detail
- Governance: audit / conflicts / forget requests / policies / timeline
- Runtime: sessions / messages / hybrid search
- Graph Explorer

## 6. 最终提交前检查命令

```bash
uv run ruff check backend/app backend/tests evaluation
uv run --with pytest python -m pytest backend/tests -q
cd frontend && npm run lint && npm run build
git diff --check
```

这些命令通过后，再把输出截图或摘录放入最终报告的"测试结果"章节。
