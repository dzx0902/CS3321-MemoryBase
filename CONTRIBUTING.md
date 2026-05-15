# Contributing Guide

## 开发流程

1. 所有任务必须先创建 Issue。
2. 从 Issue 创建对应分支。
3. 禁止直接向 main 分支 push。
4. 所有代码必须通过 Pull Request 合并。
5. PR 必须关联 Issue。
6. PR 合并前必须通过 CI。
7. PR 至少需要一名成员 review。
8. 涉及数据库结构、权限、审计、删除逻辑的修改必须由负责人 review。

## 分支命名

```text
feature/source-ingest
feature/memory-crud
feature/wiki-export
feature/recall-search
sql/schema-core
docs/requirements
fix/audit-trigger
```

## Commit 规范

```text
feat(source): add source document import API
feat(memory): implement memory item CRUD
feat(sql): add memory evidence schema
fix(trigger): correct memory revision generation
docs(requirements): add user role analysis
test(recall): add keyword recall tests
chore(ci): add GitHub Actions workflow
```

## AI 使用规范

AI 可以辅助生成代码、测试、文档和 review 建议，但不能绕过人类审查。涉及数据库结构、权限、审计、删除逻辑、安全策略的修改必须人工复核。
