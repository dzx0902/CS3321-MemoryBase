# EXPLAIN ANALYZE 案例集

本文件收集 4 个有代表性的查询，配套 `database/04_indexes.sql` 中的索引设计，演示 PostgreSQL 查询执行的实际计划。配套阅读：`docs/index-rationale.md`。

所有计划均取自实际数据库执行（PostgreSQL 16.13，本课程 demo workspace `00000000-0000-0000-0000-000000000201`，截至本文件撰写时表规模：`memory_item` 25 行 / `audit_log` 39 行 / `source_chunk` 20 行 / `wiki_page` 3 行）。

> **数据规模说明**：demo 数据量较小，部分场景下 PostgreSQL planner 会**主动选 Seq Scan**（这是正确决定，因为对几十行数据走索引反而更慢——B+ tree 要先读根节点、再读叶子、再回表）。为了**演示索引路径的形态**，几个案例使用 `SET LOCAL enable_seqscan = off` 临时强制 planner 走索引，对比"小数据 + Seq Scan"与"假设大数据时 + Index 路径"的差异。**生产数据量（1 万行以上）下，planner 会自动选择索引路径**，无需强制。

## 如何复现

```bash
# 1. 启动 PostgreSQL（已在跑则跳过）
docker compose up -d postgres   # 或本机已装好的 postgres

# 2. 完整 setup：drop & recreate schema → 加载 00-06 + 07 seed → 搜索字段 backfill
#    → 10_governance_demo_fixture（自动加载，详见 scripts/db_cli.py run_seed）
#    → 08_demo_queries
npm run db:setup

# 3. 刷新统计 + 准备 visibility map（让 planner 看到最新行数，并支撑 index-only scan）
psql $DATABASE_URL -c "VACUUM ANALYZE;"

# 4. 跑本文档任一案例的 EXPLAIN
psql $DATABASE_URL -c "EXPLAIN (ANALYZE, BUFFERS) ..."
```

> `npm run db:setup` 等价于 `python scripts/db_cli.py reset`。它**会丢弃 public schema 并重建**，仅用于 dev/demo 环境；生产/共享 DB 不要跑。

EXPLAIN 选项约定：
- `ANALYZE` — 真实执行并报告实际行数 / 时间
- `BUFFERS` — 报告 shared buffer 命中数（IO 成本的现代度量）
- `FORMAT TEXT` — 人可读形态（其他可选：`JSON` / `YAML` / `XML`）

---

## 案例 1：Memory 活跃排序（Covering Index → Index-Only Scan）

**业务场景**：dashboard / wiki 合成 / API 首屏需要"workspace 内活跃 memory 按重要性 + 最近更新排序的短列表"。

**SQL**：

```sql
SELECT memory_id, memory_type, confidence, access_level
  FROM memory_item
 WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
   AND status = 'active'
 ORDER BY importance DESC, updated_at DESC
 LIMIT 10;
```

### 1.1 走 covering index（`idx_memory_active_ranking`）

强制 `enable_seqscan = off` 让 planner 选索引路径（在大数据量下会自动选）：

```
 Limit  (cost=0.14..4.31 rows=10 width=48) (actual time=0.006..0.007 rows=10 loops=1)
   Buffers: shared hit=2
   ->  Index Only Scan using idx_memory_active_ranking on memory_item
         Index Cond: (workspace_id = '00000000-0000-0000-0000-000000000201'::uuid)
         Heap Fetches: 0
         Buffers: shared hit=2
 Execution Time: 0.016 ms
```

**关键观察**：
- **`Index Only Scan` + `Heap Fetches: 0`** — 教科书级的 index-only scan 信号。整个查询 0 次回表，IO 全部由索引叶子页满足。
- **无 Sort 节点** — 索引 key 已经按 `(workspace_id, importance DESC, updated_at DESC)` 排好序，planner 直接顺取前 10 条。
- **Buffers: shared hit=2** — 只命中 2 个共享 buffer 页（1 个 root + 1 个 leaf）。

### 1.2 对比：去掉 covering index 后

在事务里 DROP 同一索引，看 fallback 行为：

