# 数据字典

## 1. 核心数据项字典

| 数据项 | 含义 | 类型 | 约束 | 示例 |
|---|---|---|---|---|
| user_id | 用户编号 | UUID | PK | 6f9e... |
| agent_id | Agent 编号 | UUID | PK | a12c... |
| workspace_id | 工作区编号 | UUID | PK | w001 |
| session_id | 会话编号 | UUID | PK | s001 |
| message_id | 消息编号 | UUID | PK | m001 |
| doc_id | 源文档编号 | UUID | PK | doc001 |
| chunk_id | 文档块编号 | UUID | PK | chunk001 |
| memory_id | 记忆项编号 | UUID | PK | mem001 |
| scene_id | 记忆场景编号 | UUID | PK | scene001 |
| entity_id | 实体编号 | UUID | PK | ent001 |
| page_id | Wiki 页面编号 | UUID | PK | page001 |
| recall_id | 召回记录编号 | UUID | PK | recall001 |
| conflict_id | 冲突记录编号 | UUID | PK | conf001 |
| policy_id | 权限策略编号 | UUID | PK | pol001 |
| audit_id | 审计日志编号 | UUID | PK | audit001 |
| access_level | 访问范围 | VARCHAR | public/project/team/private | project |
| memory_type | 记忆类型 | VARCHAR | episodic/semantic/profile/procedural/decision/preference/task/risk | decision |
| status | 数据状态 | VARCHAR | active/archived/forgotten/superseded/conflicted | active |
| confidence | 置信度 | NUMERIC | 0.00–1.00 | 0.85 |
| importance | 重要性 | INT | 1–5 | 4 |
| relation_role | memory 与 entity 的关系角色 | VARCHAR | about/mentions/authored_by/owned_by/related_to | about |
| scene_slug | 场景短标识 | VARCHAR | workspace 内唯一 | topic-decision |
| cell_role | scene 中 memory 的叙事角色 | VARCHAR | background/context/support/decision/outcome | decision |
| forget_status | 遗忘请求状态 | VARCHAR | pending/approved/rejected/done | approved |

## 2. 数据结构字典

| 数据结构 | 组成 | 说明 |
|---|---|---|
| UserAccount | user_id、username、display_name、role_hint、created_at | 人类用户 |
| Agent | agent_id、workspace_id、name、agent_type、status | 可参与检索和写入的 Agent |
| SourceDocument | doc_id、workspace_id、title、raw_text、checksum | 原始文档 |
| SourceChunk | chunk_id、doc_id、chunk_no、chunk_text、line range | 文档切块 |
| MemoryItem | memory_id、workspace_id、memory_type、canonical_text、status | 长期记忆核心 |
| MemoryEvidence | evidence_id、memory_id、chunk_id、evidence_role | 记忆来源证据 |
| MemoryRevision | memory_id、revision_no、revision_text、editor | 记忆版本 |
| Entity | entity_id、workspace_id、canonical_name、entity_type、description | 工作区内的项目对象、概念、文档或事件 |
| MemoryEntity | memory_id、entity_id、workspace_id、relation_role | MemoryItem 与 Entity 的 M:N 关系 |
| MemoryScene | scene_id、workspace_id、scene_slug、title、summary | 面向演示和 Wiki 的主题/决策场景 |
| MemorySceneCell | scene_id、memory_id、workspace_id、cell_role、sort_order、note | MemoryScene 与 MemoryItem 的 M:N 聚合关系 |
| WikiPageRevision | page_id、revision_no、frontmatter_json、body_markdown | Wiki 页面版本 |
| ForgetRequest | request_id、target、requester、reviewer、reason、status、resolved_at | 遗忘/归档审批记录；审批 memory_item 时更新 memory status |
| AuditLog | audit_id、actor、action、target、before/after | 操作审计 |

## 3. 数据流字典

| 数据流 | 来源 | 去向 | 组成 |
|---|---|---|---|
| SourceImportFlow | Markdown 文件 | Source Ingestor | title、doc_type、raw_text、path |
| ChunkFlow | Source Ingestor | SourceChunk | doc_id、chunk_no、text、line range |
| MemoryExtractFlow | SourceChunk / 用户 | MemoryItem | type、text、summary、evidence |
| RecallFlow | 用户 / Agent | Retriever | question、workspace_id、agent_id |
| ContextPackFlow | Retriever | Agent / UI | memory list、evidence、score |
| WikiExportFlow | Wiki Exporter | 文件系统 | frontmatter、body、sources |
| AuditFlow | 各模块 | AuditLog | actor、action、target、before/after |

## 4. 数据存储字典

| 数据存储 | 对应表 | 用途 |
|---|---|---|
| D1 用户与工作区库 | user_account、workspace、workspace_member、agent | 身份、成员、Agent |
| D2 源文档库 | source_document、source_chunk、message、agent_session | 原始数据 |
| D3 记忆库 | memory_item、memory_revision、memory_evidence | 长期记忆 |
| D4 语义结构库 | entity、memory_entity、memory_scene、memory_scene_cell | 实体、记忆实体关系、场景聚合 |
| D5 表达层库 | wiki_page、wiki_page_revision、timeline_entry | Wiki 与时间线 |
| D6 治理库 | access_policy、conflict_record、forget_request、audit_log、recall_log | 权限、冲突、遗忘、审计 |
