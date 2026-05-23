# Course Alignment Risk and Recovery Plan

## 1. Why This Document Exists

本项目已经从最初的数据库课程项目，逐步扩展为面向 AI Agent 的长期记忆系统。这个方向有技术亮点，但也带来一个交付风险：

如果答辩时重点讲成“个人 Agent 记忆工具”或“CLI runtime”，老师可能会觉得它偏离了“数据库管理系统实践”的原始要求。

本文件记录这个风险，并给出后续报告、PPT、演示和开发收尾时应该遵循的调整方案。

## 2. Teacher Requirement Summary

### 2.1 总体要求

根据课程截图，老师的原始要求可以拆成以下几个评分关注点：

| Requirement | Meaning For This Project |
|---|---|
| 设计一个数据库管理系统（例：外卖、电商、信息查询系统） | 必须体现完整业务对象、关系模型、SQL 查询和应用界面 |
| 加入人工智能分析技术 | AI 是加分项，应为应用增值；本项目把它升级为 design thesis，详见 §3.5 |
| 2-4 人自由结合，分工明确 | 报告和 PPT 要展示每个成员负责的模块和交付物，**每人分开打分** |

### 2.2 Required Deliverables（红色为必选）

老师 PPT 第 17 页明确 7 项交付物，其中 4 项标红为必选项：

| # | Deliverable | 必选 | 当前状态 |
|---:|---|:---:|---|
| 1 | **需求分析文档**（含数据流图、数据字典） | ✅ | docs/01-requirements、docs/02-data-flow、docs/03-data-dictionary 已有；需复核完备性并补图 |
| 2 | 概念设计文档（含 E-R 图） | 选做 | docs/04-er-design 已有文字；**需出正式 ER 图（dbdiagram.io / drawio）** |
| 3 | 逻辑设计文档（E-R→关系模型转换、系统结构图） | 选做 | docs/05-logical-design 已有；需补 ER→关系模型显式转换说明 |
| 4 | 物理设计文档（存储安排、方法选择、存储路径、模块 IPO 表） | 选做 | docs/06-physical-design、docs/09-module-ipo 已有；需复核 IPO 表完整度 |
| 5 | **系统实现演示**（含界面与操作截图） | ✅ | 前端弱，截图清单未生成；详见 §6.1 + §6.4 |
| 6 | **流程图 + 带注释源程序**（高级语言 + SQL 等） | ✅ | SQL 已注释；**流程图缺**；高级语言注释需复核 |
| 7 | **分工说明**（具体到每人任务） | ✅ | **缺成员×模块×提交物矩阵**；详见 §6.6 |

虽然 2/3/4 标为选做，但作为完整数据库系统设计，**全部产出是争取高分的标准做法**，建议全部交付。

## 3. Current Fit

MemoryBase 并不是低匹配项目。它已经具备较强的数据库课程特征：

- 23 张核心业务表，覆盖用户、工作区、Source、Chunk、Memory、Evidence、Revision、Policy、Audit、Wiki、Conflict、ForgetRequest、Session、Message 等对象。
- 8 个视图，覆盖 active memory、source provenance、timeline、wiki source、statistics、agent-visible memory、conflict memory 等查询场景。
- 34 个索引，包含普通索引、复合索引、GIN full-text index、trigram index 和 partial unique index。
- 14 个触发器，覆盖 updated_at、memory revision、audit log、soft delete、conflict lifecycle、wiki revision sync 等行为。
- 后端已有 36 个 API endpoint，支持 source import、memory CRUD、recall、search、wiki export、policy、audit、conflict、forget、session、observe 等模块。
- 测试数量达到 110 个，说明不是只有静态 SQL，而是有可执行验证。

从数据库课程角度看，它比普通 CRUD 网站更能展示：

- 关系建模
- 主键 / 外键 / 复合外键
- CHECK / UNIQUE / partial unique index
- M:N 关系表
- 视图
- 触发器
- 全文检索
- 模糊检索
- 审计日志
- 版本管理
- 权限过滤
- 软删除

## 3.5 Design Thesis: AI 原生时代的数据访问范式

本项目的设计起点不是"做一个有 AI 加分的数据库"，而是回答一个具体的研究问题：

> **强 AI Agent 应该如何访问长期记忆？**

业界目前给出的两个主流答案各有致命缺陷：

