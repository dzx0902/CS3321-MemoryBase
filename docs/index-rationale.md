# 索引选型说明（Index Rationale）

本文件解释 `database/04_indexes.sql` 中每一类索引的工作原理、为什么这样选、以及与课程教学概念的对应关系。配套阅读：`docs/explain-analyze.md`（EXPLAIN ANALYZE 案例集）。

## 0. 关键事实：PostgreSQL 的 "B-tree" 实际是 B+ tree 变种

课堂上讲 **B+ tree** 时强调：所有数据保存在叶子层、内部节点只放分隔键、叶子节点之间通过指针串联以支持范围扫描。

PostgreSQL 文档统一使用 "B-tree" 这个历史名称，但**真实实现是 Lehman & Yao 1981 年提出的 B-link tree**——B+ tree 的一个并发变种：

- 所有 row pointer（heap TID 或 INCLUDE 列）都在叶子层；
- 叶子节点之间维护**右兄弟指针**（right-link），同时支持范围扫描和高并发分裂；
- 内部节点只保存路由用的分隔键；
- 分裂时使用 right-link 避免读者持锁穿越树。

> **结论**：课程上 B+ tree 的所有概念（叶子顺序、范围扫描效率、$O(\log_d n)$ 高度等）在 PostgreSQL 默认 `btree` 上完整成立；并发并发性比经典 B+ tree 还要更好一档。本文档后续提到"B-tree"等同于"B+ tree (B-link 变种)"。

参考：PostgreSQL 文档 *Chapter 67 B-Tree Indexes*；Lehman P.L., Yao S.B., *Efficient Locking for Concurrent Operations on B-Trees*, TODS 1981。

---

## 1. 本项目使用的索引类别一览

`database/04_indexes.sql` 共维护以下 **9 类**索引，覆盖经典关系数据库 + 现代 PostgreSQL 专属能力：

| 类别 | PostgreSQL 实现 | 教学意义 | 本项目案例 |
|---|---|---|---|
| 1. B+ tree (B-link)         | `USING BTREE`（默认） | 课程标准 B+ tree                       | 30+ 个 composite，详见 §2 |
| 2. 复合索引 + 先导列          | composite btree       | 复合索引设计、左前缀匹配                | `idx_memory_workspace_type_status` |
| 3. 排序索引（DESC）           | btree + `DESC`        | 索引内有序性消除 Sort 节点              | `idx_audit_workspace_time` |
| 4. GIN 倒排索引（FTS）        | `USING GIN(tsvector)` | 倒排索引 / 全文检索                     | `idx_memory_fts`、`idx_source_chunk_fts` |
| 5. GIN trigram                | `USING GIN(gin_trgm_ops)` | 子串 / 模糊匹配（任意位置）             | `idx_memory_canonical_text_trgm` 等 3 个 |
| 6. 向量缓存索引               | btree on metadata     | embedding provider/model 定位与去重      | `idx_memory_embedding_workspace_model` |
| 7. Partial index              | `WHERE ...` 子句      | 条件索引，缩小索引规模 + 强约束         | `idx_policy_global_unique WHERE principal_id IS NULL` |
| 8. **BRIN**                   | `USING BRIN(col)`     | 块级索引，append-only 时间数据的现代解  | `idx_audit_brin_time`（新增） |
| 9. **Covering (INCLUDE)**     | `INCLUDE (...)`（PG 11+） | Index-only scan / 消除 heap fetch       | `idx_memory_active_ranking`（新增） |

第 8、9 类是 §5 重点讨论的**"现代/先进"补强**。

---

## 2. B+ tree (B-link) — 主力工作马

绝大多数索引落在这里。设计原则：

### 2.1 先导列 = 租户隔离键

所有业务表都按 `workspace_id` 划分租户，因此**几乎所有复合索引第一列都是 `workspace_id`**：

```sql
idx_source_document_workspace          (workspace_id, imported_at DESC)
idx_source_document_workspace_status   (workspace_id, status, imported_at DESC)
idx_memory_workspace_status            (workspace_id, status)
idx_memory_workspace_type_status       (workspace_id, memory_type, status)
idx_audit_workspace_time               (workspace_id, created_at DESC)
...
```

这样保证：所有"某个 workspace 内查询"的等值过滤都能直接走索引左前缀；不同租户的数据在 B+ tree 中聚集在不同的子树，跨租户扫描可以被 planner 完全裁剪。

