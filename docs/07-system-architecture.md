# 系统总体架构

本文档描述 HEAD `2dd0d64` 的实际系统结构。MemoryBase 是一个以
PostgreSQL 为核心的组织级 / 团队级可追溯记忆数据库，前端、CLI、
Agent 调用和评测框架都围绕同一套数据库事实源工作。

## 1. 总体架构图

```text
Human User / Admin / Agent / Evaluation Runner
             |
             v
React Frontend        MemoryBase CLI (`mb` / `memorybase`)
             \          /
              v        v
            FastAPI Backend
              |
              v
        API layer (`backend/app/api`)
              |
              v
      Service + Repository layer
              |
              v
 PostgreSQL core database  <---- optional ---->  Neo4j graph cache
              |
              v
 Markdown Wiki files / evaluation reports / screenshots
```

设计重点是 **DB-first**：所有长期记忆、证据、权限、版本、审计、
召回日志和 Wiki 投影都先进入 PostgreSQL。前端和 CLI 只是不同入口；
evaluation runner 用同一套 API / service contract 度量系统表现。

## 2. 后端模块

当前后端目录以 FastAPI `api/` router + service/repository 分层为主：

```text
backend/app/
  main.py
  core/
    config.py
    database.py
  api/
    health.py
    sources.py
    memories.py
    memory_extraction.py
    recall.py
    search.py
    wiki.py
    governance.py
    agents.py
    sessions.py
    observe.py
    semantic.py
    stats.py
    graph.py
    embeddings.py
    qa.py
  services/
    source_service.py
    memory_service.py
    memory_extraction_service.py
    recall_service.py
    search_service.py
    context_pack_service.py
    wiki_service.py
    governance_service.py
    agent_service.py
    conversation_service.py
    semantic_service.py
    stats_service.py
    graph_service.py
    embedding_service.py
    llm_service.py
  models/
    *.py
  cli/
    main.py
    commands/
```

### 2.1 API layer

| API file | 主要端点 | 作用 |
|---|---|---|
| `sources.py` | `/api/sources` | 导入和查看 source document / chunks |
| `memories.py` | `/api/memories` | 创建、查看、编辑、软删除 memory |
| `memory_extraction.py` | `/api/memory-extraction/*`, `/api/memory-candidates/*` | rule-based 候选记忆抽取、approve / reject |
| `recall.py` | `/api/recall`, `/api/recall/context-pack` | keyword / vector / hybrid recall 与 context pack |
| `search.py` | `/api/search` | 面向 Agent/CLI 的 zero-config lexical search |
| `wiki.py` | `/api/wiki/*` | Wiki 页面列表、详情、版本和导出 |
| `governance.py` | `/api/policies`, `/api/audit`, `/api/conflicts`, `/api/forget-requests`, `/api/timeline` | 权限、审计、冲突、遗忘和时间线 |
| `agents.py` | `/api/agents/*` | Agent 注册与可见 memory 查询 |
| `sessions.py` / `observe.py` | `/api/sessions`, `/api/observe` | Agent Runtime 会话与消息落库 |
| `semantic.py` | `/api/entities`, `/api/scenes` | 实体和场景查询 |
| `stats.py` | `/api/stats/overview` | Dashboard 统计 |
| `graph.py` | `/api/graph/*` | PostgreSQL graph preview 与可选 Neo4j sync/load |
| `embeddings.py` | `/api/embeddings/*` | local hashing / provider embedding 生成与回填 |
| `qa.py` | `/api/qa/answer` | 基于 recall context 的可选 LLM 问答 |

### 2.2 Service layer

Service 层封装业务规则和 SQL repository：

- `source_service.py`：导入文档、计算 checksum、切分 chunk、写入搜索文本。
- `memory_service.py`：memory lifecycle 校验、evidence 绑定、inline agent note。
- `memory_extraction_service.py`：rule-based extraction，创建 `candidate`
  memory，并写入 run-level `audit_log`。
- `recall_service.py`：keyword / vector / hybrid recall、权限过滤、
  retrieval fallback metadata、`recall_log`。
- `search_service.py`：chunk / memory / source 多路 lexical search 与 RRF 排序。
- `governance_service.py`：policy、audit、conflict、forget request、
  timeline、agent-visible memory。
- `graph_service.py`：PostgreSQL workspace graph 构建、可见性过滤、
  Neo4j 同步和载入。
- `embedding_service.py`：local hashing provider、SiliconFlow provider、
  memory/chunk embedding cache。
- `llm_service.py`：可选 OpenAI-compatible / SiliconFlow / DeepSeek QA。

## 3. 数据库层

PostgreSQL 是唯一必需数据库。核心 SQL 文件：