| 路径 | 代表 | 优点 | 致命缺点 |
|---|---|---|---|
| **文件 + grep** | Karpathy "LLM Wiki" 思路；Claude Code / Codex 等 AI 工作流 | AI 原生擅长、精确、可解释 | 无结构、无关联、无审计、无版本 |
| **向量数据库 + RAG** | Mem0、Letta、ChatGPT Memory | 模糊召回、覆盖语义近似 | 黑盒 top-k、不可追溯、随机性高、调试困难 |
| **关系数据库 + AI-grep（本项目）** | MemoryBase | 精确查询 + 强关联 + 可追溯 + FTS/trigram 近似召回 | 设计成本高 |

**本项目核心论点**：用关系数据库**补足文件系统在结构、关联、审计、版本上的缺失，同时保留文件系统 grep-可寻址、人可读、可解释的优点**。23 张表的 schema、5 层 provenance 模型、FTS + trigram 索引、`mb search/recall/context` CLI —— 全部服务于让 LLM Agent 像在文件系统里 grep 一样精准访问结构化记忆。

换句话说，MemoryBase 不是把数据库做成一个黑盒向量库，而是把数据库做成 **AI 可 grep 的结构化文件系统底座**：

- 文件系统的优点：人类可读、路径稳定、行号可引用、grep 精确、AI coding agent 已经非常擅长使用。
- 文件系统的缺点：缺少强关系、约束、权限、版本、审计、冲突治理和跨文件聚合。
- 向量库的优点：能召回语义相近内容。
- 向量库的缺点：top-k 难解释、命中不稳定、调试困难、证据链容易断。
- MemoryBase 的选择：以文件 / grep-style 访问为主路，用关系数据库补齐治理能力；向量检索可以作为 future enhancement，而不是系统成立的前提。

这是"加入人工智能分析技术"在数据库课程语境下的最深层实现方式：**不是把 AI 拼装进数据库系统，而是为 AI 原生工作方式重新设计数据库访问层**。

### 3.5.1 设计选择如何由 thesis 推导

| 设计 | 服务于 thesis 的哪一面 |
|---|---|
| 5 层 schema（Source → Chunk → Memory → Evidence → Revision/Audit） | 让每条 AI 写入都可被结构化 grep 到原文行号，杜绝"记忆悬空" |
| 触发器自动写 `memory_revision` + `audit_log` | 让 AI 写入历史可追溯，区别于 ChatGPT Memory 的黑盒覆写 |
| GIN tsvector + jieba 中文分词 | 让 AI 用关键词精确命中（grep 的精确性） |
| pg_trgm 模糊索引 | 补足 AI 容错（拼错、近义）能力 |
| `v_agent_visible_memory` 视图 | 用 SQL 实现"AI 可见性"边界，权限即查询条件 |
| ForgetRequest 软治理 | 让 AI 写入可撤回但保留审计（区别于 hard delete） |
| `mb context` 同时融合 memory / session / repo / search | 让 AI 在一次 SQL 调用里拿到"完整工作上下文" |

这些设计共同形成"**AI 原生数据访问基座**"。这正是我们对"数据库 + AI 分析技术"的回答。

### 3.5.2 为什么不把向量检索作为主线

报告和答辩里可以坦诚说明：本项目没有把 pgvector / embedding 作为当前主线，不是因为不知道这条路线，而是基于应用场景做出的取舍。

| Dimension | Grep / File-Style Access | Pure Vector Recall |
|---|---|---|
| 可解释性 | 能指向具体文件、chunk、行号和 evidence | 只能给相似结果，解释依赖额外模型 |
| 可调试性 | 查询词、SQL、索引、结果都可检查 | embedding 空间难以人工检查 |
| 稳定性 | 同一 query 在同一数据上结果稳定 | top-k 对模型、参数、数据扰动敏感 |
| AI coding agent 适配 | Codex / Claude Code 天然擅长 grep、读文件、引用行号 | 需要额外工具协议和召回解释层 |
| 数据库课程价值 | 能展示关系建模、索引、视图、触发器、审计 | 容易退化成"接一个向量库 API" |

因此，本项目当前的 AI 路线是：

```text
human-readable files
  + SQL schema / constraints / evidence / audit
  + FTS / trigram / jieba
  + agent-friendly CLI context
  = grep-style structured memory for AI
```

