# 模块 IPO 表

| 模块 | Input | Process | Output | 涉及表 / 文件 |
|---|---|---|---|---|
| Source / Ingest | Markdown / txt / meeting text | 校验、checksum、切 chunk、生成 search_text_zh | SourceDocument、SourceChunk | `source_document`、`source_chunk` |
| Memory / Evidence | chunk、人工表单、Agent 写回 | 创建 memory、绑定 evidence、必要时创建 inline_agent_note | MemoryItem、MemoryEvidence | `memory_item`、`memory_evidence` |
| Memory Extraction | workspace_id、chunk_ids、max_candidates | rule-based 句子抽取、分类、创建 candidate、记录 run audit | Candidate Memory | `memory_item(status='candidate')`、`memory_evidence`、`audit_log` |
| Revision / Audit | memory / wiki / governance 修改 | 触发器或 service 写 revision 与 before/after JSON | MemoryRevision、AuditLog | `memory_revision`、`wiki_page_revision`、`audit_log` |
| Recall | query、filters、agent_id、retrieval_mode | 权限过滤、FTS/trigram、可选 embedding scoring、fallback metadata | RecallResponse、Context Pack | `recall_log`、`memory_item`、`source_chunk`、embedding tables |
| Search | query、scope、agent_id | chunk/memory/source 多路 lexical search、RRF 融合 | Search results | `source_chunk`、`memory_item`、`source_document` |
| Policy / Agent Visibility | principal、resource、scope、effect | allow/deny 策略、per-agent visibility view | AccessPolicy、visible memory list | `access_policy`、`v_agent_visible_memory` |
| Wiki | memory / scene / workspace | 渲染 Markdown frontmatter/body、写版本、可选写文件 | WikiPage、WikiPageRevision、Markdown 文件 | `wiki_page`、`wiki_page_revision`、`data/markdown_wiki/` |
| Timeline | memory、doc、event_time | 排序聚合项目事件 | Timeline entries | `timeline_entry` |
| Conflict Governance | 两条 memory、conflict_type | 创建/更新 conflict，trigger 标记 conflicted 或恢复 active | ConflictRecord、AuditLog | `conflict_record`、`memory_item`、`audit_log` |
| Forget Governance | target、reason、reviewer | 审批、软遗忘、验证、审计 | ForgetRequest、target status、verification report | `forget_request`、`audit_log` |
| Sessions / Observe | session metadata、messages | Agent Runtime 会话与消息落库 | AgentSession、Message | `agent_session`、`message` |
| Semantic Organization | workspace_id、keyword | 查询 entity / scene 聚合 | Entity / Scene response | `entity`、`memory_entity`、`memory_scene`、`memory_scene_cell` |
| Graph Explorer | workspace_id、agent_id、limit | 从 PostgreSQL 构图、可选同步/读取 Neo4j、前端 SVG 布局 | Graph nodes/edges | `graph_service.py`、`frontend/src/pages/graph/` |
| Embedding Cache | memory/chunk text、provider、model | local hashing 或 provider embedding、JSONB 缓存、backfill | MemoryEmbedding、ChunkEmbedding | `memory_embedding`、`source_chunk_embedding` |
| QA | question、workspace_id、agent_id | recall context + optional LLM provider | AnswerResponse | `qa.py`、`llm_service.py`、`recall_log` |
| Stats Dashboard | workspace_id | 汇总 source/memory/wiki/audit/forget/conflict/recall 计数 | StatsOverviewResponse | `stats_service.py`、统计 views |
| Evaluation | dataset adapter、runner config | 加载 memory benchmark case、运行 metrics、生成 report | Evaluation report | `evaluation/` |
