# 本领域研究现状分析

> 用途：可直接纳入最终报告第 2 章“项目背景与研究现状”。本节以数据库课程报告为目标，不把 MemoryBase 写成普通聊天机器人，而是定位为“面向组织与团队的 AI-native 可追溯长期记忆数据库系统”。

## 2.1 研究背景

随着大语言模型和 Agent 应用的发展，长期记忆已经从“把历史聊天塞进 prompt”演变为一个独立系统问题。团队协作、软件研发、课程项目、企业知识库等场景中，信息来源通常分散在 Markdown 文档、会议纪要、聊天记录、Issue、Wiki、数据库条目和自动化工具日志中。人类用户希望快速找到“当时为什么这样决策”，Agent 则需要在执行任务前读取可信上下文、写入新观察、更新旧结论，并在必要时忘记、归档或审计敏感内容。

传统数据库课程中的信息系统通常关注结构化业务数据，例如用户、订单、库存、审批记录等；而 AI 时代的“记忆系统”面对的是半结构化或非结构化文本。单纯文件系统便于人阅读和版本管理，但缺少关系约束、权限过滤和审计；单纯向量库便于语义检索，但难以表达“这条记忆来自哪段原文、何时被谁修改、哪些 Agent 可见、是否已经被遗忘”；单纯聊天产品的记忆功能面向个人体验，通常不暴露完整 schema、触发器、审计链路和可复现查询。

因此，本项目关注的问题不是“如何再做一个聊天助手”，而是：如何把组织长期知识编译成一个可查询、可追溯、可治理、可被人和 Agent 同时使用的数据库系统。

## 2.2 主要技术路线

### 2.2.1 传统 RAG 与向量检索

Retrieval-Augmented Generation（RAG）是当前知识增强 LLM 应用的基础范式。Lewis 等人在 RAG 论文中指出，参数化模型难以精确访问和更新知识，也难以提供决策 provenance，因此引入外部非参数记忆，并用检索结果辅助生成。工程上，LangChain、LlamaIndex 等框架进一步普及了“切分文档 → 建 embedding → 向量召回 → 拼接上下文 → 交给 LLM”的流程。

这一路线的优点是实现快、语义召回强、容易接入已有文档库。但它的数据库建模通常较弱：chunk、向量、metadata 往往被当作检索材料，而不是有完整生命周期的业务对象。实际系统还需要回答“哪条 memory 支撑了这次回答”“source 被删除后是否还能被召回”“谁有权限看 private memory”“一次 recall 为什么 fallback 到 keyword”，这些问题很难只靠向量相似度解决。

MemoryBase 保留 RAG 的检索思想，但没有把向量库作为唯一核心。系统以 PostgreSQL 关系模型为主，使用 `source_document`、`source_chunk`、`memory_item`、`memory_evidence`、`recall_log` 等表保存来源、证据、召回结果和可观测信息；embedding cache 和 hybrid recall 被设计为可选增强，并提供 keyword fallback，保证没有外部模型或向量服务时仍能完成核心演示。

在向量存储实现上，本项目也刻意没有把 `pgvector` 作为默认依赖。当前 schema 使用 `memory_embedding` 和 `source_chunk_embedding` 两张表，以 JSONB 存储 `embedding_json`，再由服务层做 cosine similarity。这一选择牺牲了大规模 ANN 检索性能，但换来部署简单、课程演示稳定、无需额外数据库扩展、fallback 行为可观测。若后续扩展到更大数据量，`pgvector` / IVFFlat / HNSW 仍然是自然演进方向。

### 2.2.2 Agent 长期记忆系统

近年来出现了多种面向 Agent 的长期记忆系统。MemGPT / Letta 把 LLM 上下文窗口类比为操作系统中的层级内存，用 core memory、archival memory 和工具调用来管理跨会话状态。Mem0 则强调生产环境中的长期记忆层，通过动态抽取、合并、检索对话中的显著信息，并进一步探索 graph memory 表达关系。MemoryBank、LongMem、Generative Agents 等研究也从不同角度证明了“观察、反思、长期存储、动态召回”对 Agent 行为一致性的重要性。