未来可以在此基础上接入 embedding，但它应服务于"找不到时的补充召回"，而不是替代 provenance-first 主线。

## 4. Real Risk

### 4.1 Topic Framing Risk

如果项目被描述为：

> 面向个人 AI Agent 的记忆数据库 / Agent CLI 工具

风险较高。因为老师可能会认为：

- 它不像传统数据库管理系统。
- 用户需求不够生活化。
- AI Agent runtime 与数据库课程目标关系不直接。
- CLI 工具不如网站系统直观。

推荐统一改成：

> MemoryBase：面向软件研发小组的项目知识、决策、证据与审计管理系统。

Agent 是高级使用者，不是系统唯一用户。

### 4.2 UI Demonstration Risk

当前前端仍然偏弱。如果最终演示只展示 API、CLI 或数据库命令，会显得不像“数据库管理系统应用”。

课程交付必须补齐可截图、可点击、可解释的演示界面。

### 4.3 AI Interpretation Risk

老师提到“可适当加入人工智能分析技术”，但这通常是加分项，不是必须做完整 Agent runtime。

当前系统已经有 agent-friendly CLI、context pack、中文分词、recall/search、evidence provenance，但这些如果不包装好，老师可能看不出“AI 分析”在哪里。

需要把它表达为：

- AI 辅助项目知识检索
- AI 上下文包生成
- 记忆证据追溯
- 冲突与风险提示
- 可审计的 Agent 写回

而不是主讲“Agent runtime 架构”。

### 4.4 Workload Perception Risk

虽然数据库和后端工作量很大，但如果 PPT 只展示几个表和一个简单页面，老师会低估实际工作量。

必须显式展示：

- schema 总体图
- E-R 图
- 关键表关系
- 视图清单
- 触发器清单
- SQL demo 查询
- API 模块图
- 测试结果
- GitHub issue / PR 分工
- 每位成员完成内容

## 4.5 Database Curriculum Coverage Gap

下表列出**数据库课程经典考点中本项目尚未覆盖的项**。这些不影响项目能跑，但影响"数据库课程"维度的评分上限。**本节作为差距记录，不要求立刻动手补 —— 详见 §6 Recovery Plan 中的优先级排序**。

| 经典考点 | 当前状态 | 差距 |
|---|---|---|
| 范式分析（3NF/BCNF） | 没正式写过 | 23 张表的函数依赖、范式判断、为什么这样拆 — 没有书面分析 |
| EXPLAIN ANALYZE 执行计划 | 几乎没做 | 没有"这条查询走了哪个索引、cost 多少、改 index 后变成什么"的实证 |
| 索引选型论证 | 索引建了但没讲为什么 | GIN / GIST / BRIN / B-tree 的对比、pg_trgm vs tsvector 各自适用场景 — 没写 |
| 存储过程 / 函数 | 0 个 PL/pgSQL function | 触发器有，主动函数没有 |
| 事务隔离级别 | 默认 READ COMMITTED 用着 | 没演示过 SERIALIZABLE 下两个 agent 抢同一 session 会发生什么 |
| 并发与锁 | 没碰 | pg_locks / pg_stat_activity 一次没截过图 |
| 窗口函数 / 递归 CTE | 视图里没用 | Timeline / scene 关系明明是天然的 WITH RECURSIVE 场景 |
| 分区表 | 没分 | audit_log 和 message 都是 append-only 时序数据，是分区教科书例子 |
| 物化视图 + 刷新策略 | 普通视图 | dashboard 统计完全可以做成 MATERIALIZED VIEW + cron refresh |
| 性能基准 | 没数据 | 100 / 1k / 10k memory 时 recall 延迟是多少？没测过 |
| 备份 / 恢复 | 没演示 | pg_dump / PITR 没在 demo 里出现过 |

按 ROI 优先级建议：

- **P0 必补**（纯文档，不动代码，约 2 天）：范式分析文档、EXPLAIN ANALYZE 执行计划报告、索引选型说明
- **P1 强烈建议**（约 1.5 天）：1 个 PL/pgSQL 存储过程、1 个递归 CTE 视图、audit_log RANGE 分区
- **P2 可选**（每项 0.5–1 天）：物化视图、并发与隔离级别演示、性能基准、备份恢复演示

具体的实施时机和归属人在 §6 Recovery Plan + §9 Development Checklist 里安排。

