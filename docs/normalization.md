# 范式分析（Normalization Analysis）

本文档对 MemoryBase 数据库的核心表做函数依赖（FD）分析和 3NF / BCNF 验证，并明确说明**主动不进一步规范化的工程取舍**及其依据。

配套阅读：
- `database/01_schema_core.sql` / `02_schema_memory.sql` / `03_schema_governance.sql` — 表定义
- `docs/04-er-design.md` — ER 设计与关系映射
- `docs/05-logical-design.md` — 逻辑设计

## 0. 范式回顾（教学对照）

| 范式 | 必要条件 |
|---|---|
| 1NF | 属性原子（atomic），无重复组（repeating group） |
| 2NF | 满足 1NF，且**非主属性完全函数依赖于候选键**（消除部分依赖） |
| 3NF | 满足 2NF，且**非主属性不传递依赖于候选键**（消除传递依赖） |
| BCNF | 满足 3NF，且**任何函数依赖 X→Y 中 X 必为超键** |

本项目目标：**核心业务表以 3NF / BCNF 为主**；少数表（`memory_item` / `source_chunk` / `wiki_page`）出于查询性能 / trigger 审计 / dirty-bit 缓存的需要，对**派生属性**做了**受控反规范化**——已在 §1.4 / §1.6 / §1.9 显式标注 ⚠，并通过 `GENERATED ALWAYS AS ... STORED` 或 trigger 自动维护一致性（详见 §5）。严格 3NF 视角下这些是已知偏离；BCNF / 业务建模视角下不构成冗余，详见各表分析。汇总表 §2 给出每张表的范式判定。

---

## 1. 核心表函数依赖与范式判定

### 1.1 `user_account`（用户）

```
user_id     → username, display_name, email, role_hint, created_at, updated_at
username    → user_id (UNIQUE)
email       → user_id (UNIQUE)
```

- **候选键**：`{user_id}`、`{username}`、`{email}`（后两个为 UNIQUE 约束）。
- **2NF**：候选键均为单属性，自动满足。
- **3NF**：所有非主属性直接依赖 `user_id`，无传递依赖。
- **BCNF**：所有 FD 左侧（`user_id`、`username`、`email`）均为候选键 → 满足。

### 1.2 `workspace`（工作区）

```
workspace_id → slug, name, description, scope_type, owner_user_id, created_at, updated_at
slug         → workspace_id (UNIQUE)
```

- **候选键**：`{workspace_id}`、`{slug}`。
- **BCNF**：所有 FD 左侧均为候选键 → 满足。

### 1.3 `agent`（智能体）

```
agent_id              → workspace_id, name, agent_type, status, owner_user_id, created_at
(workspace_id, name)  → agent_id (UNIQUE within workspace)
```

- **候选键**：`{agent_id}`、`{workspace_id, name}`。
- **BCNF**：FD 左侧（`agent_id`、`(workspace_id, name)`）均为候选键 → 满足。

### 1.4 `memory_item`（记忆主表）

```
memory_id → workspace_id, memory_type, canonical_text, summary, search_text_zh, search_vector,
            confidence, importance, status, access_level, owner_user_id, owner_agent_id,
            valid_from, valid_to, superseded_by_memory_id, current_revision_no,
            created_at, updated_at, created_from_doc_id
(memory_id, workspace_id) → ...（UNIQUE，等价于 memory_id 单决定，但用于复合 FK 见 §3）
```

- **候选键**：`{memory_id}`。
- **超键 / 复合唯一键**：`{memory_id, workspace_id}` 由 `UNIQUE(memory_id, workspace_id)` 保证，主要服务于 §3 的复合 FK；它不是候选键，因为真子集 `{memory_id}` 已可唯一决定整行。
- **2NF**：主键为单属性，自动满足。
- **严格 3NF 视角**：见下方 ⚠，因 `search_vector` / `current_revision_no` 为派生属性，不严格满足。
- **工程/物理设计视角**：除受控派生列外，其余业务属性均由 `memory_id` 直接决定；偏离部分由 GENERATED / trigger 自动维护。

当前枚举设计（需与 API / 前端 /治理流程保持一致）：

