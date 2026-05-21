# MemoryBase 项目总览

## 1. 项目名称

MemoryBase：面向 AI Agent 协作研发的文件—数据库双态长期记忆系统。

## 2. 一句话介绍

把人类可读的 Markdown、会议纪要和项目文档，编译为 Agent 可检索、可追溯、可权限控制、可审计、可版本化的长期记忆数据库。

## 3. 项目定位

本项目是一个数据库应用系统，不是普通聊天助手，也不是从零实现 DBMS。

系统以 PostgreSQL 为核心，通过 SourceDocument、SourceChunk、MemoryItem、MemoryEvidence、MemoryRevision、AuditLog、AccessPolicy、WikiPage 等表管理项目长期记忆。

## 4. 核心链路

```text
SourceDocument
  → SourceChunk
  → MemoryItem
  → MemoryEvidence
  → MemoryRevision / AuditLog
  → RecallLog / AccessPolicy
  → WikiPage / WikiPageRevision
```

## 5. 五层模型

| 层次 | 主要对象 | 作用 |
|---|---|---|
| 源文档层 | SourceDocument、SourceChunk、Session、Message | 保存原始输入 |
| 记忆层 | MemoryItem、MemoryRevision、MemoryScene | 保存长期记忆与版本 |
| 证据层 | MemoryEvidence、Entity / MemoryEntity | 绑定记忆与来源、补充轻量语义组织 |
| 表达层 | WikiPage、WikiPageRevision、TimelineEntry | 生成可读 Wiki 与时间线 |
| 治理层 | AccessPolicy、RecallLog、ConflictRecord、ForgetRequest、AuditLog | 权限、审计、冲突、遗忘 |

## 6. P0 MVP

P0 不依赖 LLM，也不依赖向量数据库。保底功能包括：

- 导入 Markdown / txt source
- 自动切分 source chunk
- 手动或规则创建 memory item
- 绑定 memory evidence
- 关键词 / 全文检索
- 版本记录
- 审计日志
- Markdown Wiki 导出
- 基础前端页面

## 7. P1 功能

- Timeline 决策时间线
- Agent 可见视图
- AccessPolicy 权限过滤
- ConflictRecord 冲突治理
- Memory statistics 统计视图

## 8. P2 / Future

- ForgetRequest 轻量治理流程（已实现：提交、审批、审计、memory forgotten）
- Entity / MemoryScene 轻量语义组织（已实现：实体、场景与 M:N 关系）
- pgvector 语义检索
- LLM 自动抽取
- 复杂 temporal knowledge graph
- 多 Agent 自动协作
- Obsidian 插件
- Git 双向同步
- SkillMemory 自动归纳

## 9. 演示闭环

1. 导入 6 份小组讨论记录。
2. 系统生成 SourceDocument 和 SourceChunk。
3. 从 chunk 创建 20 条 MemoryItem。
4. 每条 MemoryItem 绑定 MemoryEvidence。
5. 搜索“为什么放弃校园食堂系统”。
6. 返回相关 memory，并展示来源 chunk。
7. 修改一条 memory。
8. 自动生成 MemoryRevision 和 AuditLog。
9. 导出 Markdown Wiki 页面。
