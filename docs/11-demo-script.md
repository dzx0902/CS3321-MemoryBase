# 演示脚本

## 数据库准备

```bash
npm run db:setup
```

该命令等价于 `python scripts/db_cli.py reset`，会 drop public schema、按顺序加载 00–07 + governance fixture (10) + 08 demo queries，**自动包含** Tier 1 #6 的 governance 演示数据（≥ 1 forgotten memory / ≥ 1 archived / superseded / ≥ 1 forgotten source / ≥ 1 resolved conflict）。**不需要单独运行 `psql -f database/10_governance_demo_fixture.sql`**。

## 演示目标

用 5–8 分钟展示 MemoryBase 的数据库建模、检索、追溯、审计、版本和 Wiki 投影能力。

## 演示流程

1. 打开 Dashboard，展示 workspace 统计。
2. 进入 Sources 页面，展示 `db:setup` 已导入的 6 份讨论记录。
3. 展示 SourceDocument 和 SourceChunk；如需要演示写入流程，可现场额外导入一份短 note，而不是重复导入 seed 中已有的 6 份记录。
4. 从 chunk 创建 MemoryItem。
5. 展示 MemoryEvidence 来源追溯。
6. 进入 Recall 页面，搜索“为什么放弃校园食堂系统”。
7. 展示返回的 memory、evidence 和 source chunk。
8. 修改一条 memory。
9. 展示 MemoryRevision 自动新增。
10. 展示 AuditLog。
11. 展示 Agent 权限过滤。
12. 展示 ConflictRecord。
13. 导出 Markdown Wiki。
14. 展示 database/08_demo_queries.sql 的 SQL 查询结果。

## 必备演示数据

- 6 份 discussion_xx.md
- 至少 20 条 memory
- 至少 20 条 evidence
- 至少 5 条 revision
- 至少 10 条 audit
- 至少 3 个 Wiki 页面（`07_seed.sql` 已包含 `why-memorybase`、`database-design`、`demo-playbook`）
- 至少 1 个 conflict
- 至少 1 个 private memory

## 可选治理 walkthrough

治理演示的详细 SQL 和页面检查见 `docs/governance-demo-walkthrough.md`。