```text
memory_type:
- episodic
- semantic
- fact
- profile
- procedural
- decision
- preference
- task
- risk
- constraint
- policy
- summary

status:
- candidate
- active
- archived
- forgotten
- superseded
- rejected
- conflicted
```

#### ⚠ 主动违反 3NF 的两处（已识别）：

1. **`search_vector` 是 `search_text_zh` 的派生属性**：

   ```
   memory_id → search_text_zh → search_vector
   ```

   严格按 3NF 判定，`memory_id → search_vector` 是经过 `search_text_zh` 的传递依赖。

   **工程理由**：`search_vector` 是 `tsvector` 类型，由 `to_tsvector('simple', search_text_zh)` 计算得到，用于支撑 GIN 全文索引（详见 `docs/index-rationale.md` §3）。每次查询时重算代价过大。

   **补偿措施**：使用 `GENERATED ALWAYS AS ... STORED`（PG 12+）由数据库自动维护，**不允许应用层直接写入**。从用户语义看，`search_vector` 不是独立属性，而是 `search_text_zh` 的"索引投影"，本质是物理优化。

2. **`current_revision_no` 是 `memory_revision` 的聚合**：

   ```
   memory_id → current_revision_no   （= MAX(revision_no) FROM memory_revision WHERE memory_id = ...）
   ```

   严格按 3NF 判定，`current_revision_no` 是冗余的派生数据。

   **工程理由**：消除每次读取 memory 时对 `memory_revision` 的 MAX 聚合。该值在 trigger `trg_memory_after_update` 中维护。

   **补偿措施**：`trg_memory_before_update` 先在同一事务内递增
   `current_revision_no`，`trg_memory_after_update` 再写入 `memory_revision`
   和 `audit_log`。应用层只读不直接维护该字段。代价是 trigger 必须正确，
   **已在 `tests/test_governance.py` 覆盖**。

### 1.5 `memory_revision`（记忆历史版本）

```
(memory_id, revision_no) → revision_text, revision_summary, revision_reason,
                            editor_type, editor_id, created_at
```

- **候选键**：`{memory_id, revision_no}`（PK）。
- **3NF / BCNF**：所有 FD 左侧均为候选键 → 满足。
- **设计要点**：复合 PK 是版本化表的标准模式，避免单独的 `revision_id` 代理键带来无意义的全局唯一性。

### 1.6 `source_chunk`（源文档切片）

```
chunk_id              → doc_id, chunk_no, chunk_text, start_line, end_line,
                         token_count, search_text_zh, search_vector
(doc_id, chunk_no)    → chunk_id (UNIQUE)
```

- **候选键**：`{chunk_id}`、`{doc_id, chunk_no}`。
- **严格 3NF 视角**：因 `search_vector` 为派生属性，不严格满足（同 §1.4 ⚠1）。
- **工程/物理设计视角**：其余业务属性满足 BCNF；`search_vector` 属索引投影式反规范化。

### 1.7 `memory_evidence`（记忆 ↔ chunk 多对多）

```
evidence_id                            → memory_id, chunk_id, evidence_role, weight, note, created_at
(memory_id, chunk_id, evidence_role)   → evidence_id (UNIQUE)
```

- **候选键**：`{evidence_id}`、`{memory_id, chunk_id, evidence_role}`。
- **BCNF**：满足。
- **设计要点**：本表是 M:N 关联表。复合 UNIQUE `(memory_id, chunk_id, evidence_role)` 允许同一对 (memory, chunk) 有多种角色（supports / refutes / context / source），而不是默认 PK。

### 1.8 `memory_embedding` / `source_chunk_embedding`（向量缓存表）

`memory_embedding`：

```
embedding_id → memory_id, workspace_id, provider, model, dimension,
               embedding_json, embedding_text_hash, created_at
(memory_id, provider, model, embedding_text_hash) → embedding_id (UNIQUE)
```

`source_chunk_embedding`：

```
embedding_id → chunk_id, doc_id, workspace_id, provider, model, dimension,
               embedding_json, embedding_text_hash, created_at
(chunk_id, provider, model, embedding_text_hash) → embedding_id (UNIQUE)
```