## 5. Recommended Positioning

### 5.1 External Project Name

保留 MemoryBase 名称，但报告标题建议改成既贴合数据库课程、又承载 §3.5 thesis 的表达：

> **MemoryBase：AI 原生的可追溯团队知识库 —— 为 LLM Agent grep-style 访问设计的关系数据库系统**

可选副标题：

> 一个支持证据追溯、版本审计、权限治理和 AI 原生数据访问的数据库应用系统

为什么这样改：
- 保留"团队知识库"让老师能秒懂"应用需求"是什么
- "AI 原生" + "grep-style 访问" 直接把 §3.5 thesis 写进标题，避免被误判为"AI 工具包装"
- "关系数据库系统"明确课程主体

### 5.2 User Scenarios

答辩时优先讲这些普通用户场景：

1. 小组成员导入会议纪要和讨论记录。
2. 系统切分 source chunk 并保存行号。
3. 成员把关键结论整理成 memory。
4. 每条 memory 绑定 evidence，可追溯来源。
5. 查询“为什么放弃校园食堂系统”。
6. 系统返回相关 memory、source chunk 和证据。
7. 修改 memory 后自动产生 revision 和 audit log。
8. 权限策略控制不同 Agent / 成员能看到哪些 memory。
9. 冲突记录展示不同决策或观点之间的矛盾。
10. 导出 Wiki 页面和时间线，形成报告素材。

Agent CLI 只作为高级入口补充展示，不作为主线。

## 6. Recovery Plan

### P0: Must Do Before Final Submission

这些是课程交付风险最高的补救项。

#### 6.1 Build A Course-Friendly Frontend Demo

完整列出可演示页面共 6 个，但 3-4 人 1-2 周时间内**优先实现下面 2 个核心页**，其余降级为 SQL + CLI 截图：

| Page | 优先级 | Required Demo Content |
|---|:---:|---|
| **Dashboard** | P0 | 表数量、memory 数、source 数、audit 数、conflict 数、wiki 数；底部条幅 "23 tables / 8 views / 34 indexes / 14 triggers" |
| **Memory Inspector** | P0 | 点一条 memory 一屏内展示：source 文档与行号 → evidence chunks → revision timeline → audit trail → 关联 conflict → recall_log 出现历史。这一页本身就是 provenance-first 的可视化证明 |
| Source List / Detail | P1 | 文档标题、路径、checksum、chunk 列表、行号 |
| Recall / Search | P1 | 查询框、结果列表、证据、得分 |
| Audit / Conflict | P2 | 审计记录、before/after、冲突状态 |
| Wiki / Timeline | P2 | Wiki 页面预览、时间线事件 |

设计原则：**前端不求多求全，但必须能截图证明"数据库查询结果可视化"**。1 个 Memory Inspector 比 6 个零散 CRUD 页对评分更有冲击力。

#### 6.2 Strengthen SQL Demo Queries

`database/08_demo_queries.sql` 应该覆盖：

- 多表 JOIN：memory + evidence + source chunk + document
- 视图查询：`v_agent_visible_memory`、`v_conflict_memory`、`v_wiki_page_sources`
- 触发器效果：修改 memory 后 revision/audit 自动生成
- 权限过滤：不同 agent 的可见 memory 不同
- 全文 / 模糊检索：中文分词与 trigram 查询
- 审计生命周期：memory 从创建、修改、冲突、遗忘的链路
- 聚合统计：memory 类型分布、recall 次数、conflict 状态统计

这些 SQL 是数据库课程评分的直接证据。

#### 6.3 Rewrite Report Narrative

最终报告要从数据库系统角度组织，不要从 Agent runtime 角度组织。

推荐结构：

1. 应用背景：研发小组知识、会议纪要、决策和证据难管理。
2. **研究现状对比**：Mem0 / Letta / ChatGPT Memory / 传统 RAG / Karpathy LLM Wiki 各自取舍（详见 §6.3.5）
3. **设计 thesis**：AI 原生数据访问范式 —— 三方对比 + 我们的回答（§3.5）
4. 需求分析：source 管理、memory 管理、evidence 追溯、revision、audit、policy、wiki。
5. 概念结构设计：SourceDocument、SourceChunk、MemoryItem、MemoryEvidence、Revision、Audit、Wiki。
6. 逻辑结构设计：主外键、M:N、3NF、约束。
7. 物理结构设计：索引、视图、触发器、全文检索。
8. 系统实现：前端页面、后端 API、数据库 SQL。
9. AI 原生访问能力：CLI grep-style 查询、context pack、agent 可见视图。
10. 演示与测试：截图、SQL 查询、测试结果。