| 文件 | 内容 |
|---|---|
| `database/00_init.sql` | `pgcrypto`、`pg_trgm` 扩展 |
| `database/01_schema_core.sql` | 用户、工作区、Agent、成员 |
| `database/02_schema_memory.sql` | 会话、source、chunk、memory、evidence、embedding、entity、scene |
| `database/03_schema_governance.sql` | Wiki、timeline、recall log、policy、forget、conflict、audit |
| `database/04_indexes.sql` | B+ tree / GIN / BRIN / covering / partial indexes |
| `database/05_views.sql` | active memory、provenance、statistics、agent visibility 等视图 |
| `database/06_triggers.sql` | revision、audit、soft delete、wiki dirty bit、conflict lifecycle |
| `database/07_seed.sql` | 课程演示 workspace seed |
| `database/08_demo_queries.sql` | 课程演示 SQL 查询 |
| `database/10_governance_demo_fixture.sql` | forgotten / archived / superseded / resolved conflict fixture |

可选 Neo4j 只作为 graph explorer 的缓存 / 可视化后端；PostgreSQL preview
路径仍可在没有 Neo4j 时返回 workspace graph。

## 4. 前端页面

当前前端按工作流分组：

| 分组 | 页面 |
|---|---|
| Dashboard | `Dashboard.jsx` |
| Sources | `sources/SourceList.jsx`, `sources/SourceDetail.jsx` |
| Memories | `memories/MemoryList.jsx`, `MemoryDetail.jsx`, `MemoryCreate.jsx`, `MemoryEdit.jsx` |
| Recall | `recall/Recall.jsx` |
| Wiki | `wiki/WikiExport.jsx` |
| Governance | `governance/Policies.jsx`, `Audit.jsx`, `Conflicts.jsx`, `ForgetRequests.jsx`, `Timeline.jsx` |
| Runtime | `runtime/Sessions.jsx`, `Messages.jsx`, `HybridSearch.jsx` |
| Graph | `graph/GraphExplorer.jsx`, `GraphSvg.jsx`, `graphLayout.js` |

前端默认演示路径偏向人类用户：Recall 页面默认 keyword 模式，避免在未回填
embedding 的 demo DB 中每次都显示 hybrid fallback。后端 API 默认仍为
`hybrid`，并通过 `retrieval_info` 明确返回 requested/effective mode、
候选数量和 fallback reason。

## 5. CLI 与 Agent 入口

`pyproject.toml` 暴露两个命令：

```text
memorybase
mb
```

CLI 命令覆盖 configure、health、context、recall、search、observe、
remember、sessions 和 eval。它面向 Agent 的 "grep-style database access"：
Agent 可以用 search / recall 找证据，用 remember 写入带 inline evidence 的
memory，用 sessions / observe 把上下文落库。

## 6. Evaluation 扩展

`evaluation/` 不是数据库主线的替代品，而是验证 MemoryBase 在长期记忆任务上的
扩展能力：

- adapters：BEAM、BEIR、LoCoMo、LongMemEval、MemoryAgentBench。
- metrics：retrieval、QA、forgetting、system。
- runners：conflict、deletion、forgetting、locomo、longmemeval、
  memoryagentbench、performance、preference、QA、retrieval。
- reports：生成评测报告。

最终报告中应把 evaluation 放在"创新与验证"章节，而不是取代数据库设计章节。

## 7. 关键运行链路

### 7.1 Source 到 Memory

```text
POST /api/sources
  -> source_service.import_source()
  -> source_document + source_chunk
  -> optional memory_extraction.from_chunks()
  -> memory_item(status='candidate') + memory_evidence
  -> approve/reject candidate
```

### 7.2 Recall 到 Context Pack

```text
POST /api/recall
  -> recall_service
  -> permission filter (public/project or v_agent_visible_memory)
  -> keyword FTS / trigram + optional embedding candidates
  -> recall_log with retrieval_info
  -> context_pack_service formats Markdown for agents/UI
```

### 7.3 Governance Lifecycle

```text
memory update/delete/conflict/forget/wiki revision
  -> database trigger or governance_service
  -> memory_revision / audit_log / conflict_record / forget_request
  -> frontend governance pages and demo SQL queries
```

## 8. 设计取舍

- 数据库层是事实源，Markdown/Wiki 是可读投影。
- P0 不依赖 LLM；rule-based extraction 和 local hashing embedding 可在无外网时演示。
- Hybrid recall 是增强路径；无 embedding 时系统显式降级并报告原因。
- `v_agent_visible_memory` 是 per-agent visibility view，调用方必须按
  `agent_id` 过滤。
- Evaluation 是扩展验证能力，数据库建模、索引、视图、触发器和治理链路仍是课程主线。