- **候选键**：`{embedding_id}`，以及各自的 UNIQUE 组合。
- **3NF / BCNF**：满足。`provider`、`model`、`embedding_text_hash` 与 `embedding_json` 一起描述一次特定文本在特定模型下的嵌入产物，不存在非键属性之间的业务传递依赖。
- **JSONB 字段的范式定位**：`embedding_json` 存的是定长数值向量的整体序列化结果。这里不把每一维拆成单独列，是因为这些维度不作为关系型属性参与业务约束或 join；在 1NF 视角下，它是单个原子值。
- **工程取舍**：项目当前用 JSONB 缓存 embedding，而不是 `pgvector` 扩展。这样做的收益是部署简单、课程演示成本低；代价是向量相似度更偏中小规模数据处理，不追求大规模 ANN 检索性能。

### 1.9 `memory_entity` / `memory_scene_cell`（多 FK 复合表）

```
(memory_id, entity_id, relation_role) → workspace_id, created_at         [memory_entity]
(scene_id, memory_id)                  → workspace_id, cell_role, sort_order, note, created_at  [memory_scene_cell]
```

- **候选键**：均为复合 PK。
- **BCNF**：满足。
- **特殊设计**：表内 `workspace_id` 是**为了支持复合 FK 而冗余存储**（详见 §3）。

### 1.10 `wiki_page` + `wiki_page_revision`

```
page_id              → workspace_id, page_slug, page_type, title, current_revision_no,
                        generated_from_scene_id, generated_from_memory_id, needs_rebuild,
                        status, forgotten_at, created_at, updated_at
(workspace_id, page_slug) → page_id (UNIQUE)

(page_id, revision_no) → frontmatter_json, body_markdown, generated_by, created_at
```

- **`wiki_page_revision`**：候选键为 `{page_id, revision_no}`，严格 3NF / BCNF 均满足。
- **`wiki_page` 严格 3NF 视角**：因 `current_revision_no` / `needs_rebuild` 为派生属性，不严格满足。
- **`wiki_page` 工程/物理设计视角**：除这两个受控缓存列外，其余业务属性满足 BCNF。
- **`current_revision_no` 派生**：同 §1.4 ⚠2，trigger `trg_wiki_revision_after_insert` 维护。
- **`needs_rebuild` 派生**：技术上是基于"是否有 memory/scene 自上次 build 后变更"的派生标志，但作为 dirty bit 缓存，由 `trg_memory_after_update` 维护。
- **`frontmatter_json` 与 `body_markdown` 分两列**：前者是结构化元数据（JSONB），后者是非结构化正文（TEXT），属性各自原子，**未违反 1NF**。

### 1.11 `access_policy`（访问策略）

```
policy_id → workspace_id, principal_type, principal_id, resource_type, resource_scope, effect, predicate_json, created_at
(workspace_id, principal_type, principal_id, resource_type, resource_scope, effect) → policy_id   [UNIQUE 约束]
```

- **候选键**：`{policy_id}`、上述 6-列 UNIQUE 组合。
- **3NF / BCNF**：满足。
- **特殊设计**：表级 UNIQUE 对 `principal_id IS NULL`（全局策略）失效，所以加了 partial UNIQUE index `WHERE principal_id IS NULL`（详见 `docs/index-rationale.md` §6）。**这本质是 SQL 标准下 UNIQUE 约束的语义补强，不是范式问题**。

### 1.12 `audit_log` / `recall_log`（带 JSONB 的日志表）

```
audit_id  → workspace_id, actor_type, actor_id, action_type, target_type, target_id,
             before_json, after_json, created_at
recall_id → workspace_id, agent_id, user_id, query_text, filter_json, result_count,
             top_memory_ids_json, context_pack_json, created_at
```

- **候选键**：`{audit_id}` / `{recall_id}`。
- **BCNF**：所有 FD 左侧均为候选键 → 满足。
- **JSONB 字段的范式定位**：详见 §4。

### 1.13 `conflict_record`（冲突记录）