### 2.2 复合列顺序遵循"等值 → 范围"

教学上的标准规则：**先放等值过滤列，再放范围/排序列**。

`idx_memory_workspace_status_validity` 是典型示例：

```sql
CREATE INDEX idx_memory_workspace_status_validity
  ON memory_item(workspace_id, status, valid_from, valid_to);
```

- `workspace_id`（等值）+ `status`（等值）→ 走 B+ tree 直接定位到候选区间；
- `valid_from`, `valid_to`（时间区间）→ 在候选区间内做范围 scan。

如果顺序反过来（`valid_from` 先导），则任意"`status = 'active'`"查询都要全索引扫描。

### 2.3 DESC 顺序与排序消除

`audit_log`、`recall_log`、`timeline_entry` 等时间维度查询大量出现 `ORDER BY created_at DESC LIMIT N`。索引建立时显式标注 DESC：

```sql
idx_audit_workspace_time  ON audit_log(workspace_id, created_at DESC);
```

这样 EXPLAIN 显示为 `Index Scan` 而不是 `Sort`，是 B+ tree 索引的标准优化点。

---

## 3. GIN 倒排索引（全文检索）

`source_chunk.search_vector` 和 `memory_item.search_vector` 是 `tsvector` GENERATED ALWAYS 列。对它们建 GIN 索引：

```sql
CREATE INDEX idx_source_chunk_fts ON source_chunk USING GIN(search_vector);
CREATE INDEX idx_memory_fts       ON memory_item  USING GIN(search_vector);
```

**教学映射**：GIN（Generalized Inverted Index）是课堂讲的"倒排索引"的现代版——每个词项（term/lexeme）维护一个 posting list（pointing to rows）。`tsvector @@ tsquery` 直接走 GIN，比顺序扫描 + `ts_rank` 快多个数量级。

本项目召回主查询（`recall_service.py:124`）就走 `sc.search_vector @@ websearch_to_tsquery(...)`。

---

## 4. GIN trigram — 子串 / 模糊匹配

`pg_trgm` 扩展把任意字符串拆成 3-gram 集合，配合 GIN 即可索引 `ILIKE '%xxx%'` 这种**任意位置**子串匹配。

```sql
idx_source_chunk_text_trgm     ON source_chunk(chunk_text)     USING GIN(... gin_trgm_ops)
idx_memory_canonical_text_trgm ON memory_item(canonical_text)  USING GIN(... gin_trgm_ops)
idx_source_document_title_trgm ON source_document(title)       USING GIN(... gin_trgm_ops)
```

**为什么不是 B+ tree**：B+ tree 只能加速前缀匹配 `LIKE 'xxx%'`；中缀和后缀（`ILIKE '%xxx%'`）必须扫表。trigram + GIN 解决任意位置匹配，并且对短查询（≥ 3 字符）有非常好的 selectivity。

召回主查询里的 `mi.canonical_text ILIKE ANY(%(keyword_patterns)s::text[])` 分支走的就是 trigram 索引。

---

## 5. 现代索引补强（重点）

本节是本项目对索引设计的**主动加分项**：除了上面的经典索引，我们额外引入两类 PostgreSQL 专属的现代索引。

### 5.1 BRIN — Block Range Index

```sql
CREATE INDEX idx_audit_brin_time
  ON audit_log USING BRIN(created_at)
  WITH (pages_per_range = 32);
```

**问题背景**：`audit_log` 是只增不删（append-only）的日志表，按写入顺序天然有序于 `created_at`。如果只用 `idx_audit_workspace_time`（B+ tree, `workspace_id` 先导），跨租户的全库时间窗分析（如"全系统过去 24 小时的所有 `forget.execute` 事件"）需要扫描全 B+ tree。

**BRIN 工作原理**：把表按物理 page 分成"page range"（默认 128 页 = 1 MB，我们设为 32 页以适配 demo 数据量），每个 range 只保存 `(min_value, max_value)` 元组。查询时：

1. 查 BRIN 找出**有可能包含目标范围**的 page range；
2. 对这些 range 内的页做 bitmap heap scan。

**对比 B+ tree**：

|             | B+ tree on `(workspace_id, created_at)` | BRIN on `(created_at)` |
|---|---|---|
| 索引大小    | 每行一条索引条目                  | 每 32 页一条 min/max → 通常小 1-2 个数量级 |
| 写入开销    | 每次 INSERT 都更新叶子            | 几乎为零（只在 range 边界更新元组） |
| 查询适用    | "某 workspace 最近 N 条"          | "全库时间窗口分析" |
| 唯一性保证  | 可以做 unique index               | 不能 |