这些工作共同说明：长期记忆不是可有可无的 prompt 技巧，而是 Agent 系统的核心基础设施。它们的优势在于 agent-friendly，能自动抽取、压缩和召回信息，面向连续对话或长期交互有明显价值。但从数据库课程和组织治理角度看，它们通常更关注“如何让模型记得并用上”，较少把关系完整性、证据表、版本表、审计表、权限策略、遗忘审批和 SQL 可验证性作为一等公民。

MemoryBase 的设计选择是把 Agent 记忆问题落到关系数据库上。系统允许 Agent 通过 CLI/API 做 recall、search、observe、remember，但每次写入都落入可约束的表结构；每条 memory 可以追溯到 source chunk；修改会触发 revision 和 audit；Agent 可见范围通过 `v_agent_visible_memory` 和 policy 约束，而不是只依赖 prompt 自觉。

### 2.2.3 产品化记忆：ChatGPT Memory、Confluence AI、Notion AI 与个人知识库

ChatGPT Memory 代表了面向终端用户的产品化记忆能力。官方帮助文档区分 saved memories 与 reference chat history，用户可以查看、删除、关闭或管理记忆；启用后，系统会在后续对话中参考这些信息以提供更个性化的回答。这类功能降低了普通用户使用长期记忆的门槛，但它本质上是黑盒产品能力：用户通常不能直接看到底层 schema、完整日志、检索 SQL、触发器或多租户权限策略。

Confluence AI / Atlassian Rovo 是企业 wiki 和团队协作场景中更直接的对照对象。Atlassian 把 Rovo 定位为连接 Confluence、Jira、Slack 和企业应用的 AI 方案，包含 search、chat、agents、studio 等能力；Rovo agents 也可以在 Confluence / Jira 编辑与自动化流程中协作，帮助生成、整理或修改团队内容。这说明企业知识管理正在从“静态文档库”走向“带 Agent 的工作流知识系统”。但从本课程项目角度看，Rovo 的核心价值在 Atlassian 生态集成与协作体验，而不是开放一个可由学生展示的关系 schema、触发器、SQL EXPLAIN、审计表和可复现实验数据库。

Notion AI Enterprise Search、Obsidian、Logseq 等工具则代表知识管理路线。Notion AI 可以在 workspace、连接器和 web 中搜索，并给出来源引用；Obsidian 以本地 Markdown、内部链接、反向链接和文件系统可控性为核心，适合构建个人或团队知识库。这一路线在人类可读性、文档组织和手工维护方面很强，但对 Agent 来说，文件链接和全文搜索仍不足以表达严谨的数据生命周期：记忆是否 active、archived、forgotten、candidate？一次编辑是否留下不可变 revision？一个 forget request 是否被审批？这些治理问题通常不在普通笔记软件的核心模型里。

MemoryBase 吸收文件型知识库的优点：source 保留原文，wiki 可导出 Markdown，CLI 支持 grep-style 查询；同时用数据库补齐关系、状态、约束、审计和权限。也就是说，文件系统负责人类可读与可迁移，数据库负责治理与可验证。

### 2.2.4 长期记忆评测基准

长期记忆系统需要评测，而不仅是演示。LoCoMo 提供多 session、长对话、事件图和问答/总结任务，用于评估模型对长期对话的理解；LongMemEval 关注聊天助手在信息抽取、多 session 推理、时间推理、知识更新和拒答等能力上的表现；MemoryAgentBench 进一步把 memory agent 的能力拆成 accurate retrieval、test-time learning、long-range understanding 和 selective forgetting。

这些 benchmark 的共同趋势是：从静态长上下文问答转向动态、多轮、可更新、可遗忘的长期记忆能力。它们也暴露出一个现实问题：单纯长上下文或普通 RAG 在时间关系、冲突更新、选择性遗忘、跨 session 证据整合上仍有不足。

MemoryBase 在代码中已经接入 evaluation framework，包含 LoCoMo、LongMemEval、MemoryAgentBench 等 adapter，以及 retrieval、QA、forgetting、system 等指标。对本课程项目而言，评测不是主线替代品，而是证明数据库设计能服务长期记忆任务的扩展证据。

