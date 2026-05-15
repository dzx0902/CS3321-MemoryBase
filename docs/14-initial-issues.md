# Initial GitHub Issues for MemoryBase

## Epic 1：项目初始化与 GitHub 规范

### Issue 1：初始化 MemoryBase 仓库结构
- 创建 README.md
- 创建 docs/
- 创建 database/
- 创建 backend/
- 创建 frontend/
- 创建 scripts/
- 创建 data/raw_sources/
- 创建 report/
- 添加 .gitignore
- 添加 .env.example

### Issue 2：编写 GitHub 协作规范
- 编写 CONTRIBUTING.md
- 编写 docs/12-github-workflow.md
- 添加 PR 模板
- 添加 Issue 模板
- 规定分支命名
- 规定 commit message 格式
- 规定 AI 使用说明

### Issue 3：配置基础 CI
- 添加 .github/workflows/ci.yml
- 检查 backend Python 依赖
- 检查 frontend build
- 检查 SQL 文件存在
- PR 时自动运行

## Epic 2：项目文档与课程报告基础

### Issue 4：编写项目总览文档
- 写清项目名称 MemoryBase
- 写清“文件—数据库双态长期记忆系统”定位
- 写清项目不是普通 RAG / 聊天助手
- 写清 P0 / P1 / P2 范围
- 写清演示闭环

### Issue 5：编写需求分析文档
- 定义普通用户、小组成员、Agent、管理员、访客
- 写功能需求表
- 写非功能需求
- 标注 P0 / P1 / P2
- 写项目边界和不做内容

### Issue 6：编写数据流图文档
- 画 0 层 DFD
- 画 1 层 DFD
- 画 Source 导入 2 层 DFD
- 画 Recall 检索 2 层 DFD
- 画 Wiki 导出 2 层 DFD

### Issue 7：编写 E-R 与逻辑设计文档
- 整理核心实体
- 整理实体联系与基数
- 绘制 Mermaid E-R 图
- 写 E-R 到关系模型转换
- 写 3NF 分析
- 说明允许的冗余字段

## Epic 3：数据库 SQL 基础

### Issue 8：实现核心用户与工作区表
- user_account
- workspace
- agent
- workspace_member

### Issue 9：实现 Source 与 Chunk 表
- agent_session
- message
- source_document
- source_chunk
- 全文检索字段

### Issue 10：实现 Memory、Evidence、Revision 表
- memory_item
- memory_revision
- memory_evidence

### Issue 11：实现 Wiki、Timeline、Recall、Audit 表
- wiki_page
- wiki_page_revision
- timeline_entry
- recall_log
- audit_log

### Issue 12：实现索引、视图与触发器
- indexes.sql
- v_active_memory
- v_memory_with_source
- v_project_timeline
- v_memory_statistics
- memory insert trigger

## Epic 4：后端 P0 闭环

### Issue 13：搭建 FastAPI 后端基础结构
- backend/app/main.py
- config.py
- database.py
- /api/health
- requirements.txt

### Issue 14：实现 Source 导入 API
- POST /api/sources
- GET /api/sources
- GET /api/sources/{id}
- chunker.py
- checksum
- 写入 source_document 和 source_chunk

### Issue 15：实现 Memory CRUD API
- POST /api/memories
- GET /api/memories
- GET /api/memories/{id}
- PATCH /api/memories/{id}
- DELETE /api/memories/{id} 使用软删除
- 创建 memory 时绑定 evidence

### Issue 16：实现 Recall 检索 API
- POST /api/recall
- 支持 query_text
- 查询 source_chunk 全文索引
- join memory_evidence 和 memory_item
- 写入 recall_log
- 返回 memory + evidence + source 信息

### Issue 17：实现 Wiki 导出 API
- POST /api/wiki/export
- 从 memory / scene 生成 markdown
- 写入 wiki_page
- 写入 wiki_page_revision
- 导出到 data/markdown_wiki/

## Epic 5：前端 P0 页面

### Issue 18：实现 Dashboard 页面
### Issue 19：实现 Source 页面
### Issue 20：实现 Memory 页面
### Issue 21：实现 Recall 页面
### Issue 22：实现 Wiki 与 Timeline 页面

## Epic 6：P1 / 冲高分功能

### Issue 23：实现 AccessPolicy 和 Agent 可见视图
### Issue 24：实现 ConflictRecord 页面与 SQL 查询
### Issue 25：准备演示数据与最终 Demo 脚本
