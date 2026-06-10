# Gap 3 — 创新点展开

> 用途：可直接纳入最终报告“创新点总结”章节，也可作为答辩时解释项目差异化的材料。本文与 `docs/gap2-research-landscape.md` 对应：Gap 2 说明现有方案缺什么，Gap 3 说明 MemoryBase 如何用已实现的数据库、后端、CLI、前端和评测框架补上这些空缺。

## 3.1 总体创新定位

MemoryBase 的创新点不在于“再做一个聊天机器人”，也不在于“把文档扔进向量库再做 RAG”。项目的核心 thesis 是：

> 面向组织与团队的长期记忆，应该首先被建模为一个可追溯、可治理、可审计、可被 Agent 调用的数据库系统；LLM、embedding、Graph 和 evaluation 都是围绕这个数据库事实源的增强层。

这个定位和现有研究/产品有明显差异：

- 传统 RAG 关注 chunk 检索和回答效果，但通常弱化 memory 生命周期、证据关系、权限和审计。
- MemGPT / Letta / Mem0 等 Agent memory 系统关注 Agent 是否能“记得并用上”，但数据库 schema、触发器、SQL 可验证性、课程级 E-R / 范式 / 索引展示不是主目标。
- ChatGPT Memory、Confluence AI / Rovo、Notion AI 等产品能提供很好的使用体验，但底层 schema、审计链路、权限视图和 EXPLAIN 计划通常不可见。
- GraphRAG 关注图结构辅助检索和全局 sensemaking，但如果把图作为主路径，容易偏离课程项目的关系数据库主线。

MemoryBase 的差异化是 **DB-first AI substrate**：PostgreSQL 是长期记忆的事实源；前端、CLI、Agent、Graph Explorer、Markdown Wiki 和 evaluation 都围绕同一套关系模型工作。

## 3.2 创新点一：文件—数据库双态长期记忆架构

传统文件知识库保留了 Markdown 的可读性，但缺少数据库约束和治理；传统数据库系统结构严谨，但对非结构化文本、Agent context 和 Wiki 导出不友好。MemoryBase 把两者结合成“文件—数据库双态”：

```text
SourceDocument
  -> SourceChunk
  -> MemoryItem
  -> MemoryEvidence
  -> MemoryRevision / AuditLog
  -> RecallLog / AccessPolicy
  -> WikiPage / WikiPageRevision
```

代码和 SQL 证据：

- `source_document` / `source_chunk` 保存原始文档和切片。
- `memory_item` 保存可召回的长期记忆。
- `memory_evidence` 把 memory 绑定回 source chunk。
- `wiki_page` / `wiki_page_revision` 把数据库内容投影成 Markdown Wiki。
- `backend/app/services/source_service.py`、`memory_service.py`、`wiki_service.py` 分别实现导入、记忆维护和 Wiki 导出。

相比只用文件系统，MemoryBase 可以用外键、CHECK、UNIQUE、视图和触发器保证数据一致性；相比只用数据库，它又保留了 Markdown export 和可读 source，使人类用户、答辩演示和 Agent 都能访问同一套知识。

## 3.3 创新点二：Provenance-first 的证据链建模

长期记忆系统最容易被问到的问题是：“这条结论从哪里来？”普通 RAG 往往只能给出 top-k chunk，而 memory 本身、证据、版本和回答之间不是稳定关系。MemoryBase 把 provenance 设计成一等公民。

核心设计：

- `memory_evidence` 是 memory 与 source chunk 的多对多证据桥，支持 `supports`、`refutes`、`context`、`source` 等角色。
- `v_memory_with_source` 把 memory、evidence、chunk、source 串成可查询视图。
- `v_wiki_page_sources` 把 WikiPage 反向追溯到 memory / scene / evidence / source。
- `recall_log.context_pack_json` 记录一次 recall 的过滤参数、top memory 和 context pack 快照。
- `/api/recall/context-pack` 返回 Markdown context，同时带 citation map、supporting evidence、conflict warnings、risk notes 和 excluded memories。