如果在 LoCoMo / LongMemEval 等原始 recall accuracy 上，MemoryBase 不一定超过 Mem0、Letta 这类专门优化长期记忆效果的产品，这并不构成本项目失败。MemoryBase 的评价重点是数据库系统能力：provenance、governance、multi-tenant visibility、audit trail、SQL-verifiable lifecycle 和可降级检索。评测结果应被解释为“长期记忆任务上的验证信号”，而不是唯一产品目标。

### 2.2.5 GraphRAG 与知识图谱记忆

GraphRAG 代表了另一条重要路线：在普通 RAG 的 chunk / vector 之外，先从私有语料中抽取实体、关系和社区结构，再结合局部图搜索与全局摘要回答问题。Microsoft GraphRAG 的核心动机是让系统能回答跨文档、跨主题的 global sensemaking 问题，而不只是做 top-k chunk 拼接。Mem0 等长期记忆系统也在探索 graph memory，用图结构表达人物、事件、偏好和事实之间的关系。

MemoryBase 已经实现 Graph Explorer、PostgreSQL workspace graph preview 和可选 Neo4j sync，但项目定位与 GraphRAG 有意区分：图不是默认检索主路径，也不是替代 PostgreSQL 的事实源。当前图层主要服务 provenance 与 governance 可视化：展示 source、chunk、memory、evidence、wiki、conflict、forget request 等对象之间的关系；Neo4j 只是可选关系索引和展示后端，PostgreSQL 仍是权威数据源。这样既吸收图结构的可解释性，也避免把课程主线变成复杂知识图谱构建项目。

## 2.3 研究现状对比

| 路线 / 代表 | 主要能力 | 优点 | 局限 | 对 MemoryBase 的启发 |
|---|---|---|---|---|
| 传统 RAG / LangChain / LlamaIndex | 文档切分、向量索引、语义召回、上下文拼接 | 上手快，适合知识问答，生态成熟 | chunk 关系弱，生命周期和审计弱，权限与遗忘通常需额外实现 | 保留检索能力，但把 source、memory、evidence、recall 关系化 |
| MemGPT / Letta | core memory、archival memory、stateful agent、工具管理上下文 | 面向 Agent，能跨会话管理上下文 | 更像 Agent runtime，数据库层 provenance 和治理不是主目标 | Agent 可用 API/CLI，但记忆写入必须落入可审计关系模型 |
| Mem0 / graph memory | 动态抽取、合并、检索长期记忆，探索图结构记忆 | 生产化记忆层，强调低延迟和 token 成本 | 更重 memory 效果，较少强调课程数据库层面的约束、触发器和审计 | graph / hybrid retrieval 可作为增强，核心仍是可验证 DB schema |
| ChatGPT Memory | saved memories、reference chat history、用户管理记忆 | 普通用户体验好，自动化程度高 | 产品目标是消费者体验，没有公开 schema / SQL / 数据库治理接口 | 说明用户确实需要长期记忆，但 MemoryBase 要做可解释、可治理版本 |
| Confluence AI / Rovo / Notion AI / Obsidian | enterprise search、workspace AI、Markdown 知识库、链接和引用 | 人类可读，适合组织文档和知识管理 | 对课程要求的关系 schema、触发器、EXPLAIN、遗忘审批链路展示不足 | 保留 Markdown/Wiki 友好性，同时加入关系数据库治理 |
| LoCoMo / LongMemEval / MemoryAgentBench | 长期记忆能力评测 | 让系统效果可量化 | benchmark 不等同产品，且不能替代数据库设计 | evaluation 作为验证层，主线仍是数据库建模与治理 |
| GraphRAG / graph memory | 实体关系图、社区摘要、局部/全局图检索 | 适合跨文档关系理解和复杂语料组织 | 图构建成本高，若作为主路径会偏离课程数据库主线 | Graph Explorer / Neo4j 作为 provenance 可视化增强，PostgreSQL 仍是事实源 |

## 2.4 现有方案的共同不足

综合以上路线，可以看到当前长期记忆系统存在四类空缺：

