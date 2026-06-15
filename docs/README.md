# 文档与材料导览

MemoryBase 的设计文档、演示材料、源程序说明与参考资料统一组织在 `docs/` 目录下。其中 [`final-report.md`](final-report.md)（及其导出的 [`final-report.pdf`](final-report.pdf)）是整合后的主报告，已覆盖需求分析、研究现状、方案设计、系统实现、演示与分工；本目录下的其余文档是各章节的详细展开与证据，可按需查阅。

## 主要交付物

- **大作业报告**：[`final-report.md`](final-report.md) / [`final-report.pdf`](final-report.pdf)
- **答辩 PPT**：[`final-assets/slides/final-defense.pdf`](final-assets/slides/final-defense.pdf)
- **流程图 / ER / 时序图**：[`final-assets/diagrams/`](final-assets/diagrams/)
- **系统演示截图**：[`final-assets/screenshots/`](final-assets/screenshots/)
- **源程序**：`database/*.sql`（SQL）、`backend/`、`frontend/`、`evaluation/`（高级语言），清单见 [`source-sql-appendix.md`](source-sql-appendix.md)

## 按主题分文档

| 主题 | 文档 |
|---|---|
| 项目总览 | [`00-project-overview.md`](00-project-overview.md) |
| 需求分析（含数据流图、数据字典） | [`01-requirements.md`](01-requirements.md)、[`02-data-flow.md`](02-data-flow.md)、[`03-data-dictionary.md`](03-data-dictionary.md) |
| 概念设计（E-R） | [`04-er-design.md`](04-er-design.md) + [`final-assets/diagrams/`](final-assets/diagrams/) |
| 逻辑设计与范式 | [`05-logical-design.md`](05-logical-design.md)、[`normalization.md`](normalization.md) |
| 物理设计、索引与 EXPLAIN | [`06-physical-design.md`](06-physical-design.md)、[`index-rationale.md`](index-rationale.md)、[`explain-analyze.md`](explain-analyze.md) |
| 系统架构 / API / 模块 IPO | [`07-system-architecture.md`](07-system-architecture.md)、[`08-api-design.md`](08-api-design.md)、[`09-module-ipo.md`](09-module-ipo.md) |
| 测试与演示 | [`10-test-plan.md`](10-test-plan.md)、[`11-demo-script.md`](11-demo-script.md)、[`governance-demo-walkthrough.md`](governance-demo-walkthrough.md) |
| 研究现状分析 | [`research-landscape.md`](research-landscape.md) |
| 创新点 | [`innovation-analysis.md`](innovation-analysis.md) |
| 可选 LLM 抽取与评测证据 | [`26-optional-llm-memory-extraction.md`](26-optional-llm-memory-extraction.md)、[`27-longmemeval-full-evaluation-20260609.md`](27-longmemeval-full-evaluation-20260609.md) |
| 小组分工与个人贡献 | [`contribution-ledger.md`](contribution-ledger.md) + `contribution-audit-*.tsv` |
| 带注释源程序附录 | [`source-sql-appendix.md`](source-sql-appendix.md) |

## 开发过程记录

[`process/`](process/) 保存项目推进中的规划、roadmap、issue 记录与内部审计，供追溯开发脉络，不属于最终交付主体。