这种建模让系统能回答四类问题：

| 问题 | MemoryBase 的回答路径 |
|---|---|
| 一条 memory 来自哪份 source？ | `memory_evidence -> source_chunk -> source_document` |
| 这次 context pack 选了哪些 memory？ | `recall_log.top_memory_ids_json` / `context_pack_json` |
| 一个 Wiki 页面引用了哪些 source？ | `v_wiki_page_sources` / `wiki_page_revision.frontmatter_json` |
| 证据是支持、反驳还是上下文？ | `memory_evidence.evidence_role` |

这补齐了传统 RAG 和黑盒记忆产品的关键不足：它们能返回结果，但不一定能用 SQL 复现“结果为何出现”。

## 3.4 创新点三：Governance-by-default 的记忆生命周期

组织级长期记忆不能只考虑“写入”和“召回”。真实团队还需要归档、遗忘、冲突处理、权限变更、版本追踪和审计。MemoryBase 把治理能力直接放进 schema 和触发器，而不是作为 UI 装饰。

核心表：

- `memory_revision`：不可变 memory 版本历史。
- `audit_log`：append-only 操作日志，保存 before / after JSON 快照。
- `forget_request`：遗忘申请和审批状态。
- `conflict_record`：冲突记忆对，约束 `left_memory_id < right_memory_id` 防止重复 A/B 与 B/A。
- `access_policy`：用户、Agent 或 role 级策略。
- `timeline_entry`：项目决策演进记录。

核心触发器：

- `trg_memory_after_insert`：memory 创建后写入初始 revision 和 audit。
- `trg_memory_before_update` / `trg_memory_after_update`：memory 修改时递增 revision、写 audit、标记 Wiki 需要 rebuild。
- `trg_memory_soft_delete`：直接 DELETE memory 时转成 archived，避免物理丢失。
- `trg_conflict_after_insert` / `trg_conflict_after_update`：open conflict 自动把相关 memory 标记为 `conflicted`，冲突关闭后在无其他 open conflict 时恢复。
- `trg_wiki_revision_after_insert`：Wiki revision 插入后同步页面当前版本并写 audit。

这使 MemoryBase 的生命周期不是“应用层记得做就做”，而是被数据库约束和触发器强制执行。对数据库课程而言，这也是项目最能体现关系数据库能力的部分：状态机、外键、触发器、审计日志和 SQL 查询共同承担业务规则。

## 3.5 创新点四：Agent-aware visibility，而不是 prompt 里的“请不要看”

很多 Agent 系统把权限问题交给 prompt 或上层工具约定：告诉 Agent 不要读取某些内容。但在组织场景中，权限必须成为数据库查询的一部分。MemoryBase 用 `agent`、`workspace_member`、`access_policy` 和 `v_agent_visible_memory` 实现 Agent 级可见性。

实现方式：

- `agent` 表独立于 `user_account`，允许每个 Agent 有类型、状态和 owner。
- `access_policy` 支持 `principal_type = user / agent / role`，也支持 allow / deny。
- `v_agent_visible_memory` 展开每个 Agent 可见的 active memory，并处理 deny 优先和 role policy。
- `recall_service.py` 和 `search_service.py` 在传入 `agent_id` 时使用 `v_agent_visible_memory` 过滤 memory。
- recall 路径未传 `agent_id` 时默认只允许 `public` / `project` 范围；search 路径采用同类的无 Agent 可见性分支，避免人类或普通前端路径直接看到 private/team memory。
- `graph_service.py` 加载图后也按 Agent 可见 memory 做过滤，避免图视角绕过 memory-level visibility。

这比普通 RAG 的 metadata filter 更强：权限不是临时参数，而是关系模型中的可审计对象。它也比黑盒企业工具更适合课程展示，因为我们能直接展示视图 SQL、策略表、API 行为和测试用例。