```
 Limit  (cost=13.07..13.10 rows=10 width=48) (actual time=0.026..0.027 rows=10 loops=1)
   Buffers: shared hit=4
   ->  Sort
         Sort Key: importance DESC, updated_at DESC
         Sort Method: quicksort  Memory: 27kB
         ->  Bitmap Heap Scan on memory_item
               Recheck Cond: ((workspace_id = '00000000-0000-0000-0000-000000000201'::uuid)
                              AND ((status)::text = 'active'::text))
               Heap Blocks: exact=3
               ->  Bitmap Index Scan on idx_memory_workspace_status_validity
 Execution Time: 0.037 ms
```

**关键退化**：
- 没有 covering 时，planner 退到 `idx_memory_workspace_status_validity`（B+ tree 复合索引）走 Bitmap Index Scan，**再做 Bitmap Heap Scan 回表**取 `memory_type / confidence / access_level`。
- 因为索引顺序不是 `importance DESC`，多了一个 **Sort 节点**。
- status 条件仍能进入复合索引，但该索引不覆盖 SELECT 列，也不能消除 `ORDER BY importance DESC, updated_at DESC` 的排序。
- **Buffers 命中 4 个**（vs 2 个），小表规模下只多 2 页；生产规模下差异主要来自 Sort 和 heap fetch。

> **教学要点**：单一索引同时实现了 partial（缩小规模）+ composite DESC（消除 Sort）+ INCLUDE（消除 heap fetch）三种现代特性。配合 visibility map 即可达到"读 2 个 buffer 页完成 LIMIT 10"的极致。

---

## 案例 2：Recall 主查询（GIN tsvector + GIN trigram + 多表 join）

**业务场景**：`recall_service.py` 中召回主查询：根据 query 字符串，先用 FTS + trigram 拿到匹配 chunk，再 join memory_evidence → memory_item，按综合分数排序返回 top K。

**SQL**（简化版，原 SQL 见 `backend/app/services/recall_service.py:124`）：

```sql
WITH matched_chunks AS (
    SELECT sc.chunk_id, sc.chunk_text,
           ts_rank(sc.search_vector, websearch_to_tsquery('simple', 'memorybase')) AS chunk_rank
      FROM source_chunk sc
      JOIN source_document sd ON sd.doc_id = sc.doc_id
     WHERE sd.workspace_id = '...'
       AND sd.status = 'active'
       AND (sc.search_vector @@ websearch_to_tsquery('simple', 'memorybase')
            OR sc.chunk_text ILIKE '%memorybase%')
)
SELECT mi.memory_id, mi.memory_type, mi.canonical_text,
       MAX(mc.chunk_rank) + (AVG(me.weight) * 0.2) + (mi.importance * 0.1) AS score
  FROM matched_chunks mc
  JOIN memory_evidence me ON me.chunk_id = mc.chunk_id
  JOIN memory_item mi ON mi.memory_id = me.memory_id
 WHERE mi.workspace_id = '...'
   AND mi.status = 'active'
 GROUP BY mi.memory_id, mi.memory_type, mi.canonical_text, mi.importance
 ORDER BY score DESC LIMIT 5;
```

### 2.1 完整 plan（默认）

```
 Limit  (cost=8.72..8.72 rows=2 width=138) (actual time=0.065..0.066 rows=2 loops=1)
   Buffers: shared hit=12
   ->  Sort  Sort Key: score DESC
         ->  GroupAggregate  Group Key: mi.memory_id
               ->  Sort  Sort Key: mi.memory_id
                     ->  Hash Join  Hash Cond: (sc.doc_id = sd.doc_id)
                           ->  Nested Loop
                                 ->  Hash Join  Hash Cond: (me.chunk_id = sc.chunk_id)
                                       ->  Seq Scan on memory_evidence me     (20 rows)
                                       ->  Seq Scan on source_chunk sc        (Filter: FTS OR trigram)
                                 ->  Index Scan using memory_item_memory_id_workspace_id_key on memory_item mi
                                       Index Cond: (memory_id = me.memory_id AND workspace_id = ...)
                           ->  Seq Scan on source_document sd
 Execution Time: 0.106 ms
```

