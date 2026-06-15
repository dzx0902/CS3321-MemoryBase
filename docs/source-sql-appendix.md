# 带注释源程序 / SQL 附录

> 用途：回应老师“具有注释的源程序，包括高级语言、SQL 语言等”的要求。最终报告可将本文拆成“附录 A SQL 源程序”和“附录 B 高级语言源程序说明”，源码全文以仓库文件为准，报告正文引用代表性片段即可。

## 8.1 交付口径

MemoryBase 的源程序分为两类：

1. **SQL 源程序**：位于 `database/`，包括扩展初始化、表结构、索引、视图、触发器、seed、演示查询和治理 fixture。
2. **高级语言源程序**：位于 `backend/app/`、`frontend/src/`、`backend/scripts/`、`evaluation/`，包括 FastAPI 后端、React 前端、CLI、数据处理脚本和评测框架。

本项目不建议在最终报告中全文粘贴所有代码。更稳妥的做法是：

- 报告附录列出源程序文件、功能说明和注释位置；
- 正文只摘取最能体现数据库课程要求的 SQL / Python / JSX 片段；
- 完整源码通过仓库文件提交，老师可以按本文清单逐项核对。

## 8.2 SQL 源程序清单

| 文件 | 类型 | 作用 | 注释覆盖 | 报告引用建议 |
|---|---|---|---|---|
| `database/00_init.sql` | SQL 初始化 | 启用 `pgcrypto` 和 `pg_trgm` 扩展 | 已补每个扩展用途注释 | 附录 A；物理设计章节引用 |
| `database/01_schema_core.sql` | DDL | 用户、workspace、Agent、成员表 | 每个核心表前有业务说明 | 附录 A；E-R / 逻辑设计引用 |
| `database/02_schema_memory.sql` | DDL | session、message、source、chunk、memory、evidence、embedding、entity、scene | 每个表前有业务说明，重点解释 evidence / embedding / composite FK | 附录 A；逻辑设计和创新点引用 |
| `database/03_schema_governance.sql` | DDL | Wiki、timeline、recall log、policy、forget、conflict、audit | 每个治理表前有业务说明 | 附录 A；governance 章节引用 |
| `database/04_indexes.sql` | SQL 索引 | B+ tree、GIN、BRIN、covering、partial indexes | 分组注释说明索引用途 | 索引设计章节重点摘录 |
| `database/05_views.sql` | SQL 视图 | active memory、provenance、agent visibility、statistics、conflict view | 每个视图前有用途注释 | 视图设计章节重点摘录 |
| `database/06_triggers.sql` | PL/pgSQL | revision、audit、soft delete、conflict lifecycle、wiki dirty bit | 函数 / 触发器均有用途注释 | 触发器设计章节重点摘录 |
| `database/07_seed.sql` | DML seed | 固定 UUID demo workspace、source、memory、evidence、policy、wiki | 已补阶段性注释，说明每段 seed 的演示意义 | 演示数据附录 |
| `database/08_demo_queries.sql` | SQL 查询 | 课程演示 SQL：provenance、visibility、audit、forget、stats | 查询前有说明注释 | 系统演示 / SQL 查询结果引用 |
| `database/09_graph_demo.sql` | DML seed | 可选 Graph Explorer 清爽图数据 | 已补阶段性注释，说明 graph 节点/边来源 | Graph demo 截图附录 |
| `database/10_governance_demo_fixture.sql` | DML fixture | forgotten / archived / superseded / resolved conflict fixture | 注释密度高，含幂等和治理说明 | Governance demo 附录 |

## 8.3 关键 SQL 片段索引

| 课程要求 | 推荐展示文件 / 片段 | 说明 |
|---|---|---|
| 主键、外键、唯一约束、CHECK | `database/01_schema_core.sql`、`02_schema_memory.sql`、`03_schema_governance.sql` | 表级约束最集中 |
| M:N 关系转换 | `memory_evidence`、`memory_entity`、`memory_scene_cell` | 体现 E-R 到关系模型转换 |
| 范式与受控反规范化 | `memory_item.search_vector`、`current_revision_no`、`wiki_page.needs_rebuild` | 与 `docs/normalization.md` 对应 |
| 全文检索与模糊检索 | `database/04_indexes.sql` 的 GIN / trigram 索引 | 与 search / recall 服务对应 |
| 现代索引 | `idx_audit_brin_time`、`idx_memory_active_ranking` | BRIN + covering index 加分点 |
| 权限视图 | `v_agent_visible_memory` | Agent-aware visibility 关键 SQL |
| 来源追溯视图 | `v_memory_with_source`、`v_wiki_page_sources` | provenance-first 关键 SQL |
| 版本与审计触发器 | `trg_memory_after_insert`、`trg_memory_before_update`、`trg_memory_after_update` | revision + audit 自动化 |
| 软删除 | `trg_memory_soft_delete` | DELETE 转 archived |
| 冲突生命周期 | `trg_conflict_after_insert`、`trg_conflict_after_update` | open conflict 自动改变 memory 状态 |