当前边界也需要讲清楚：已实现的主线是 **memory-level visibility**。source/chunk 的独立访问控制仍以 workspace 和 active status 为主，若投入生产，需要进一步把 `source_document` / `wiki_page` 的 resource policy 纳入所有读取路径。

## 3.6 创新点五：可解释的 hybrid retrieval 与透明降级

MemoryBase 没有把“向量召回”当成唯一答案。当前检索系统同时保留数据库可解释性和 AI-native 扩展性：

- `source_chunk.search_vector` / `memory_item.search_vector` 使用 PostgreSQL generated `tsvector` + GIN 支撑全文检索。
- `search_service.py` 合并 chunk FTS、memory FTS、trigram fuzzy、title boost，并用 RRF 融合排序。
- `recall_service.py` 支持 `keyword`、`vector`、`hybrid` 三种模式。
- `memory_embedding` / `source_chunk_embedding` 使用 JSONB 缓存 embedding，避免默认依赖 `pgvector`。
- `embedding_service.py` 提供 local hashing provider，可无外网演示；也保留 SiliconFlow provider 扩展路径。
- `retrieval_info` 返回 requested mode、effective mode、embedding provider/model、vector candidate count、fallback reason。
- `recall_log` 记录每次召回的 filter、top memory 和 context pack 快照。

这形成一个重要创新口径：MemoryBase 不假装“向量永远可用”。如果没有 embedding 记录，hybrid recall 会明确降级到 keyword，并把 fallback reason 返回给 UI / API。相比普通 RAG demo 只展示结果，这种透明降级更符合组织系统的可观测性要求。

与 `pgvector` 的关系也要讲清楚：本项目选择 JSONB embedding cache 是课程演示和部署稳定性的取舍，不是说 JSONB 比 pgvector 更适合大规模向量检索。未来数据量增大时，pgvector / HNSW / IVFFlat 是自然演进方向；当前版本重点证明“可降级、可审计、可接入 Agent”的检索闭环。

## 3.7 创新点六：AI-assisted candidate extraction，但不让 LLM 成为 P0 依赖

很多长期记忆产品依赖 LLM 自动抽取，这在效果上有优势，但课程演示和本地复现会被 API key、模型质量、网络环境影响。MemoryBase 采用分层策略：

- P0 能力不依赖外部 LLM：人工创建 memory、规则抽取、keyword recall、Wiki 导出、审计和治理都能本地运行。
- `memory_extraction_service.py` 实现 rule-based extraction，从 chunk 生成 `status = candidate` 的 memory。
- candidate memory 自动绑定 `memory_evidence`，不会成为无来源草稿。
- `/api/memory-candidates/{memory_id}/approve` 和 `/reject` 把候选记忆纳入生命周期状态机。
- extraction run 写入 `audit_log` 的 `memory_extraction.run.start` 和 `memory_extraction.run.complete`，保留 run_id、chunk_ids、候选数量和 candidate memory ids。

这个设计避免了两个极端：一端是完全不做自动抽取，所有文档都要人工处理；另一端是把 LLM 输出直接写成事实，缺少审批和证据链。MemoryBase v1 选择“候选 -> 审批 -> active”的中间路线，既能演示 AI-assisted import，又保留治理闭环。

未来可扩展方向是引入 `analysis_run` / `analysis_memory_draft` / `analysis_draft_evidence` 这类更完整的 LLM 分析草稿表，但当前版本已经可以用主表生命周期 + audit_log run trace 回答“这次抽取产生了哪些候选”。

## 3.8 创新点七：Graph Explorer 作为 provenance 可视化层

GraphRAG 和知识图谱系统强调实体关系和图检索。MemoryBase 吸收了图的可解释性，但没有让图替代 PostgreSQL。

当前实现：