**关键观察**：
- **Nested Loop + Index Scan on `memory_item`** — 内层循环对每个匹配 chunk 通过 `(memory_id, workspace_id)` 复合唯一索引定位 memory，是典型的"小驱动表 + 索引查找"模式。
- `source_chunk` 的 FTS + ILIKE 在小数据量下走 Seq Scan + Filter；大数据量下会切换到 BitmapOr(BitmapIndexScan(`idx_source_chunk_fts`), BitmapIndexScan(`idx_source_chunk_text_trgm`))。
- `GroupAggregate` 在 Sort 之后，按 `memory_id` 聚合多个 evidence。

### 2.2 强制走 GIN（演示 GIN tsvector + GIN trigram bitmap 路径）

小数据下 planner 默认选 Seq Scan（§2.1）；要演示真实索引路径，把 seq scan 和 (非 bitmap) index scan 全部关掉，强制走 bitmap：

```sql
SET enable_seqscan   = off;
SET enable_indexscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT sc.chunk_id, sc.chunk_no, sc.chunk_text
  FROM source_chunk sc
 WHERE sc.search_vector @@ websearch_to_tsquery('simple', 'memorybase')
    OR sc.chunk_text ILIKE '%memorybase%'
 LIMIT 5;
```

实际 plan：

```
 Limit  (cost=48.10..51.23 rows=2 width=167) (actual time=0.016..0.017 rows=2 loops=1)
   Buffers: shared hit=21
   ->  Bitmap Heap Scan on source_chunk sc
         Recheck Cond: ((search_vector @@ '''memorybase'''::tsquery)
                       OR (chunk_text ~~* '%memorybase%'::text))
         Heap Blocks: exact=2
         ->  BitmapOr
               ->  Bitmap Index Scan on idx_source_chunk_fts
                     Index Cond: (search_vector @@ '''memorybase'''::tsquery)
                     Buffers: shared hit=2
               ->  Bitmap Index Scan on idx_source_chunk_text_trgm
                     Index Cond: (chunk_text ~~* '%memorybase%'::text)
                     Buffers: shared hit=17
 Execution Time: 0.022 ms
```

**关键观察**：
- **`BitmapOr` 节点**把"FTS 命中"和"trigram 子串命中"两条 bitmap 直接合并 → 完美对应 SQL 的 `OR` 谓词。这是 PostgreSQL bitmap 执行的标志性能力。
- 上面那个 Bitmap Index Scan 命中 **`idx_source_chunk_fts`（GIN tsvector 倒排索引）**；下面那个命中 **`idx_source_chunk_text_trgm`（GIN trigram 模糊索引）**。两个 GIN 索引同一查询同时点亮，验证 `docs/index-rationale.md` §3 + §4 的索引选型决策正确。
- `Bitmap Heap Scan` 的 `Recheck Cond`：bitmap 路径返回的是 page-level 候选，回表时必须再次验证行级谓词（trigram 是 lossy 的，可能产生假阳性）。
- **生产规模下无需 `SET`**：FTS 谓词的 selectivity 在 GIN posting list 中能快速估算；当匹配比例 < ~1% 时 planner 会自动选 Bitmap GIN 路径，本节的两个 SET 只是把"假设大数据时"的执行形态在小 demo 数据上提前展示。

#### 单 GIN tsvector 路径（无 trigram OR 分支）

如果只走 FTS（无 ILIKE OR 分支），plan 退化为单个 Bitmap Index Scan：

```
 Bitmap Heap Scan on source_chunk sc
   Recheck Cond: (search_vector @@ '''memorybase'''::tsquery)
   ->  Bitmap Index Scan on idx_source_chunk_fts
         Index Cond: (search_vector @@ '''memorybase'''::tsquery)
         Buffers: shared hit=2
```

Buffers 从 21 降到 4，说明 trigram 分支在 OR 路径里贡献了大部分 IO 成本（trigram posting list 较厚）。这给"是否要在生产对 chunk_text 也建 trigram 索引"提供了量化依据：trigram 让"任意位置子串匹配"变可索引，代价是 OR 时多 ~17 个 buffer。