#### 6.3.5 Research Landscape Section（必写，对应交付物 #1 的"研究现状"部分）

报告 §2 "项目背景与研究现状" 必须包含 1-2 页对比分析，至少覆盖：

- **Mem0（2024）**：embedding 抽取 + LLM 自动生成 memory；agent-friendly 但不可追溯
- **Letta（前 MemGPT）**：分层 memory（core / archival），stateful agent runtime；强 in-context 管理但弱 provenance
- **ChatGPT Memory**：黑盒 KV 存储；无 schema、无审计
- **Notion AI / Obsidian**：人工组织 + 弱 AI 检索；不为 agent 设计
- **传统 RAG（LangChain / LlamaIndex）**：vector store + chunker；无关系建模
- **Karpathy "LLM Wiki" 思路**：文件 + grep；AI 友好但缺结构与审计

论证锚点：**以上方案没有一个把"可追溯关系建模"作为一等公民**。MemoryBase 的差异化由此而来 —— 详见 §3.5 Design Thesis。

这一节是 assignment 明确要求的"本领域研究现状分析"，**缺失会直接丢分**。

#### 6.4 Prepare Screenshots

最终报告至少准备这些截图：

- 数据库表结构或 ER 图
- Source 导入结果
- Chunk 行号展示
- Memory 详情与 Evidence
- Recall/Search 查询结果
- Revision timeline
- Audit log
- Policy / Agent visible memory
- Conflict page
- Wiki preview
- SQL demo output
- 测试结果或 CI 结果

### P1: Strongly Recommended

#### 6.5 Add Visible AI Analysis Features

为了更贴合“可加入人工智能分析技术”，建议至少展示 2-3 个直观功能：

- 中文分词检索：展示“食堂方向”和“cafeteria system”相关结果。
- 智能上下文包：把 recall 结果生成 agent 可读 Markdown。
- 风险 / 冲突提示：展示 conflict memory 如何提示决策矛盾。
- 记忆写回：展示 Agent 或 CLI 如何写入一条带证据的 memory。

如果时间允许，可以增加轻量规则分析，不必接 LLM：

- 根据 `memory_type='risk'` 自动汇总风险清单。
- 根据 `importance` 和 `recall_log` 生成热点 memory。
- 根据 `conflict_record` 生成“待处理分歧”列表。

#### 6.6 Make Workload Visible

##### 6.6.1 项目维度（PPT 一页 slide）

```text
23 tables
8 views
34 indexes
14 triggers
36 backend API endpoints
110 automated tests
Source -> Chunk -> Memory -> Evidence -> Revision/Audit -> Recall/Policy -> Wiki
```

这不是炫数字，而是防止老师误以为只是一个简单 AI wrapper。

##### 6.6.2 成员维度（对应交付物 #7，必选）

老师 PPT 明确”每位同学是分开打分的”。需要在报告 §19 “小组分工与个人完成情况” 给出**成员 × 模块 × 提交物**矩阵，建议模板如下（人名待填）：

| 成员 | 主负责模块 | 关键提交物（文件路径 + GitHub commit/PR） | 课程考点覆盖 |
|---|---|---|---|
| [姓名 A] | Schema + 索引 + 触发器 | `database/01-04_*.sql`、范式分析文档（待补）、ER 图 | ER 设计 / 范式 / 索引选型 / 触发器 |
| [姓名 B] | API + 后端服务 + 测试 | `backend/app/api/`、`backend/app/services/`、110 测试 | 事务、约束验证、并发、SQL 嵌入应用 |
| [姓名 C] | CLI + AI 集成 + Context Pack | `backend/app/cli/`、`docs/17` agent runtime、`docs/20` grep-thesis | 应用接口、AI 分析、查询语言 |
| [姓名 D] | 前端 + 演示 + 文档 + PPT | `frontend/`、`docs/11` demo 脚本、PPT、截图清单 | 系统演示、流程图、用户界面 |

每人在报告 §19 有独立小节：
- 主负责模块说明
- 关键代码贡献清单（用 `git log --author='...' --oneline` 自动生成）
- 关键 PR/Issue 链接
- 个人完成的课程考点

