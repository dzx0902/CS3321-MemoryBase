# 数据流图设计

## 1. 0 层 DFD

外部实体：

- E1 普通用户 / 小组成员
- E2 Agent
- E3 管理员
- E4 Markdown / 会议纪要文件
- E5 Markdown Wiki 文件系统

处理过程：

- P0 MemoryBase 长期记忆数据库系统

数据存储：

- D1 Source Store
- D2 Memory Store
- D3 Governance Store
- D4 Wiki Store
- D5 Audit Store

## 2. 1 层 DFD

```text
Markdown / txt 文件
  → P1 Source Ingest
  → D1 SourceDocument / SourceChunk
  → P2 Memory Extract
  → D2 MemoryItem / MemoryEvidence
  → P2a Semantic Organization
  → D2 Entity / MemoryScene
  → P3 Recall Search
  → Context Pack
  → P4 Wiki Export
  → D4 WikiPage / WikiPageRevision

所有关键操作
  → P5 Governance
  → D5 AuditLog / Revision / RecallLog / AccessPolicy
```

## 3. Source 导入 2 层 DFD

```text
用户上传文件
  → 校验文件类型
  → 计算 checksum
  → 保存 SourceDocument
  → 按行数 / token 切分
  → 保存 SourceChunk
  → 通过 imported_at / imported_by_user_id 保留导入来源

说明：当前实现中 source import 不直接写 `audit_log`；`audit_log` 主要覆盖
memory、wiki、conflict、forget、extraction run 等治理事件。最终报告若要展示
source import 审计，应先补代码或只展示 source 表内的导入元数据。
```

## 4. Recall 检索 2 层 DFD

```text
用户 / Agent 输入 query
  → 解析 query 和过滤条件
  → 应用 AccessPolicy
  → 查询 SourceChunk FTS / trigram
  → 查询 MemoryItem 文本匹配
  → 可选查询 MemoryEmbedding / SourceChunkEmbedding
  → Join MemoryEvidence / SourceChunk / SourceDocument
  → 返回 memory + evidence + source
  → 写入 RecallLog（含 retrieval_info / fallback reason）
```

## 5. Wiki 导出 2 层 DFD

```text
选择 scene / memory / workspace
  → 查询 MemoryItem
  → 查询 MemoryEvidence
  → 查询 SourceChunk
  → 生成 Markdown frontmatter
  → 生成正文和来源列表
  → 写入 WikiPage
  → 写入 WikiPageRevision
  → 导出 data/markdown_wiki/
```

## 6. 语义组织 2 层 DFD

```text
MemoryItem / MemoryEvidence
  → 识别项目对象、概念和决策主题
  → 绑定 Entity
  → 聚合 MemoryScene
  → 支撑 Memory 详情、Wiki 来源追溯和演示查询
```