> **教学要点**：召回路径串起 GIN tsvector（倒排索引，§3）+ GIN trigram（子串模糊，§4）+ 复合 B+ tree（workspace 隔离 + 主键查找，§2）+ Nested Loop / Hash Join 切换（统计驱动）。是项目里使用索引"密度"最大的一条查询。

---

## 案例 3：审计聚合（BRIN vs B-tree）

**业务场景**：管理后台 / 课程报告需要"全库（不限 workspace）过去 N 天的 audit_log 按天 + 按 action_type 聚合统计"。这是 BRIN 最擅长的"append-only 时间维 + 大范围分析"场景。

**SQL**：

```sql
SELECT date_trunc('day', created_at) AS day, action_type, count(*) AS cnt
  FROM audit_log
 WHERE created_at >= now() - interval '30 days'
 GROUP BY 1, 2
 ORDER BY 1 DESC, cnt DESC;
```

### 3.1 默认（小数据 → Seq Scan）

```
 Sort  Sort Key: day DESC, cnt DESC
   Buffers: shared hit=12
   ->  HashAggregate  Group Key: date_trunc(...), action_type
         Buffers: shared hit=6
         ->  Seq Scan on audit_log  Filter: created_at >= now() - 30 days
              Rows Removed by Filter: 1
              Buffers: shared hit=6
 Execution Time: 0.148 ms
```

39 行 + 时间过滤几乎全部命中 → Seq Scan 是最优解。

### 3.2 假设大数据：强制走索引（B-tree 路径，已复验）

`SET enable_seqscan = off`，未单独限制其他索引：

```
 Bitmap Heap Scan on audit_log
   Recheck Cond: (created_at >= now() - 30 days)
   Heap Blocks: exact=6
   Buffers: shared hit=7
   ->  Bitmap Index Scan on idx_audit_target_time
         Index Cond: (created_at >= now() - 30 days)
         Buffers: shared hit=1
 Execution Time: 0.070 ms
```

注意：该计划已在 fresh demo DB 上复验。B+ tree 复合索引最擅长使用先导列；这里查询只约束 trailing column `created_at`，planner 仍选择 `idx_audit_target_time`，是因为 demo 数据量很小且我们显式关闭了 Seq Scan。生产报告中应把它解释为"B-tree 竞争路径"，不是推荐的全库时间窗索引。

### 3.3 BRIN 路径（drop 竞争索引后）

```sql
BEGIN;
DROP INDEX idx_audit_workspace_time;
DROP INDEX idx_audit_actor_time;
DROP INDEX idx_audit_target_time;
SET LOCAL enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS) <上面查询>;
ROLLBACK;
```

```
 Bitmap Heap Scan on audit_log
   Recheck Cond: (created_at >= now() - 30 days)
   Heap Blocks: lossy=6
   ->  Bitmap Index Scan on idx_audit_brin_time
         Index Cond: (created_at >= now() - 30 days)
         Buffers: shared hit=5
   Buffers: shared hit=11
 Execution Time: 0.195 ms
```

**关键观察**：
- BRIN 报 **`Heap Blocks: lossy=6`** —— 这是 BRIN 的特征：page range 内可能有不满足条件的行，所以是"lossy"，需要 Recheck Cond 在 heap 上验证。B-tree 报的是 `exact=6`，索引精确定位到行。
- Buffers 略多（11 vs 7），因为 39 行规模下 BRIN 的 page range 元数据反而引入额外读。

### 3.4 索引大小对比

```sql
SELECT indexname,
       pg_size_pretty(pg_relation_size(indexname::regclass)) AS size,
       am.amname AS method
  FROM pg_indexes pi
  JOIN pg_class c ON c.relname = pi.indexname
  JOIN pg_am am ON am.oid = c.relam
 WHERE tablename = 'audit_log';
```

