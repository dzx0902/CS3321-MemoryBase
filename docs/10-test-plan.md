# 测试计划

## 1. Source 导入测试

| 用例 | 输入 | 预期结果 |
|---|---|---|
| 导入 Markdown | discussion_01.md | 生成 SourceDocument |
| 自动切分 chunk | 100 行文本 | 生成多个 SourceChunk |
| 重复导入 | 相同 checksum | 阻止重复或提示 |

## 2. Memory 测试

| 用例 | 输入 | 预期结果 |
|---|---|---|
| 创建 memory | canonical_text + chunk_id | 生成 MemoryItem 和 MemoryEvidence |
| 修改 memory | 新文本 | 生成新 MemoryRevision |
| 删除 memory | memory_id | status 改为 archived |

## 3. Recall 测试

| 用例 | 输入 | 预期结果 |
|---|---|---|
| 关键词检索 | “校园食堂系统” | 返回相关 memory |
| evidence 追溯 | memory_id | 返回 source chunk |
| 权限过滤 | project-only agent | 不返回 private memory |

## 4. Wiki 测试

| 用例 | 输入 | 预期结果 |
|---|---|---|
| 导出 Wiki | workspace_id | 生成 markdown 文件 |
| 版本记录 | 重复导出 | 生成 WikiPageRevision |

## 5. Audit 测试

| 用例 | 操作 | 预期结果 |
|---|---|---|
| 创建 memory | insert | audit_log 有记录 |
| 修改 memory | update | audit_log 有 before/after |
| 删除 memory | delete | audit_log 有 soft_delete |