**教学价值**：BRIN 是**针对现代硬件（SSD）和数据布局（时间天然有序）**的现代索引设计。课程里讲索引时往往以"每行一条目"为隐含假设，BRIN 打破这个假设，是讲清楚"索引设计要看数据物理分布"的最佳案例。

**EXPLAIN 演示思路**：相同 audit 时间窗查询，分别 disable BRIN / B-tree 对比 buffer 数 + 执行时间。见 `docs/explain-analyze.md` 案例 #3。

### 5.2 Covering Index + INCLUDE — 实现 Index-Only Scan

```sql
CREATE INDEX idx_memory_active_ranking
  ON memory_item(workspace_id, importance DESC, updated_at DESC)
  INCLUDE (memory_id, memory_type, confidence, access_level)
  WHERE status = 'active';
```

这是一个三合一索引，同时演示三种现代 PostgreSQL 特性：

#### 5.2.1 Partial index — `WHERE status = 'active'`

只有 `status = 'active'` 的行进入索引。`memory_item` 随着使用增长会累积大量 `archived` / `forgotten` / `superseded` / `conflicted` 状态的旧记录，但绝大多数 hot path 查询只关心 active。

**收益**：索引大小随活跃率（active / total）线性缩小；索引扫描时不需要再过滤 status。

#### 5.2.2 Composite + DESC — 直接消除 Sort 节点

`(workspace_id, importance DESC, updated_at DESC)` 直接覆盖前端常用的"workspace 内活跃记忆按重要性 + 最近更新排序"。

执行 `WHERE workspace_id = ? AND status = 'active' ORDER BY importance DESC, updated_at DESC LIMIT N` 时，planner 直接拿索引顺序，无 Sort 节点。

#### 5.2.3 Covering (INCLUDE, PG 11+) — Index-only Scan

`INCLUDE (memory_id, memory_type, confidence, access_level)` 把这些**非 key 列**加入索引叶子节点（不参与排序、不参与去重判断），目的是让查询能完全用索引数据回答，不需要回表（heap fetch）。

**触发 index-only scan 的条件**：

1. 查询 SELECT 的列全部在索引中（key + INCLUDE 列）；
2. 涉及的页在 visibility map 中**全部"all visible"**（即近期没有未 VACUUM 的写入）；

满足时 EXPLAIN 显示 `Index Only Scan` + `Heap Fetches: 0`，IO 直接砍掉表数据访问。

**对比传统 B+ tree**：

|                | 普通 B-tree `(workspace_id, status)` | 本索引（partial + composite + covering） |
|---|---|---|
| 索引大小       | 全部行                                | 只有 active 行 → 大幅缩小 |
| ORDER BY 排序  | 需要 Sort 节点                        | 索引内已有序 |
| 列读取         | 必须回表读 memory_type / confidence   | INCLUDE 列直接从索引读 |
| 典型 EXPLAIN   | Bitmap Heap Scan + Sort               | Index Only Scan（Heap Fetches: 0） |

**教学价值**：Index-only scan 是 PostgreSQL（自 9.2 起）"现代查询执行"的标志特性之一，依赖 visibility map（PostgreSQL 8.4+ 引入的一种位图结构）。`INCLUDE` 是 PG 11 引入的 SQL:2003 标准语法。整套加起来体现"现代关系数据库对 IO 的极致优化"。

**EXPLAIN 演示思路**：同一个 dashboard 查询，对比 (a) 未建本索引 (b) 建了但未 VACUUM ANALYZE (c) 完整 VACUUM 后；三种情况下分别得到 Bitmap Heap Scan / Index Scan with Heap Fetches / Index Only Scan with Heap Fetches: 0。见 `docs/explain-analyze.md` 案例 #1。

---

## 6. Partial unique index — 软去重的 SQL 范例

```sql
CREATE UNIQUE INDEX idx_policy_global_unique
  ON access_policy(workspace_id, principal_type, resource_type, resource_scope, effect)
  WHERE principal_id IS NULL;
```

