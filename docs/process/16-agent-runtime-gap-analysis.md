# Agent Runtime 视角的差距分析与改进路线

> 本文档不是 P0/P1 课程需求的一部分，而是"如果要把 MemoryBase 从课程作品演进成 agent 真正可用的 memory layer"的对照表。后续每开一个 P2/P3 issue 都可以回到这里看一眼。

## 1. 当前定位（一句话）

MemoryBase 现在是一个**优秀的"档案治理"系统**：扎实的关系建模、3NF 分析、复合 FK、完整的 policy/audit/conflict/forget 治理链，以及 agent-visible view、conflict 联动触发器、宽范围 audit lifecycle 和 as-of recall。但它仍是 **file-first / manual / sync archive / keyword-only**，不是 agent runtime 的在线 memory layer。

核心错配：
- 入口是 **Markdown 文件**，不是 conversation turn
- 创建/分类/抽取/冲突检测全是 **手动**
- API 是 **给前端 React UI 用的**，不是给 agent runtime 调的
- 检索是 **PostgreSQL FTS**（对中文几乎不分词，对意图改写完全无效）

### 1.1 当前如果给 agent 用，应该怎么用

现阶段不要把 MemoryBase 当成"会自己记忆的 agent brain"，而应该当成**项目事实库 + 证据库 + 审计库**：

```text
agent start
  -> recall(query/task) 拉取相关 MemoryItem + Evidence + SourceChunk
  -> 把 context_pack 转成短 Markdown 注入上下文
  -> agent 执行任务
  -> 人或脚本把新决策/风险/事实写回 MemoryItem
  -> 必要时导出 WikiPage 供人审查
```

这个使用路径的价值在于"可追溯可信"：agent 不只是得到一段摘要，还能看到每条记忆来自哪个 source chunk、何时被修订、谁修改过、是否受权限控制。它不如 Mem0 / Letta 自动，但比普通 RAG 更适合课程项目、团队决策记录和需要审计的研发场景。

## 2. Agent 实际使用视角的缺口

### 2.1 没有 in-line 写记忆的 API

`POST /api/memories` 强制要求 `evidence[].chunk_id`。agent 在线对话产生的事实（如"用户咖啡因摄入 < 200mg"）根本没有 source chunk。

**缺什么**：`POST /api/observe { session_id, role, content }`，内部生成虚拟 chunk + memory，或允许 evidence 为空。

### 2.2 检索质量不够 agent 用

- 中文 FTS 不分词，`recall("为什么放弃食堂方向")` 匹配不上 `canonical_text="校园食堂系统被否决"`。
- 没有 embedding 列、没有 pgvector、没有 hybrid rank（BM25 + 语义融合）。
- recall_log 记了但没有反馈循环（点击/有用/无用反馈不回流到 ranking）。

### 2.3 没有 conversation / session / turn 的 live 流

`Session / Message` 在文档里出现，schema 里基本是死的，没接到 agent runtime。缺 `POST /api/sessions/{id}/turns`、缺 streaming write、缺持续灌对话的入口。

### 2.4 没有 working memory vs long-term memory 的分层

单一的"已沉淀知识库"概念。agent 下一次跑回来不知道上次聊到哪、不知道任务进行到什么程度。`importance` 是手填 1-5 静态值，没有访问衰减、没有 LRU、没有自动晋升/降级。

### 2.5 没有 LLM 自动抽取

自动 distill、自动 entity 链接、自动 scene 归类、自动冲突检测 —— 仍然没有形成在线管线。当前已经有 `POST /api/conflicts` 和 trigger 驱动的冲突生命周期：open conflict 会把相关 memory 标记为 `conflicted`，解决后自动恢复。但"写入一条新 memory 时自动判断是否矛盾并登记 conflict_record"还没有实现。

### 2.6 缺 agent-friendly 协议

没有 CLI、SDK、OpenAPI tool spec 或可安装的 agent adapter。API 完全是给前端调的形态。

本项目后续默认优先考虑 **CLI / `uv tool` 可安装形态**，而不是 MCP-first。原因是 CLI 更容易审查、调试、脚本化、接入 Codex/Claude Code/GitHub Actions，也更符合本项目"文件—数据库双态"的工程气质。MCP 可以作为后续可选适配层，但不应成为第一条必经路线。

### 2.7 没有 agent 身份/persona

`agent` 只是 actor_id 字符串，没有 agent capability、context、persona 表。Letta 的 core block（persona / human / memory）完全没有对应。

### 2.8 没有时间维度记忆

`valid_to / valid_from` 已经接入 `POST /api/recall` 的 `as_of` 过滤，可以做基础时态召回。但这仍不是完整 temporal knowledge graph：没有事实区间推理、事件版本合并和多时间点对比。

### 2.9 没有 agent-ready context pack 格式