## 8.4 高级语言源程序清单

### 8.4.1 FastAPI 后端

| 文件 / 目录 | 作用 | 说明依据 | 报告引用建议 |
|---|---|---|---|
| `backend/app/main.py` | FastAPI app 创建、router 挂载、lifespan 清理 | 已补 app lifespan 和 `/api` router 注释 | 系统架构 / 后端入口 |
| `backend/app/api/deps.py` | 依赖注入、数据库单例、service/repository 组装、embedding/LLM provider 选择 | 已补依赖构造和 provider 选择注释 | 模块设计 / 系统实现 |
| `backend/app/api/*.py` | API router 层，定义 sources、memories、recall、search、wiki、governance、graph 等端点 | 代码结构清晰，主要通过路径和 Pydantic model 表达契约 | API 设计章节引用路径表 |
| `backend/app/models/*.py` | Pydantic request/response model | 类型注解即接口说明，适合 API contract 附录 | API request/response 附录 |
| `backend/app/core/database.py` | PostgreSQL 连接封装 | 简洁边界代码 | 系统实现可简述 |
| `backend/app/core/config.py` | 环境变量配置 | 类型化配置 | 部署说明引用 |

### 8.4.2 后端 service / repository

| 文件 | 作用 | 说明依据 | 报告引用建议 |
|---|---|---|---|
| `backend/app/services/source_service.py` | source 导入、checksum、chunk 写入、搜索文本处理 | 依靠现有函数边界，配合 SQL 注释说明 source/chunk | Source 导入模块 |
| `backend/app/services/memory_service.py` | memory 创建、更新、删除、inline agent evidence、生命周期校验 | 已补 lifecycle 和 agent inline evidence 注释 | Memory lifecycle 重点摘录 |
| `backend/app/services/recall_service.py` | keyword/vector/hybrid recall、visibility 过滤、fallback、recall_log | 已补 DB-first recall 和 vector fallback 注释 | Recall / context pack 重点摘录 |
| `backend/app/services/search_service.py` | FTS + trigram + title boost + RRF 多路 search | 依靠现有阈值调参注释 | Search API / RRF 说明 |
| `backend/app/services/context_pack_service.py` | 将 recall 结果格式化成 agent-ready Markdown | 依靠现有函数边界展示 context pack 构造 | Agent 使用章节 |
| `backend/app/services/governance_service.py` | policy、audit、conflict、forget、timeline、agent-visible memory | 已补 governance repository 和 lifecycle query 注释 | Governance 重点摘录 |
| `backend/app/services/memory_extraction_service.py` | rule-based candidate extraction、approve/reject、run audit | 已补 candidate 和 run-level audit 注释 | AI-assisted import 章节 |
| `backend/app/services/embedding_service.py` | local hashing / SiliconFlow embedding、JSONB cache、backfill | 依靠 provider 类名和方法结构 | Hybrid retrieval 附录 |
| `backend/app/services/graph_service.py` | PostgreSQL graph preview、Neo4j sync/load、graph visibility | 已补 optional Neo4j、batch sync、visibility 注释 | Graph Explorer 章节 |
| `backend/app/services/wiki_service.py` | Wiki list/detail/revision/export/batch export | 依靠现有函数边界，并与 `wiki_page` / `wiki_page_revision` SQL 对应 | Wiki projection 章节 |
| `backend/app/services/llm_service.py` | 可选 OpenAI-compatible QA | 依靠现有函数边界；P2 功能，不作为主线 | Future / optional QA |

### 8.4.3 CLI / scripts / evaluation