| indexname | size | method |
|---|---|---|
| `audit_log_pkey` | 16 kB | btree |
| `idx_audit_actor_time` | 16 kB | btree |
| **`idx_audit_brin_time`** | **24 kB** | **brin** |
| `idx_audit_target_time` | 16 kB | btree |
| `idx_audit_workspace_time` | 16 kB | btree |

> **诚实披露**：在 39 行规模下 BRIN 实际**比 B-tree 还大**——因为 BRIN 有元页 + range descriptor 的固定开销，B-tree 39 行也只有 1 个叶子页（最小 16 kB）。
>
> **BRIN 的优势在哪儿出现**：当 `audit_log` 行数到 100 万级别时：
> - B-tree 索引大小 ≈ 几十 MB（与行数线性相关）
> - BRIN 索引大小 ≈ 几十 KB（与 page 数量相关；`pages_per_range = 32` 意味着每 32 页 1 条元组，1 GB 表 ≈ 4000 条元组）
>
> 这就是教科书所说的 "BRIN 索引大小相比 B-tree 小 **1-2 个数量级**"。同时 BRIN 的写入开销几乎为零（只在 range 边界更新元组），对纯 append 的 `audit_log` 是绝佳匹配。

> **教学要点**：BRIN 是讲清楚"索引设计要看数据物理分布"的最佳案例。课程上一般默认"每行一索引条目"，BRIN 打破这个假设——用"块级 min/max"代替"行级 row pointer"，以"可能的假阳性 + 必须 Recheck"换"小到可以放进 buffer 的索引"。详见 `docs/index-rationale.md` §5.1。

---

## 案例 4：Wiki Provenance Join（多跳来源追溯）

**业务场景**：Wiki 页面详情页要展示"页面 → 场景 → 记忆 → 证据 chunk → 源文档"完整 5 跳来源链。视图 `v_wiki_page_sources` 封装了这条 join。

**SQL**：

```sql
SELECT page_id, page_slug, memory_id, chunk_id, doc_id, source_title, start_line, end_line
  FROM v_wiki_page_sources
 WHERE workspace_id = '00000000-0000-0000-0000-000000000201'
 LIMIT 20;
```

视图定义见 `database/05_views.sql:91-153`，核心是 `wiki_page → memory_scene → LATERAL(memory_scene_cell) → memory_item → memory_evidence → source_chunk → source_document` 这条链。

### 4.1 完整 plan

```
 Limit  (cost=18.39..40.01 rows=1 width=1068) (actual time=0.160..0.286 rows=6 loops=1)
   Buffers: shared hit=55
   ->  Nested Loop Left Join
         Filter: ((sd.doc_id IS NULL) OR ((sd.status)::text = 'active'::text))
         ->  Nested Loop Left Join
               ->  Index Scan using idx_wiki_page_workspace_status on wiki_page wp
                     Index Cond: (workspace_id = ... AND status = 'active')
               ->  Hash Right Join  Hash Cond: (mi.memory_id = page_memory.memory_id)
                     ->  Seq Scan on memory_item mi
                     ->  Hash  ->  Subquery Scan on page_memory
                           ->  HashAggregate
                                 ->  Append
                                       ->  Result  One-Time Filter: ...
                                             InitPlan 1
                                               ->  Index Only Scan using memory_scene_cell_pkey
                                       ->  Bitmap Heap Scan on memory_scene_cell msc
                                             ->  Bitmap Index Scan on idx_memory_scene_cell_order
         ->  Nested Loop Left Join
               ->  Index Only Scan using memory_evidence_memory_id_chunk_id_evidence_role_key on memory_evidence me
               ->  Index Scan using source_chunk_pkey on source_chunk sc
               ->  Index Scan using source_document_pkey on source_document sd
 Execution Time: 0.492 ms
```

**关键观察**：
- 整棵树有 **6 个 join 节点**（5 个 LEFT JOIN + 1 个 LATERAL），是项目最复杂的查询之一。
- LATERAL 子查询里用 `Append + Result + Bitmap Heap Scan` 把"直接关联 memory（generated_from_memory_id）"与"通过 scene_cell 间接关联 memory"两种来源合并去重。
- 当前 demo DB 已经点亮 `idx_wiki_page_workspace_status`、`memory_scene_cell_pkey`、`idx_memory_scene_cell_order`、`memory_evidence_memory_id_chunk_id_evidence_role_key`、`source_chunk_pkey` 和 `source_document_pkey`。这说明视图虽然封装了复杂 join，planner 仍能把过滤和连接下推到具体索引。