`POST /api/recall` 返回 JSON，但 agent 最需要的是可直接注入上下文的、长度受控的 Markdown：

```md
## Relevant Memories
- [decision] ...

## Evidence
- Source: discussion_01.md lines 12-24

## Known Conflicts / Risks
- ...

## Do Not Assume
- ...
```

缺少这层会导致每个 agent 客户端都要自己拼接 context，格式不统一，也难以做 token budget、去重和引用编号。

### 2.10 缺少写入质量控制

当前可以写 memory，但没有"值得记吗"的判定层，也没有重复检测、相似记忆合并、事实更新策略。实际 agent runtime 中，写入错误比检索错误更危险：垃圾记忆会长期污染 recall。

最低限度需要：

- relevance gate：普通闲聊、临时状态、重复内容不入库
- duplicate check：同一事实不要重复写多条
- update policy：新事实是补充、替换，还是冲突
- confidence policy：LLM 抽取结果不能默认 1.0 confidence

### 2.11 缺少评测集和回归指标

`recall_log` 已经能记录查询，但还没有形成"固定问题集 -> 期望 memory/evidence -> P@K / recall@K / citation correctness"的回归测试。和 Mem0、EverOS、GBrain 这类项目相比，MemoryBase 现在没有办法客观证明 recall 质量是否变好了。

课程阶段可以先用 10 个 demo questions 做小型 gold set，不必立刻上复杂 benchmark。

### 2.12 前端还不是记忆操作台

数据库和后端已经能支撑主线，但前端仍缺 Memory / Recall / Wiki / Audit / Conflict 的真实页面。对人类 reviewer 来说，没有操作台就很难审查 agent 写入的记忆是否可信。

## 3. 对比知名项目

| 项目 | 核心卖点 | MemoryBase 对应 | 差距 |
|---|---|---|---|
| **Mem0** | `add(messages)` / `search(query)` 两行 SDK；自动 ADD/UPDATE/DELETE/NOOP 4 操作；自动去重与冲突解决；user-scoped | 已有手动 CRUD、ConflictRecord、冲突状态联动触发器 | 整套 fact-extraction 管线 + auto-merge 决策；user_id 维度而不仅是 workspace |
| **Letta（前 MemGPT）** | Stateful agent；Core Block（persona/human/recall/archival）；agent 自己用 tool 改记忆；context window 自动压缩到 archival | 没有 agent 实例表，没有 core block，没有上下文管理 | Agent state schema + self-editing tool API + 上下文溢出策略 |
| **Karpathy 的 LLM Wiki** | LLM 自动 curate 个人 wiki，自动反向链接，cross-link | 方向最像，已有 `wiki_page` 表 | 自动 distill + backlink graph + Obsidian 风格 `[[wiki link]]`；当前 wiki 仍是手动 export |
| **Garry Tan 的 GBrain** | 多源 ingest（Slack/邮件/Twitter/Notion）→ 自动整理 → 自然语言提问 | 只能上传 Markdown | 连接器（connectors）+ 自然语言 QA 接口 |
| **EverOS 类** | 跨 app 共享 memory layer，event-sourced | audit_log 接近 event log 但不是 source of truth | 跨应用集成 + 真正的 event sourcing |

### 3.1 MemoryBase 可以防守的独特方向

MemoryBase 不应该直接复刻 Mem0 或 Letta。它更适合走一条 **provenance-first memory ledger** 路线：

- Mem0 偏"好用的自动记忆服务"
- Letta 偏"完整 stateful agent runtime"
- GBrain / LLM Wiki 偏"自动维护 Markdown brain"
- MemoryBase 可以偏"每条记忆都有证据、版本、权限、审计和 Wiki 投影"

这个定位更符合当前 schema 优势，也更容易在课程答辩中讲清楚。未来如果接入 LLM，也应该把 LLM 当成 extractor / compiler，而不是替代数据库治理链。

## 4. 按 ROI 排序的关键改进

### 优先级 0：CLI / uv tool / context formatter

如果目标是让 Codex、Claude Code、Cursor 或其他 agent 尽快真实使用，最短路径不是先上 pgvector，也不是 MCP-first，而是先做一个可安装、可脚本化、可审查的命令行工具：

```bash
uv tool install memorybase
memorybase recall "为什么放弃校园食堂系统" --workspace demo --format context
memorybase remember --type decision --evidence chunk-id "..."
memorybase export-context "当前任务是什么" --max-tokens 3000
```

最低限度提供：

- `memorybase recall`：调用 `/api/recall`
- `memorybase context`：把 recall JSON 转成 agent-ready Markdown
- `memorybase remember`：写入 MemoryItem，可选 evidence
- `memorybase update`：带 revision reason 修改记忆
- `memorybase forget`：走 ForgetRequest 或 soft delete