| 文件 / 目录 | 作用 | 说明依据 | 报告引用建议 |
|---|---|---|---|
| `backend/app/cli/main.py` | `memorybase` / `mb` CLI 入口 | 依靠 Typer command 结构和现有 docstring | Agent 工具入口 |
| `backend/app/cli/commands/*.py` | configure、health、context、recall、search、observe、remember、sessions、eval | 依靠命令函数名、参数说明和 Typer help | CLI 附录 |
| `backend/app/cli/client.py` | CLI HTTP client | 依靠现有函数边界，与 `frontend/src/api/client.js` 类似 | CLI 实现说明 |
| `backend/scripts/backfill_search_terms.py` | seed 后回填 `search_text_zh` | 依靠脚本入口和现有用途说明 | 搜索/分词附录 |
| `evaluation/` | benchmark adapter、metrics、runner、report | 依靠 README 和测试覆盖说明框架边界 | Evaluation 章节 |

### 8.4.4 React 前端

| 文件 / 目录 | 作用 | 说明依据 | 报告引用建议 |
|---|---|---|---|
| `frontend/src/App.jsx` | 页面路由入口 | 依靠路由结构 | 前端页面总览 |
| `frontend/src/api/client.js` | 前端 API client、错误处理、query string 构造、各 API namespace | 已补错误处理、proxy、空参数注释 | API 对账和前端实现 |
| `frontend/src/components/Layout.jsx` | 导航与页面框架 | 依靠组件结构 | UI 架构 |
| `frontend/src/components/Toast.jsx` | 全局提示 | 依靠组件结构 | 前端辅助组件 |
| `frontend/src/pages/sources/*` | source 列表和详情 | 依靠页面名和 API 调用 | Source demo 截图 |
| `frontend/src/pages/memories/*` | memory CRUD、evidence、revision | 依靠页面名和 API 调用 | Memory inspector 截图 |
| `frontend/src/pages/recall/Recall.jsx` | recall、context pack、QA 同页演示 | 已补共享表单注释 | Recall demo 截图 |
| `frontend/src/pages/governance/*` | audit、policies、conflicts、forget requests、timeline | 依靠页面名和 API 调用 | Governance demo 截图 |
| `frontend/src/pages/runtime/*` | sessions、messages、hybrid search | 依靠页面名和 API 调用 | Agent runtime demo |
| `frontend/src/pages/graph/*` | Graph Explorer、SVG 渲染、布局 | 依靠组件结构，并与 `graph_service.py` 对应 | Graph demo 截图 |
| `frontend/src/pages/wiki/WikiExport.jsx` | Wiki export UI | 依靠组件结构，并与 `wiki_service.py` 对应 | Wiki demo 截图 |

## 8.5 最终报告建议摘录

最终报告附录不需要贴全部源码，可选择以下代表片段：

1. `database/02_schema_memory.sql`：`memory_item`、`memory_evidence`、`memory_embedding`。
2. `database/05_views.sql`：`v_memory_with_source`、`v_agent_visible_memory`。
3. `database/06_triggers.sql`：`fn_memory_before_update`、`fn_memory_after_insert`、`fn_memory_after_update`、`fn_memory_soft_delete`、`fn_conflict_after_update`。
4. `backend/app/services/recall_service.py`：权限过滤 + hybrid fallback + `recall_log` 写入。
5. `backend/app/services/memory_extraction_service.py`：candidate extraction + run-level audit。
6. `backend/app/services/graph_service.py`：PostgreSQL graph preview + Neo4j sync + visibility filter。
7. `frontend/src/api/client.js`：统一 API client。
8. `frontend/src/pages/recall/Recall.jsx`：Recall / Context Pack / QA 页面闭环。

这 8 组片段覆盖 SQL DDL、SQL view、PL/pgSQL trigger、Python service、React UI，足够回应“高级语言 + SQL 源程序均具有注释”的要求。

## 8.6 对账结论

当前仓库已经具备：

- SQL 源程序：11 个 `database/*.sql` 文件，核心 DDL / index / view / trigger / seed / query 均有注释。
- 高级语言源程序：FastAPI、React、CLI、script、evaluation 均有清晰目录结构；代表性核心模块已补充解释性注释。
- 报告路径：`docs/process/13-final-report-outline.md` 的“附录 A SQL 源程序”“附录 B 高级语言源程序说明”可直接引用本文作为清单来源。

剩余注意事项：正式报告排版时不要粘贴过长源文件全文，应以“代表片段 + 文件清单 + 仓库路径”方式呈现，避免报告主体被源码淹没。
