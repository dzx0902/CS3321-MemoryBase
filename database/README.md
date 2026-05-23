# Database SQL Files

建议执行顺序：

```bash
npm run db:run -- database/00_init.sql
npm run db:run -- database/01_schema_core.sql
npm run db:run -- database/02_schema_memory.sql
npm run db:run -- database/03_schema_governance.sql
npm run db:run -- database/04_indexes.sql
npm run db:run -- database/05_views.sql
npm run db:run -- database/06_triggers.sql
npm run db:run -- database/07_seed.sql
python backend/scripts/backfill_search_terms.py --full --database-url "$DATABASE_URL"
npm run db:run -- database/08_demo_queries.sql
```

开发环境推荐直接运行 `npm run db:setup`，它会在 seed 后自动执行 lexical search
backfill，避免中文 / 中英混排 seed 的 `search_text_zh` 留空或未分词。
调试单个 SQL 文件时推荐使用 `npm run db:run -- <sql-file>`，它和 `db:setup`
一样会自动读取项目根目录的 `.env`。
