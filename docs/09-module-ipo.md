# 模块 IPO 表

| 模块 | Input | Process | Output | 涉及表 |
|---|---|---|---|---|
| Source / Ingest | Markdown / txt | 校验、checksum、切 chunk | SourceDocument、SourceChunk | source_document、source_chunk |
| Memory / Evidence | chunk、人工表单 | 创建 memory，绑定 evidence | MemoryItem、MemoryEvidence | memory_item、memory_evidence |
| Revision / Audit | memory 修改 | 触发器生成版本和审计 | MemoryRevision、AuditLog | memory_revision、audit_log |
| Recall | query、filters、agent_id | FTS、join evidence、权限过滤 | Context Pack | recall_log、memory_item、source_chunk |
| Policy | principal、resource、scope | 创建 allow / deny 策略 | AccessPolicy | access_policy |
| Wiki | memory / scene | 渲染 Markdown 和 frontmatter | WikiPage、WikiPageRevision | wiki_page、wiki_page_revision |
| Timeline | memory、doc、event_time | 排序聚合项目事件 | 时间线 | timeline_entry |
| Conflict | 两条 memory | 标记冲突、处理状态 | ConflictRecord | conflict_record |