**注意**：assignment 写的是 “2-4 人”，如果是 3 人组，把上表 4 行合并为 3 行（D 可以并入 A 或 C）。

### P2: Optional Enhancement

如果前端和报告已经完成，再考虑：

- pgvector / embedding hybrid search
- LLM 自动抽取 memory
- 自动生成 Wiki 草稿
- 更完整的 Memory QA dashboard
- 更多统计图表

这些可以作为展望，不应抢占课程交付主线。

## 7. What To Avoid

答辩和报告中避免这样讲：

- "这是一个给个人 Agent 用的 memory CLI。"
- "我们主要做了 agent runtime。"
- "用户通过命令行和数据库交互。"
- "AI Agent 自动维护全部记忆。"
- ❌ "我们加了中文分词 / context pack 作为 AI 加分点。" —— 这是低估自己的设计，把 thesis 讲成 trick
- ❌ "我们以后接入向量数据库才算真正 AI。" —— 这会否定当前设计。向量是可选增强，不是本项目 AI 原生价值的前提

更稳妥的讲法：

- "这是一个 AI 原生的可追溯团队知识库系统。"
- "数据库是系统核心 —— 我们用关系建模回答了'AI Agent 应该如何访问长期记忆'这个问题（§3.5）。"
- "每条记忆都能追溯来源、版本和审计记录。"
- "系统支持小组成员和 Agent 两类用户，演示主线面向普通小组成员；Agent 作为高级使用者证明 thesis 可行性。"
- ✅ "AI 在我们系统里不是加分模块，而是设计目标 —— 我们对比了文件 + grep 和向量库两条路径，给出第三条路：关系数据库 + AI-grep。"
- ✅ "我们保留文件系统 grep 的精确、可解释和 AI 友好优点，再用数据库补齐关系、权限、版本、审计和治理。"

## 8. Suggested PPT Storyline

1. **问题背景**：小组讨论、会议纪要、技术决策散落在 Markdown / chat 中，难检索、难追溯、难审计。
2. **研究现状**：Mem0 / Letta / ChatGPT Memory / 传统 RAG / Karpathy LLM Wiki — 各有取舍但都没解决"可追溯关系建模"问题（对应交付物 #1 的研究现状要求；详见 §6.3.5）
3. **系统目标**：把非结构化项目资料转成可查询、可追溯、可权限控制的数据库记忆系统。
4. **总体架构**：前端、后端、PostgreSQL、文件导入、Wiki 导出。
5. **数据主线**：SourceDocument -> SourceChunk -> MemoryItem -> Evidence -> Revision / Audit -> Recall / Wiki。
6. **E-R 与关系模型**：展示核心实体和 M:N 关系。
7. **数据库亮点**：约束、索引、视图、触发器、全文检索、审计、版本。
8. **AI 原生数据访问范式（核心创新点）**：grep-thesis 一页 slide —— 三方对比表（文件 / 向量库 / 关系库）+ "为什么 grep/file-style 是强 AI Agent 的自然接口" + "我们为什么选第三条路" + 把 schema/触发器/FTS/CLI 全部纳入这个论证 (详见 §3.5)。
9. **系统演示**：导入、检索、证据、修改、审计、冲突、Wiki + Memory Inspector 一屏 provenance 全链路。
10. **测试与分工**：测试结果、成员贡献矩阵（§6.6.2）、GitHub issue / PR。
11. **总结与展望**：后续可接入 LLM 抽取、向量检索、更多连接器（注意：放在展望，不抢主线）。

## 9. Development Checklist

后续按以下顺序推进，分为 4 个优先级。

### 9.1 P0 — 定位与必选交付物（必做，缺一直接丢分）