```
conflict_id            → workspace_id, left_memory_id, right_memory_id, conflict_type, status,
                          resolution_note, resolved_by_actor_type, resolved_by_actor_id,
                          resolved_at, created_at, updated_at
(left_memory_id, right_memory_id) → conflict_id  [UNIQUE]
```

- **候选键**：`{conflict_id}`、`{left_memory_id, right_memory_id}`。
- **BCNF**：满足。
- **CHECK 约束 `left_memory_id < right_memory_id`**：保证 `(A,B)` 和 `(B,A)` 不会被记成两条，**这是范式之外的语义约束**，等价于"无序对"建模。

---

## 2. 3NF / BCNF 总结

| 表 | 1NF | 2NF | 3NF | BCNF | 备注 |
|---|---|---|---|---|---|
| user_account            | ✅ | ✅ | ✅ | ✅ | |
| workspace               | ✅ | ✅ | ✅ | ✅ | |
| agent                   | ✅ | ✅ | ✅ | ✅ | |
| workspace_member        | ✅ | ✅ | ✅ | ✅ | 复合 PK |
| agent_session / message | ✅ | ✅ | ✅ | ✅ | |
| source_document         | ✅ | ✅ | ✅ | ✅ | |
| source_chunk            | ✅ | ✅ | ⚠ | ✅\* | search_vector 派生，见 §1.4 ⚠1 |
| **memory_item**         | ✅ | ✅ | ⚠ | ✅\* | search_vector + current_revision_no 派生 |
| memory_revision         | ✅ | ✅ | ✅ | ✅ | 复合 PK |
| memory_evidence         | ✅ | ✅ | ✅ | ✅ | M:N |
| memory_embedding        | ✅ | ✅ | ✅ | ✅ | JSONB 向量缓存，避免 pgvector 依赖 |
| source_chunk_embedding  | ✅ | ✅ | ✅ | ✅ | JSONB 向量缓存，避免 pgvector 依赖 |
| entity / memory_entity  | ✅ | ✅ | ✅ | ✅ | 复合 PK + 复合 FK |
| memory_scene / cell     | ✅ | ✅ | ✅ | ✅ | 复合 PK + 复合 FK |
| timeline_entry          | ✅ | ✅ | ✅ | ✅ | |
| wiki_page               | ✅ | ✅ | ⚠ | ✅\* | current_revision_no + needs_rebuild 派生 |
| wiki_page_revision      | ✅ | ✅ | ✅ | ✅ | 复合 PK |
| access_policy           | ✅ | ✅ | ✅ | ✅ | partial unique 补强 |
| audit_log / recall_log  | ✅ | ✅ | ✅ | ✅ | JSONB 见 §4 |
| forget_request          | ✅ | ✅ | ✅ | ✅ | |
| conflict_record         | ✅ | ✅ | ✅ | ✅ | 复合 UNIQUE + CHECK 序约束 |

\* 标记 ✅\* 的表：**严格 3NF 不满足**（派生属性导致传递依赖），但属于**经识别、有据可循、有 trigger/GENERATED 自动维护**的主动反规范化。详见 §1.4 ⚠ 与 §4。

---

## 3. 复合主键 + 复合外键：多租户完整性

本项目大量使用一种特殊设计：**M:N 关联表内冗余存储 `workspace_id`，配合复合 FK 引用主表的 `(主键, workspace_id)`**。例如：

```sql
-- memory_item 表
CREATE TABLE memory_item (
  memory_id    UUID PRIMARY KEY,
  workspace_id UUID NOT NULL,
  ...
  UNIQUE(memory_id, workspace_id)
);

-- memory_entity 关联表
CREATE TABLE memory_entity (
  memory_id    UUID NOT NULL,
  entity_id    UUID NOT NULL,
  workspace_id UUID NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
  relation_role VARCHAR(40) NOT NULL DEFAULT 'about',
  PRIMARY KEY (memory_id, entity_id, relation_role),
  FOREIGN KEY (memory_id, workspace_id)
    REFERENCES memory_item(memory_id, workspace_id) ON DELETE CASCADE,
  FOREIGN KEY (entity_id, workspace_id)
    REFERENCES entity(entity_id, workspace_id) ON DELETE CASCADE
);
```

