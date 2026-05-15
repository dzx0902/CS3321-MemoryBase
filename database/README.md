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
```
