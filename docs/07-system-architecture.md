# 系统总体架构

## 1. 架构图

```text
User / Agent
  ↓
React Frontend
  ↓
FastAPI Backend
  ↓
Service Layer
  ↓
PostgreSQL
  ↓
Markdown Wiki Export
```

## 2. 模块划分

| 模块 | 职责 |
|---|---|
| Frontend | 页面展示、表单、搜索、Wiki 预览 |
| Backend API | 对外提供接口 |
| Source Service | 导入文档、切分 chunk |
| Memory Service | 创建、编辑、删除 memory |
| Recall Service | 检索与召回 |
| Policy Service | 权限过滤 |
| Audit Service | 审计日志 |
| Wiki Service | Markdown Wiki 导出 |
| Database | 保存 source、memory、evidence、revision、audit |

## 3. 后端目录

```text
backend/app/
  main.py
  core/
    config.py
    database.py
  services/
    ingest_service.py
    memory_service.py
    recall_service.py
    policy_service.py
    audit_service.py
    wiki_service.py
  routers/
    sources.py
    memories.py
    recall.py
    wiki.py
    audit.py
```

## 4. 前端页面

```text
Dashboard
Sources
Memories
Recall
Wiki
Timeline
Audit
Conflicts
```
