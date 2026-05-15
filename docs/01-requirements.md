# 项目需求文档

## 1. 项目背景

AI Agent 和项目团队在长期协作中会产生大量会议纪要、讨论记录、项目文档、决策和变更记录。若这些信息只存在聊天记录或 Markdown 文件中，会出现难检索、难追溯、难更新、难审计、难权限控制的问题。

MemoryBase 通过数据库管理长期记忆，使项目知识可以被结构化查询、版本追踪、来源追溯、权限过滤和 Wiki 投影。

## 2. 用户角色

| 角色 | 使用目标 | 主要操作 |
|---|---|---|
| 普通用户 | 查看项目记忆、搜索结论、阅读 Wiki | 搜索、查看 source、查看 timeline、导出 Wiki |
| 小组成员 | 维护课程项目记忆 | 导入 source、创建 memory、编辑 memory、处理 conflict |
| Agent | 基于权限读取 context pack | recall、生成建议 memory、生成 wiki 草稿 |
| 管理员 | 管理用户、权限、审计 | 用户管理、Agent 管理、权限策略、归档、恢复 |
| 访客 / 只读用户 | 查看公开 Wiki 或演示结果 | 浏览、搜索公开内容 |

## 3. 功能需求

| 模块 | 功能 | P0/P1/P2 |
|---|---|---|
| Workspace 管理 | 创建工作区、成员管理 | P0 |
| 用户与 Agent 管理 | 管理用户、Agent 和角色 | P1 |
| Source 导入 | 导入 Markdown / txt，切分 chunk | P0 |
| Message / Chunk 管理 | 保存会话消息和文档块 | P0 |
| Memory 抽取与编辑 | 创建、编辑、删除 memory | P0 |
| Evidence 追溯 | memory 绑定 source chunk | P0 |
| Revision 版本管理 | 修改 memory 自动记录版本 | P0 |
| AuditLog 审计 | 记录关键操作 | P0 |
| Recall 检索 | 关键词 / 全文检索 memory | P0 |
| Markdown Wiki 导出 | 导出 WikiPage 和版本 | P0 |
| Timeline | 展示项目决策演进 | P1 |
| AccessPolicy | Agent 权限过滤 | P1 |
| ConflictRecord | 冲突记忆治理 | P1 |
| Entity / Relation | 实体和关系管理 | P2 |
| ForgetRequest | 遗忘与归档申请 | P2 |
| SkillMemory | 过程性经验归纳 | Future |

## 4. 非功能需求

| 类别 | 要求 | 实现方式 |
|---|---|---|
| 数据完整性 | 不允许孤立 evidence、revision | 主键、外键、CHECK |
| 可追溯性 | 每条 memory 可追到 source chunk | MemoryEvidence |
| 权限控制 | Agent 只能看授权范围 | AccessPolicy + view |
| 可审计性 | 关键操作可回放 | AuditLog |
| 可降级性 | 不依赖 LLM 也能跑通 P0 | 人工/规则抽取 |
| 可演示性 | 5–8 分钟讲清楚 | 封闭 demo 数据 |
| 性能需求 | 课程规模下秒级查询 | 索引、FTS、limit |
| 安全性 | 删除不物理丢失 | soft delete、status |

## 5. 项目边界

本项目不做：

- 从零实现数据库内核
- 复杂查询优化器
- 复杂多 Agent runtime
- 企业级 Row Level Security
- 复杂 temporal knowledge graph
- LLM 自动高质量抽取作为必需功能

本项目重点做：

- 数据库建模
- SQL 查询
- 索引、视图、触发器
- 来源追溯
- 版本审计
- 权限治理
- Wiki 投影
