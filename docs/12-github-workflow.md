# GitHub 协作与开发流程

## 1. 分支策略

```text
main       稳定版本，只允许 PR 合并
dev        日常集成分支
feature/*  功能分支
fix/*      修复分支
docs/*     文档分支
sql/*      数据库任务分支
```

## 2. Issue 规范

Issue 应包含：

- 背景
- 目标
- 任务清单
- 验收标准
- 标签
- Milestone
- Assignee

## 3. PR 规范

PR 必须：

- 关联 Issue
- 填写修改内容
- 说明测试情况
- 说明数据库影响
- 标注 AI 使用情况
- 至少一名成员 review

## 4. Label 建议

```text
type: docs
type: database
type: backend
type: frontend
type: test
type: ci
type: demo

priority: p0
priority: p1
priority: p2
priority: future

area: source
area: memory
area: evidence
area: recall
area: policy
area: audit
area: wiki
area: timeline
area: conflict
```

## 5. Milestone

```text
M1 - Project Setup & Documentation
M2 - Database Schema & SQL Foundation
M3 - P0 Source-Memory-Evidence MVP
M4 - Recall, Revision & Audit
M5 - Wiki, Timeline & Demo UI
M6 - Final Report & Presentation
```

## 6. AI 使用规则

AI 可以辅助：

- 生成代码草稿
- 补测试
- 写文档
- 做初步 review

AI 不可以：

- 绕过 PR
- 直接合并 main
- 单独决定数据库结构
- 单独决定权限和删除逻辑