- [ ] 先冻结课程定位：AI 原生可追溯团队知识库系统（§5.1），而不是个人 Agent 工具
- [ ] 更新 README / docs/00 项目总览 / docs/13 报告标题，对外表述统一到 §5.1
- [ ] 在 docs/13 报告 §2 写满 1-2 页 research landscape（§6.3.5），覆盖 Mem0/Letta/ChatGPT Memory/RAG/Karpathy LLM Wiki
- [ ] 在 docs/13 报告新增章节写 §3.5 design thesis 完整内容
- [ ] 在报告和 PPT 中明确：向量检索是 future enhancement，当前主线是 grep-style structured memory，不要把 AI 价值绑定到 embedding
- [ ] 复核交付物 #1 必选项：docs/01-requirements + docs/02-data-flow + docs/03-data-dictionary 是否完备
- [ ] 补**流程图**（交付物 #6 必选）：至少出"导入 → 切分 → memory 创建 → recall → wiki 导出"的主流程图 1 张
- [ ] 出**正式 ER 图**（交付物 #2，强烈推荐）：用 dbdiagram.io / drawio 生成
- [ ] 实现 Dashboard + Memory Inspector 两个前端页（§6.1），支撑交付物 #5 必选项
- [ ] 生成 12 张演示截图清单（§6.4），归档到 `docs/screenshots/`
- [ ] 产出**成员 × 模块 × 提交物矩阵**（§6.6.2，交付物 #7 必选）
- [ ] 准备重点突出的 PPT（§8 storyline），方便 Canvas 分享

### 9.2 P1 — 数据库课程深度补强（强烈建议，对应 §4.5 gap）

- [ ] 写《Schema 范式分析》文档（3NF/BCNF + 函数依赖 + 拆表理由）—— 纯文档约 1 天
- [ ] 写《索引选型与 EXPLAIN ANALYZE 报告》—— 跑 5 个代表性 query + 截图 + 解读，约 1 天
- [ ] 加 1 个 PL/pgSQL 存储过程（推荐：`create_memory_atomic` 把 memory + revision + audit 三表事务封装）—— 半天
- [ ] 加 1 个递归 CTE 视图（推荐：`v_memory_scene_tree` 展开 memory_scene 父子）—— 半天
- [ ] `audit_log` 改 RANGE 按月分区，schema + demo 演示 `\d+ audit_log` —— 半天
- [ ] 补强 `database/08_demo_queries.sql`（§6.2 已列清单）

### 9.3 P2 — 可选增强（有时间再做）

- [ ] 物化视图 + 刷新策略演示（`v_workspace_stats` 改 MATERIALIZED VIEW）
- [ ] 事务隔离级别 + 并发锁演示（两个 psql session 抢同一 memory，截 `pg_locks`）
- [ ] 性能基准（100 / 1k / 10k memory 时 recall p50/p95 延迟曲线）
- [ ] 备份 / 恢复演示（`pg_dump` + PITR 截图）
- [ ] 轻量规则分析（risk 清单、热点 memory、待处理分歧列表，详见 §6.5）

### 9.4 P3 — 不在课程交付范围（明确写在展望，不要做）

- [ ] pgvector / embedding hybrid search
- [ ] LLM 自动抽取 memory
- [ ] 自动生成 Wiki 草稿
- [ ] MCP adapter
- [ ] 把 Agent CLI / runtime 作为答辩主线（应作为 §3.5 thesis 的能力支撑，不喧宾夺主）

## 10. Bottom Line

MemoryBase 本身不偏题。真正的风险有两条：

> 1. 项目实际做得像数据库系统，但对外讲得像 Agent 工具。
> 2. AI 部分被讲成"加了几个 trick"，而不是讲成"为 AI 时代重新设计数据库访问层"的 thesis。

因此后续工作重点是两件事：

**第一件 —— 把数据库系统价值显性化**：

- 可见的前端（Dashboard + Memory Inspector）
- 可解释的 SQL（demo queries + EXPLAIN ANALYZE）
- 清晰的 ER / 关系模型 / 范式分析
- 可截图的演示流程
- 数据库课程语言下的报告和 PPT

**第二件 —— 把 grep-thesis 当作创新主线讲**（§3.5）：

- 三方对比表（文件 + grep / 向量库 / 关系数据库）
- "我们为什么选第三条路"的论证
- "数据库如何补足文件系统缺失，同时保留 grep/file-style 优点"的论证
- 把 schema、触发器、FTS、CLI 全部纳入这个论证的支撑证据
- 把 Mem0 / Letta / ChatGPT Memory / Karpathy LLM Wiki 都点到（§6.3.5），证明这是真领域问题

只要叙事调整到位 + 必选交付物补齐 + 数据库深度有补强（§4.5 P0/P1），本项目不仅能贴合原始需求，而且能比普通 CRUD 题目更突出**数据库设计深度 + AI 时代创新性**双重价值。