**为什么不能用普通 UNIQUE 约束**：`access_policy` 表的 `UNIQUE(workspace_id, principal_type, principal_id, resource_type, resource_scope, effect)` 在 `principal_id` 为 NULL 时**不会触发去重**（SQL 标准里 NULL ≠ NULL）。但业务上"全局策略"（principal_id 为 NULL，代表对所有 principal）必须唯一。

**解决**：partial unique index 配 `WHERE principal_id IS NULL`，把"全局策略"这部分行单独做去重，与"具体 principal 策略"互不干扰。

**教学价值**：Partial index 不是简单的优化，它还能**表达普通 UNIQUE 约束表达不了的语义**——是 SQL 标准约束体系的扩展。这个索引可以作为讲 partial index "约束维度"的范例。

---

## 7. Embedding metadata indexes — 向量缓存的工程化最小闭环

本轮 schema 新增了两张 embedding 缓存表：

```sql
memory_embedding
source_chunk_embedding
```

对应索引：

```sql
idx_memory_embedding_memory
idx_memory_embedding_workspace_model
idx_source_chunk_embedding_chunk
idx_source_chunk_embedding_workspace_model
```

它们不是 ANN 索引，而是**元数据定位索引**，解决的是：

- 某个 workspace 下是否已经为某 provider/model 生成过 embedding；
- 回填任务按 workspace + provider + model 扫描待处理记录；
- 从 memory / chunk 反查其 embedding 缓存；
- 去重约束之外，再给 backfill / health / debug 查询一条稳定路径。

当前项目把 embedding 存在 JSONB 里而不是 `pgvector`，因此索引重点不在"近邻搜索"，而在"缓存命中、批量回填、审计可查"。这和课程项目的现实目标一致：先把 agent-native retrieval 的数据闭环讲清楚，再决定是否引入额外扩展。

---

## 8. 索引设计的工程取舍

为了避免索引膨胀，本项目主动**不**做以下索引：

| 没做的索引 | 原因 |
|---|---|
| 单列 `created_at` btree（非时间分析表）   | 与 `(workspace_id, created_at DESC)` 复合索引重复 |
| `memory_item(memory_type)` 单列          | 与复合索引左前缀冲突；planner 不会主动用 |
| `audit_log(action_type)`                  | action_type 基数较低（< 100 种）+ 几乎总是与 workspace 一起过滤，不值得单独索引 |
| Hash index                                 | PG 上 hash index 历史上没有 WAL，10.0 才修复；大多场景 B-tree 已经够好 |
| pgvector / IVFFlat                         | 当前主线先用 JSONB embedding 缓存 + metadata btree，避免部署依赖；若后续数据规模上来，再考虑 ANN |

---

## 9. 与课程内容的对照

| 课程概念                  | 本项目对应                                     |
|---|---|
| B+ tree                  | 默认 btree（B-link 变种），见 §0 / §2          |
| 索引选择性 / 区分度       | partial index `WHERE status='active'`，§5.2.1  |
| 复合索引左前缀            | 几乎所有复合索引以 `workspace_id` 先导，§2.1    |
| 等值在前、范围在后         | `idx_memory_workspace_status_validity`，§2.2    |
| 排序索引 / 消除 Sort      | DESC 索引 + INCLUDE，§2.3、§5.2.2              |
| 倒排索引                  | GIN tsvector，§3                                |
| 模糊匹配的索引            | GIN trigram，§4                                 |
| 向量缓存的元数据索引       | embedding 表上的 btree，§7                      |
| 块级索引（page-level）    | BRIN，§5.1（教科书外的"现代"主题）              |
| Index-only scan / 覆盖索引 | INCLUDE + visibility map，§5.2.3              |
| 约束与索引的关系          | partial unique index，§6                        |

---

## 10. 参考

- PostgreSQL 文档：
  - Chapter 11 *Indexes* / Chapter 67 *B-Tree Indexes* / Chapter 70 *BRIN Indexes* / Chapter 71 *GIN Indexes*
  - `CREATE INDEX` 语法的 `INCLUDE` 子句（PG 11+）
- Lehman P.L. & Yao S.B. (1981) *Efficient Locking for Concurrent Operations on B-Trees*, ACM TODS 6(4).
- Pavlo A. (CMU 15-721) *Database Storage & Indexes* lecture notes（教学对照）
- 本项目相关文件：
  - `database/04_indexes.sql` — 索引定义
  - `docs/06-physical-design.md` §5 — 索引策略概览表
  - `docs/explain-analyze.md` — 配套 EXPLAIN ANALYZE 案例