### 3.1 范式视角

`memory_entity.workspace_id` 严格说是**冗余**——它可以通过 `memory_id → workspace_id`（来自 `memory_item`）推导得出，技术上违反 3NF（传递依赖）。

### 3.2 工程理由（必须这么做）

**这条冗余是 SQL 表达"跨表多租户完整性"的唯一手段**：

- 普通 FK `(memory_id) REFERENCES memory_item(memory_id)` 只能保证 memory 存在；
- 但如果两个不同 workspace 的 memory 和 entity 被错误关联（`memory.workspace_id ≠ entity.workspace_id`），普通 FK **无法检测**；
- **复合 FK 强制要求 `memory_entity.workspace_id` 同时存在于 `memory_item` 和 `entity` 的 `(*_id, workspace_id)` UNIQUE 中** → 数据库层硬性保证三方 workspace 一致。

### 3.3 替代方案对比

| 方案 | 完整性 | 性能 | 代码复杂度 |
|---|---|---|---|
| 普通单 FK | ❌ 跨租户关联无防御 | 索引最小 | 应用层补 check |
| 触发器 check | ✅ | trigger 开销 | 中等 |
| **复合 FK（本项目）** | ✅ | 索引略大 | 0 |
| 行级安全（RLS） | ✅ | RLS 评估开销 | 中等 |

**本项目选复合 FK** 因为：(a) 完整性由 DBMS 保证；(b) 不需要 trigger 也能享受；(c) 应用层 0 改动。冗余 `workspace_id` 列的存储成本（16 bytes/UUID × 行数）远低于完整性失效的代价。

### 3.4 范式判定的修正

**严格 3NF 视角**：`memory_entity.workspace_id` 是冗余 → 违反 3NF。
**Boyce-Codd 视角 + 业务建模视角**：把 `workspace_id` 视为 `memory_entity` 自己的**实体身份的一部分**（"这个关联属于哪个 workspace"），而不是从其他表派生 → 没有冗余，BCNF 满足。

这两个视角的差别在于**怎么解读 `workspace_id` 的语义角色**。本项目采用后者：把多租户隔离视为 first-class 设计目标，所有跨表关联的 workspace_id 都是关联本身的属性，不是冗余。

---

## 4. JSONB 字段的范式定位

`audit_log.before_json` / `audit_log.after_json` / `recall_log.filter_json` / `recall_log.top_memory_ids_json` / `recall_log.context_pack_json` / `access_policy.predicate_json` / `wiki_page_revision.frontmatter_json` 等字段使用 PostgreSQL 的 JSONB 类型。

### 4.1 严格 1NF 视角

JSON 文档内有嵌套结构 → 严格按 Codd 的 1NF "属性原子" → **违反 1NF**（这也是为什么有 "NF² / 非第一范式" 之争）。

### 4.2 现代关系数据库视角（PostgreSQL / SQL:2016）

SQL:2016 标准引入 JSON 数据类型，将 JSONB 视为**一个原子的"半结构化文档值"**（atomic JSON document），其内部结构由 JSON path 语法（`jsonb_path_*`、`->`、`->>`、`@>` 等）访问，但从关系层看仍是单值属性。

按这个解读，所有 JSONB 字段满足 1NF。

### 4.3 本项目的使用准则

每个 JSONB 字段都有明确的语义角色，**不是"懒得设计 schema"的兜底**：

| 字段 | 语义 | 不能展开成表的原因 |
|---|---|---|
| `audit_log.before_json` / `after_json` | 写操作前后的**完整记录快照** | 跨多个表、且要在 schema 演进后仍可读旧快照 → 必须是 JSON 快照而非动态 FK |
| `recall_log.filter_json` | 召回查询的过滤参数 | 参数 schema 随召回 API 演化，结构化建模代价过大 |
| `recall_log.top_memory_ids_json` | 召回结果的 memory_id 列表 | 是"该次召回时的快照"，不是"memory 列表的实时关联" |
| `recall_log.context_pack_json` | 召回返回的完整 context pack | 嵌套深、字段多变、只用于日志回放 |
| `access_policy.predicate_json` | 策略附加判定条件 | 条件 DSL 灵活，未来可能扩展 |
| `wiki_page_revision.frontmatter_json` | Markdown 文章 frontmatter | 标准做法：frontmatter 即任意 key-value |