1. **可追溯性不足**：许多系统能“记住并召回”，但不能稳定说明记忆来自哪个 source、哪个 chunk、哪次编辑、哪次审批。
2. **关系建模不足**：向量库擅长相似度，但对 memory、source、evidence、revision、audit、policy、wiki projection 之间的关系表达不够自然。
3. **治理能力不足**：组织场景需要权限、冲突、遗忘、归档、审计和多角色访问。个人记忆产品通常无法直接满足这一层要求。
4. **课程可验证性不足**：很多 AI memory 系统是黑盒或框架调用，难以展示数据库课程要求的 E-R 图、关系模式、范式分析、索引、视图、触发器、SQL 查询和 EXPLAIN。

这也是 MemoryBase 的切入点：不是追求最强 LLM 自动抽取，也不是替代 Notion 或向量数据库，而是把长期记忆作为一个数据库应用系统来建模。

## 2.5 本项目定位

MemoryBase 的核心 thesis 是：组织级长期记忆需要同时服务人和 Agent。人需要可读 Wiki、来源引用、审计记录和演示界面；Agent 需要可查询 API、context pack、权限可见视图和可持续写入的记忆层；数据库课程则要求结构化设计、完整约束和可执行 SQL 证据。

因此，本项目选择“文件—数据库双态”架构：

- 文件侧：保存 Markdown / txt source，导出 Markdown Wiki，保持人类可读、可迁移、可 grep。
- 数据库侧：用关系模型管理 source、chunk、memory、evidence、revision、audit、policy、conflict、forget request、recall log。
- AI 侧：提供 recall/search/context-pack/CLI/Agent runtime/evaluation，让 Agent 可以使用数据库记忆，但不把 LLM 作为 P0 依赖。

与现有方案相比，MemoryBase 的差异化不在于“又做一个向量检索”或“又做一个聊天记忆”，而在于把 provenance、governance、multi-tenant visibility 和 SQL-verifiable lifecycle 放在系统中心。这一点也更符合数据库课程大作业的评价重点：概念结构、逻辑结构、物理结构、索引、视图、触发器、完整性约束和可复现查询都能在项目中找到对应实现。

## 参考资料

- Lewis et al., [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401), 2020.
- Park et al., [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442), 2023.
- Zhong et al., [MemoryBank: Enhancing Large Language Models with Long-Term Memory](https://arxiv.org/abs/2305.10250), 2023.
- Packer et al., [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), 2023.
- Maharana et al., [Evaluating Very Long-Term Conversational Memory of LLM Agents / LoCoMo](https://arxiv.org/abs/2402.17753), 2024.
- Wu et al., [LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory](https://arxiv.org/abs/2410.10813), 2024.
- Chhikara et al., [Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory](https://arxiv.org/abs/2504.19413), 2025.
- Hu et al., [Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions / MemoryAgentBench](https://arxiv.org/abs/2507.05257), 2025.
- OpenAI Help Center, [Memory FAQ](https://help.openai.com/en/articles/8590148-memory-in-chatgpt).
- Letta Docs, [Agent memory and architecture](https://docs.letta.com/guides/agents/architectures/memgpt), accessed 2026-06.
- LangChain Docs, [Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval).
- LlamaIndex Docs, [Vector Stores](https://docs.llamaindex.ai/en/v0.10.23/module_guides/storing/vector_stores/).
- Atlassian Support, [What is Rovo?](https://support.atlassian.com/rovo/docs/what-is-rovo/).
- Atlassian Support, [Rovo Agents](https://support.atlassian.com/rovo/docs/agents/).
- Atlassian, [Rovo in Confluence: AI features](https://www.atlassian.com/software/confluence/ai).
- Edge et al., [From Local to Global: A Graph RAG Approach to Query-Focused Summarization](https://arxiv.org/abs/2404.16130), 2024.
- Microsoft, [GraphRAG GitHub repository](https://github.com/microsoft/graphrag).
- Notion Help Center, [Enterprise Search](https://www.notion.com/en-gb/help/enterprise-search).
- Obsidian Help, [About Obsidian](https://obsidian.md/help/obsidian).