**影响**：项目立刻从"课程作品"变成"任何 shell-capable agent 可消费的服务"，而且比 MCP 更容易调试和纳入 CI。

### 优先级 1：pgvector + embedding + hybrid recall
- 给 `memory_item` / `source_chunk` 加 `embedding vector(1536)` 列
- 建 ivfflat 或 hnsw 索引
- `/api/recall` 内部 `BM25 + cosine` 融合排序
- 顺手解决中文 FTS 不分词的硬伤
- **影响**：检索质量从"勉强能用"跃迁到"agent 可信赖"

### 优先级 2："对话 → 记忆"自动管线
- 新增 `POST /api/observe { session_id, role, content }`
- 异步 worker：LLM 抽取 fact → Mem0 风格 4 操作（ADD/UPDATE/DELETE/NOOP）→ 写 `memory_item`
- 配套：`session` / `message` 表真正落数
- **影响**：拉平 Mem0 / Letta 的核心入口

### 优先级 3：可选 adapter 暴露
- MCP server 可以作为 CLI 稳定后的薄包装，而不是核心形态
- OpenAPI tool spec 可以服务 function calling
- SSE / HTTP streaming 只有在 live observe 或长任务导出时才需要
- **影响**：在不绑死单一 agent 协议的前提下，扩大可接入范围

## 5. 二级改进（解锁更高维能力，但 ROI 排在后面）

- **agent 实例表**：把 agent 当一等公民，每个 agent 有 persona / capability / context_pointer
- **core memory blocks**：Letta 风格的固定 slot（用户画像、任务状态），始终在 context 里
- **temporal recall 深化**：在已有 `as_of` 过滤之上，支持事实区间推理、时间点对比和 temporal conflict 检测
- **automatic backlink graph**：Wiki 页面互相引用自动建索引
- **连接器**：Slack / 邮件 / Notion 等多源 ingest
- **冲突自动检测**：在当前 manual conflict + trigger lifecycle 之上，加入规则/LLM judge 自动登记 conflict_record
- **反馈回流**：recall_log 的 click / useful 信号回流到 ranking
- **importance 自动衰减**：基于访问频次和时间的动态 importance

## 6. 建议拆成的后续工作包

这些不一定现在开 issue，但如果要从"课程系统"推进到"agent runtime"，可以按下面顺序拆：

| Work Package | 目标 | 最小验收 |
|---|---|---|
| Agent Usage Guide | 说明 agent 开工前 recall、完工后 write-back、何时 forget/conflict | 文档中有完整 prompt / CLI 使用样例 |
| Context Pack Formatter | 把 recall JSON 转为 token-limited Markdown | 同一查询可输出 `memories/evidence/risks/do-not-assume` |
| CLI / uv tool | 让 shell-capable agent 直接调用 MemoryBase | 至少支持 recall + context + remember |
| Observe API | conversation turn 写入入口 | `POST /api/observe` 能落 message，并生成待整理记录 |
| Extraction Worker | LLM/规则抽取 memory | ADD/UPDATE/NOOP 至少可解释并写 audit |
| Hybrid Recall | 改善中文和改写查询 | demo gold set 上 P@5 高于 FTS-only |
| Memory QA Dashboard | 人审查 agent 写入 | 页面展示 evidence、revision、audit、conflict |
| MCP Adapter | 适配 MCP 客户端 | 复用 CLI/service 逻辑，不另起一套核心协议 |

## 7. 课程项目 vs 真实可用的判断

| 维度 | 当前评价 |
|---|---|
| CS3321 数据库课设 | A+：3NF、复合 FK、视图、触发器、治理体系比工业界很多产品还规范 |
| 投放为 agent memory layer | 差 6–12 个月：缺抽取管线、缺向量检索、缺 runtime 协议 |

最关键的判断：**Mem0 和 Letta 之所以成为创业公司，技术核心是抽取管线 + 向量检索 + runtime 协议这三层，schema 反而是最容易复刻的部分**。MemoryBase 当前赢在 schema，差距全在这三层。

## 8. 后续行动建议

不要急着开 issue。先在 P2 收尾后专门留一个 review session，把本文档过一遍，决定：
1. 是否把 P3 定位为"向 agent runtime 演进"
2. 如果是，CLI / context formatter / observe API / pgvector 四件事拆成最小可演示子集
3. 如果不是（比如团队精力有限），就把本文档作为最终报告的"未来工作"章节素材

短期更务实的判断：

- 如果目标是课程交付，优先补前端、回归测试、演示脚本，不要被 P3 runtime 吸走精力。
- 如果目标是个人后续继续做，优先做 CLI / `uv tool` + context formatter，因为它能最快让真实 agent 开始吃 MemoryBase。
- 如果目标是对标 Mem0/Letta，才进入 observe API、自动抽取、pgvector、core memory block。