> **教学要点**：这个查询展示了**视图作为复杂 join 抽象**的价值——业务代码只需要 `SELECT ... FROM v_wiki_page_sources WHERE workspace_id = ?`，视图把 6 个表的 join + 去重逻辑全部封装。对应课程上"视图作为派生关系 / 关系代数表达"的概念。同时也是 §5.1 提到的 `v_provenance_lineage` 递归 CTE 视图（Tier 2 #11）的语义前身——后者要在此基础上把"固定 5 跳"扩展为"任意深度递归"。

---

## 索引覆盖率总结

本文 4 个案例触及的索引：

| 索引 | 案例 | 类别 |
|---|---|---|
| `idx_memory_active_ranking` | 案例 1（covering） | Partial + Composite DESC + Covering (INCLUDE) |
| `memory_item_memory_id_workspace_id_key` | 案例 2（Nested Loop 内层） | B+ tree 唯一复合 |
| `idx_memory_workspace_status_validity` | 案例 1B（fallback） | B+ tree 复合 |
| `idx_source_chunk_fts` | 案例 2（大数据切换） | GIN tsvector |
| `idx_source_chunk_text_trgm` | 案例 2（OR 分支大数据切换） | GIN trigram |
| `idx_audit_target_time` | 案例 3.2 | B+ tree 复合（trailing time） |
| `idx_audit_brin_time` | 案例 3.3 | **BRIN** |
| `idx_wiki_page_workspace_status` | 案例 4 | B+ tree 复合 |
| `memory_scene_cell_pkey` | 案例 4 | B+ tree PK |
| `idx_memory_scene_cell_order` | 案例 4 | B+ tree 复合排序 |
| `memory_evidence_memory_id_chunk_id_evidence_role_key` | 案例 4 | B+ tree 唯一复合 |
| `source_chunk_pkey` | 案例 4 | B+ tree PK |
| `source_document_pkey` | 案例 4 | B+ tree PK |

> 计 13 个不同索引、覆盖 **7 种索引类别**（PK / 唯一复合 / 复合带 DESC / GIN tsvector / GIN trigram / BRIN / Covering）。完整 9 类索引清单见 `docs/index-rationale.md` §1。

## 复现命令汇总

把本文每个案例改成可直接 copy 的 SQL 文件：

```bash
# 准备
psql $DATABASE_URL -c "VACUUM ANALYZE memory_item, audit_log, source_chunk, memory_evidence, wiki_page, memory_scene_cell, memory_scene, source_document;"

# 案例 1
psql $DATABASE_URL -c "SET enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS) SELECT memory_id, memory_type, confidence, access_level
  FROM memory_item WHERE workspace_id = '...' AND status = 'active'
  ORDER BY importance DESC, updated_at DESC LIMIT 10;"

# 案例 2（取自 recall_service.py:124 的简化版，见正文）

# 案例 3.3（BRIN 强制路径）
psql $DATABASE_URL <<SQL
BEGIN;
DROP INDEX idx_audit_workspace_time;
DROP INDEX idx_audit_actor_time;
DROP INDEX idx_audit_target_time;
SET LOCAL enable_seqscan = off;
EXPLAIN (ANALYZE, BUFFERS) SELECT date_trunc('day', created_at) AS day,
       action_type, count(*) AS cnt
  FROM audit_log WHERE created_at >= now() - interval '30 days'
  GROUP BY 1, 2 ORDER BY 1 DESC, cnt DESC;
ROLLBACK;
SQL

# 案例 4
psql $DATABASE_URL -c "EXPLAIN (ANALYZE, BUFFERS)
  SELECT page_id, page_slug, memory_id, chunk_id, doc_id, source_title, start_line, end_line
    FROM v_wiki_page_sources WHERE workspace_id = '...' LIMIT 20;"
```
