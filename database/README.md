# Database SQL Files

建议执行顺序：

```bash
psql "$DATABASE_URL" -f database/00_init.sql
psql "$DATABASE_URL" -f database/01_schema_core.sql
psql "$DATABASE_URL" -f database/02_schema_memory.sql
psql "$DATABASE_URL" -f database/03_schema_governance.sql
psql "$DATABASE_URL" -f database/04_indexes.sql
psql "$DATABASE_URL" -f database/05_views.sql
psql "$DATABASE_URL" -f database/06_triggers.sql
psql "$DATABASE_URL" -f database/07_seed.sql
PYTHONPATH=backend .venv/bin/python backend/scripts/backfill_search_terms.py --full --database-url "$DATABASE_URL"
psql "$DATABASE_URL" -f database/08_demo_queries.sql
```

开发环境推荐直接运行 `npm run db:setup`，它会在 seed 后自动执行 lexical search
backfill，避免中文 / 中英混排 seed 的 `search_text_zh` 留空或未分词。