- `graph_service.py` 可以从 PostgreSQL 构建 workspace graph，节点包括 workspace、source、chunk、memory、entity、scene、wiki。
- 边包括 `CONTAINS`、`HAS_CHUNK`、`CREATED_FROM`、`SUPPORTED_BY`、`MENTIONS`、`CONTAINS_MEMORY`、`DERIVED_FROM`。
- `/api/graph/workspace/preview` 在没有 Neo4j 时也能返回 PostgreSQL preview。
- `/api/graph/workspace/sync` 可选同步到 Neo4j，并写入 `audit_log` 的 `graph.sync`。
- `GraphExplorer.jsx` / `GraphSvg.jsx` 提供前端关系图展示。

创新点在于定位：图层是 provenance 与关系展示的增强层，不是事实源。PostgreSQL 仍负责约束、版本、权限、审计和查询；Neo4j 只是可选缓存 / 可视化后端。这样既能展示图结构，又不会把数据库课程主线变成知识图谱项目。

## 3.9 创新点八：Evaluation 作为系统验证层，而不是产品主线替代品

MemoryBase 已经包含 evaluation framework，覆盖 synthetic datasets、local baselines、live API modes、adapter、metrics、runner 和 report generation。它的作用不是把项目包装成 benchmark-only 产品，而是回答：“这个数据库设计是否真的能支持长期记忆任务？”

已实现能力：

- `evaluation/datasets/` 包含 conflict、deletion、performance、preference、synthetic memory cases。
- `evaluation/metrics/` 覆盖 retrieval、QA、forgetting、system metrics。
- `evaluation/runners/` 覆盖 retrieval、QA、forgetting、conflict、deletion、preference、performance 以及 LoCoMo / LongMemEval / MemoryAgentBench 等外部 benchmark runner。
- `evaluation/reports/generate_report.py` 生成评测报告。
- `backend/app/cli/commands/eval.py` 提供 CLI gold-set evaluation 入口。
- 后端测试中有 `test_evaluation_baselines.py`、`test_evaluation_adapters.py`、`test_evaluation_judging.py`、`test_evaluation_metrics.py`、`test_evaluation_runner_checkpoint.py` 等验证 evaluation 基础行为。
- 当前已完成一次 LongMemEval oracle 500-case live `db_qa` 运行，结果记录在 `docs/27-longmemeval-full-evaluation-20260609.md` 和 `evaluation/results/longmemeval_full_20260609.csv`：deterministic pass 为 35.2%，DeepSeek semantic judge pass 为 58.4%。

这使项目比普通课程 CRUD 系统多一层“可量化验证”。LongMemEval 的当前结果不高，尤其是 multi-session reasoning 和 preference following 仍明显弱于专门优化长期记忆问答的系统；因此报告不应把 benchmark 分数作为主卖点。MemoryBase 的独立价值在于：它用 evaluation 暴露数据库记忆层在 retrieval、forgetting、conflict、system behavior 和 answer generation 上的真实边界，同时保留 provenance、governance、multi-tenant visibility、audit trail 和 SQL-verifiable lifecycle 这些专门记忆产品通常不突出展示的数据库系统能力。

需要在报告中保持诚实：当前 LongMemEval 数字适合作为工程验证和限制分析，不适合作为对外榜单 claim。LoCoMo 全量结果、MemoryAgentBench 非 conflict 任务、更独立的 judge model、groundedness / hallucination 评估和更强 baseline 对照可以作为 future work；当前主线仍是 database-backed evaluation harness 和可运行的本地 / API 评测路径。

## 3.10 创新点九：人和 Agent 共用同一套数据库入口

MemoryBase 不是只给前端用户看的系统，也不是只给 Agent 的隐藏工具。它同时提供：

- React 前端：Dashboard、Sources、Memories、Recall、Wiki、Governance、Runtime、Graph 页面。
- FastAPI：sources、memories、recall、search、wiki、governance、agents、sessions、observe、semantic、stats、graph、embeddings、qa 等端点。
- CLI：`memorybase` / `mb`，支持 configure、health、context、recall、search、observe、remember、sessions、eval。
- Agent runtime 入口：`agent_session` / `message` 表 + observe / remember / context pack API。