### 4.4 不滥用的边界

**业务实体**（memory_item / source_document / entity / wiki_page 等）的核心属性**全部使用强类型列**，不塞进 JSONB。JSONB 只用于：
- 历史快照（before_json/after_json）
- 调用参数 / 返回包（filter_json / context_pack_json）
- 用户自定义 / 第三方 schema（frontmatter_json / predicate_json）

这种**"业务核心强 schema + 边缘场景 JSONB"** 的混合范式，是现代 PG 生产数据库的标准实践，对应课程"NoSQL 与 SQL 融合"的现代主题。

---

## 5. 派生数据 / 反规范化的统一管理

本项目所有**主动反规范化**的数据均通过下列机制之一保持一致性：

| 派生字段 | 维护机制 | 一致性保证 |
|---|---|---|
| `memory_item.search_vector` / `source_chunk.search_vector` | `GENERATED ALWAYS AS (...) STORED` | DBMS 强制，应用层无法直接写 |
| `memory_item.current_revision_no` | trigger `trg_memory_before_update` 递增，`trg_memory_after_update` 写 revision/audit | trigger 单事务原子更新 |
| `wiki_page.current_revision_no` | trigger `trg_wiki_revision_after_insert` | 同上 |
| `wiki_page.needs_rebuild` | trigger `trg_memory_after_update` | dirty bit 设置；rebuild 时清零 |
| `memory_entity.workspace_id` / `memory_scene_cell.workspace_id` | 应用层显式写入 + 复合 FK 校验 | DBMS 复合 FK 拒绝跨租户引用 |

**统一原则**：派生数据不允许应用层"两写"（业务表 + 派生表分别写），必须通过 GENERATED / trigger / FK 自动维护，由 DBMS 而不是业务代码保证一致性。

---

## 6. 与课程内容的对照

| 课程概念 | 本项目对应 |
|---|---|
| 1NF 属性原子 | 所有列单值；JSONB 按 SQL:2016 视为原子文档（§4） |
| 2NF 完全函数依赖 | 候选键多为单列；少数复合 PK 也已检查非主属性完全依赖 |
| 3NF 消除传递依赖 | 核心表满足；`memory_item` / `source_chunk` / `wiki_page` 三表存在派生属性（search_vector / current_revision_no / needs_rebuild），属于受控反规范化，由 GENERATED / trigger 自动维护（§1.4 / §1.6 / §1.9 / §5） |
| BCNF 全 FD 左侧为超键 | 主体满足；含派生属性的 3 张表在严格 3NF 视角是偏离，BCNF / 业务建模视角不构成冗余，详见汇总表 §2 |
| 候选键 / 主键选择 | 业务表用 UUID 代理键 + 业务字段 UNIQUE；M:N 表用复合自然键 PK（§1.5 / §1.7 / §1.8） |
| 外键参照完整性 | 所有跨表引用使用 FK + ON DELETE 策略；多租户跨表用复合 FK（§3） |
| 反规范化与一致性 | 派生字段统一通过 GENERATED / trigger 维护（§5）；不允许应用层多写 |
| NF² / NoSQL 内嵌 | JSONB 用于历史快照 / 调用参数 / 用户扩展（§4） |

---

## 7. 参考

- Codd E.F. (1970) *A Relational Model of Data for Large Shared Data Banks*
- PostgreSQL 文档：Chapter 8.14 *JSON Types* / Chapter 11 *Indexes* / Chapter 5.4 *Constraints*
- SQL:2016 标准的 JSON 部分
- 本项目相关文件：
  - `database/01_schema_core.sql` / `02_schema_memory.sql` / `03_schema_governance.sql`
  - `database/06_triggers.sql` — 派生字段维护 trigger
  - `docs/04-er-design.md` / `docs/05-logical-design.md` — 逻辑设计
  - `docs/index-rationale.md` — 索引选型（包含 partial unique index 对 access_policy 的补强）
