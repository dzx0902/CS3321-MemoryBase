# 最终报告整合入口

> Gap 1 输出说明：`docs/final-report.md` 是当前可直接排版的最终报告主体草稿；本文负责说明正文、图表、截图、SQL/源码附录和成员信息的装配关系。

## 1. 报告标题

《MemoryBase：面向组织与团队的 AI-native 可追溯长期记忆数据库系统设计与实现》

旧标题“面向 AI Agent 协作研发的文件—数据库双态长期记忆系统”可作为副标题或答辩口径，但最终主叙事建议使用“组织与团队”，避免场景过窄。

## 2. 主体正文

主体文件：

```text
docs/final-report.md
```

当前正文结构：

| 章节 | 内容 | 主要素材来源 |
|---|---|---|
| 摘要 | 项目定位、数据库主线、评测边界 | `docs/00-project-overview.md`、`docs/innovation-analysis.md` |
| 1 项目概述 | 项目定位、核心链路、已交付能力 | `docs/00-project-overview.md` |
| 2 研究现状分析 | RAG、Agent memory、企业知识库、GraphRAG、benchmark | `docs/research-landscape.md` |
| 3 需求分析 | 角色、功能需求、非功能需求 | `docs/01-requirements.md` |
| 4 数据流设计 | 0 层、1 层、Source/Recall/Wiki 2 层流程 | `docs/02-data-flow.md` |
| 5 数据字典 | 核心数据项、数据结构 | `docs/03-data-dictionary.md` |
| 6 概念结构设计与 E-R 图 | 概念分层、核心 ER、关系和基数 | `docs/04-er-design.md`、`docs/final-assets/diagrams/` |
| 7 逻辑结构设计与范式分析 | 关系模式、E-R 转换、3NF/BCNF | `docs/05-logical-design.md`、`docs/normalization.md` |
| 8 物理结构设计 | PostgreSQL、路径、索引、EXPLAIN、视图、触发器 | `docs/06-physical-design.md`、`docs/index-rationale.md`、`docs/explain-analyze.md` |
| 9 系统总体架构 | 前后端、CLI、Agent、evaluation、Graph | `docs/07-system-architecture.md` |
| 10 API 与模块 IPO | API 摘要、模块 IPO | `docs/08-api-design.md`、`docs/09-module-ipo.md` |
| 11 系统实现 | Source→Wiki、Recall、Governance、状态机 | `docs/final-assets/diagrams/` |
| 12 系统演示 | demo setup、操作流程、截图索引 | `docs/11-demo-script.md`、`docs/final-assets/screenshots/README.md` |
| 13 测试与评估 | 自动化测试、SQL 测试、LongMemEval 解释 | `docs/10-test-plan.md`、`docs/27-longmemeval-full-evaluation-20260609.md` |
| 14 创新点总结 | DB-first、provenance、governance、visibility、fallback、evaluation | `docs/innovation-analysis.md` |
| 15 小组分工 | 成员贡献表和边界说明 | `docs/contribution-ledger.md` |
| 16 带注释源程序 | SQL 和高级语言源程序清单 | `docs/source-sql-appendix.md` |
| 17 总结与展望 | 已完成、边界、future work | `docs/innovation-analysis.md`、`docs/process/22-backend-memory-roadmap.md` |

## 3. 图表插入清单

图源和 SVG 位于：

```text
docs/final-assets/diagrams/
```

| 建议位置 | 图片 |
|---|---|
| 第 6 章概念结构设计开头 | `01-er-core.svg` |
| 第 6 章附录或正文后半 | `02-er-full.svg` |
| 第 11.1 节 Source 到 Wiki | `03-source-to-wiki.svg` |
| 第 11.2 节 Recall | `04-recall.svg` |
| 第 11.3 节 Governance | `05-governance.svg` |
| 第 11.4 节 Memory 状态机 | `06-memory-status.svg` |

如需重新渲染，按 `docs/final-assets/diagrams/README.md` 使用 Mermaid CLI。

## 4. 截图插入清单

截图和完整命令日志位于：

```text
docs/final-assets/screenshots/
```

推荐正文截图：

| 报告位置 | 截图 |
|---|---|
| 系统演示总览 | `ui/01-dashboard.png` |
| Source 导入 / chunk | `ui/02-sources-list.png`、`ui/03-source-detail-project-pivot.png` |
| Memory evidence / revision | `ui/05-memory-detail-evidence-revisions.png` |
| Recall / context pack | `ui/06-recall-search-results.png`、`ui/07-recall-context-pack.png` |
| Optional LLM QA | `ui/08-recall-qa-answer-or-config-state.png` |
| Governance audit / conflict / forget | `ui/10-governance-audit.png`、`ui/12-governance-conflicts.png`、`ui/13-governance-forget-requests.png` |
| Graph Explorer | `ui/15-graph-explorer-demo-workspace.png` |
| SQL 证据 | `sql/04-focused-sql-evidence.png` |
| 测试结果 | `tests/01-pytest-core.png`、`tests/02-frontend-build.png` |

注意：SQL/test PNG 是从完整日志渲染，避免终端预览截断。若报告需要更清晰缩放，优先使用同名 `.svg`。

## 5. 附录安排

| 附录 | 内容 | 入口 |
|---|---|---|
| 附录 A SQL 源程序 | DDL、indexes、views、triggers、seed、demo queries | `database/*.sql`、`docs/source-sql-appendix.md` |
| 附录 B 高级语言源程序说明 | FastAPI、React、CLI、evaluation、tests | `docs/source-sql-appendix.md` |
| 附录 C 演示数据 | seed workspace、governance fixture、graph demo data | `database/07_seed.sql`、`database/09_graph_demo.sql`、`database/10_governance_demo_fixture.sql` |
| 附录 D 测试与命令日志 | backend tests、frontend build、SQL outputs、EXPLAIN | `docs/final-assets/screenshots/logs/` |
| 附录 E 评测结果 | LongMemEval summary 和 CSV | `docs/27-longmemeval-full-evaluation-20260609.md`、`evaluation/results/longmemeval_full_20260609.csv` |

## 6. 正式排版前待补项

这些是内容层面之外的最终排版信息，需由团队确认：

1. 封面：课程名、教师、学院/班级、组号、四位成员姓名和学号。
2. 第 15 章成员分工：第四位成员的实际贡献证据仍为空，需要补 Git 身份或非 Git 证据。
3. 图表编号：Word/PDF 中按“图 6-1”“表 8-1”等重新编号。
4. 截图压缩：正文只放关键截图，其余放附录或 PPT。
5. 引用格式：参考资料可按老师要求改成 GB/T 7714、APA 或脚注格式。

## 7. 最终提交前检查

建议在最终导出报告前重新执行：

```bash
uv run ruff check backend/app backend/tests evaluation
uv run --with pytest python -m pytest backend/tests -q
cd frontend && npm run lint && npm run build
git diff --check
```

如果数据库或截图更新，再执行：

```bash
npm run db:setup
psql $DATABASE_URL -f database/08_demo_queries.sql
```

并同步更新 `docs/final-assets/screenshots/README.md` 中的截图基线。