这个多入口设计的重点不是“页面多”，而是 **同一套 source / memory / evidence / audit 数据结构同时服务人类和 Agent**。人类可以浏览、编辑、审批和导出；Agent 可以 search / recall / context / remember；管理员可以看 audit、policy、conflict 和 forget request。

这补齐了现有系统常见的割裂：

- 文件知识库适合人读，但 Agent 使用不稳定。
- Agent memory store 适合 Agent，但人类审计和治理弱。
- 企业 AI 工具适合协作，但数据库内部不可展示。

MemoryBase 把这三者统一到数据库应用系统中。

## 3.11 与研究现状的差异化总结

| 研究/产品路线的不足 | MemoryBase 的对应创新 | 主要实现证据 |
|---|---|---|
| RAG 只给 top-k chunk，证据链弱 | Provenance-first evidence chain | `memory_evidence`、`v_memory_with_source`、context pack |
| Agent memory 关注效果，治理弱 | Governance-by-default lifecycle | `memory_revision`、`audit_log`、`forget_request`、`conflict_record`、触发器 |
| 黑盒产品不可展示 schema / SQL | DB-first 可验证 substrate | `database/*.sql`、EXPLAIN、索引、视图、触发器 |
| prompt 权限不可靠 | Agent-aware visibility | `access_policy`、`v_agent_visible_memory`、recall/search filters |
| 向量检索依赖外部服务 | Hybrid retrieval with transparent fallback | JSONB embedding cache、local hashing、`retrieval_info` |
| LLM 抽取不可控 | Candidate extraction + approval | `memory_extraction_service.py`、candidate/approve/reject、run audit |
| 图系统容易替代数据库主线 | Graph as optional provenance visualization | PostgreSQL preview、optional Neo4j sync、`graph.sync` audit |
| benchmark 与产品割裂 | Evaluation as validation layer | `evaluation/` runners/metrics/reports、LongMemEval 500-case result、CLI eval |

## 3.12 答辩推荐口径

如果只用一句话概括创新点：

> MemoryBase 把 AI 长期记忆从“模型或向量库里的黑盒能力”转化为一个以 PostgreSQL 为事实源的组织级数据库系统，核心创新是 provenance、governance、agent-aware visibility、transparent retrieval fallback 和 evaluation-backed validation。

如果分点讲，建议用五点：

1. **DB-first AI substrate**：长期记忆先进入关系模型，LLM / embedding / Graph 都是增强层。
2. **Provenance-first**：memory、source chunk、evidence、Wiki、recall log 可以被 SQL 串起来。
3. **Governance-by-default**：revision、audit、forget、conflict、policy 被 schema 和 trigger 固化。
4. **Agent-aware visibility**：Agent 不是普通用户别名，而是有独立身份和可见视图的 principal。
5. **Evaluation-backed**：评测框架验证 retrieval、forgetting、conflict 和长期记忆行为，不只做 UI demo。

## 3.13 边界与未来增强

为了避免答辩中过度承诺，需要明确当前版本边界：

- 自动抽取是 rule-based v1，不是完整 LLM analysis pipeline；LLM 高质量抽取属于后续增强。
- JSONB embedding cache 适合课程规模和可部署性，不替代大规模 `pgvector` / ANN。
- Agent visibility 当前主线覆盖 memory-level recall/search/graph 过滤；source/wiki 的细粒度策略可继续扩展。
- Graph Explorer 是 provenance 可视化和可选关系缓存，不是默认 GraphRAG 检索主路径。
- Evaluation framework 已具备本地和 API 模式，并有 LongMemEval 500-case 工程验证结果；但完整 LoCoMo / MemoryAgentBench 对照、正式榜单数字和独立 judge 仍需后续补齐。

这些边界不削弱项目创新，反而说明系统设计有清晰主线：先把数据库层做成可复现、可治理、可演示的事实源，再逐步接入更强的模型、向量索引和评测数据。
