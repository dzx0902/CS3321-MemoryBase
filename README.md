# MemoryBase

MemoryBase 是一个面向 AI Agent 协作研发场景的文件—数据库双态长期记忆系统。

系统将 Markdown、会议纪要、讨论记录等人类可读文件导入数据库，切分为 SourceChunk，并进一步整理为可检索、可追溯、可权限控制、可审计、可版本化的 MemoryItem，最终导出为 Markdown Wiki。

## 项目定位

MemoryBase 不是普通聊天助手，也不是简单 RAG 知识库，而是一个以数据库为核心的长期记忆治理系统。

核心链路：

```text
SourceDocument
  → SourceChunk
  → MemoryItem
  → MemoryEvidence
  → MemoryRevision / AuditLog
  → RecallLog / AccessPolicy
  → WikiPage / WikiPageRevision
```

## 技术栈

- Backend: FastAPI
- Frontend: React + Vite
- Database: PostgreSQL
- Search: PostgreSQL Full Text Search
- SQL: views, triggers, indexes
- Deployment: Docker Compose

## P0 MVP

- SourceDocument / SourceChunk
- MemoryItem / MemoryEvidence
- MemoryRevision / AuditLog
- RecallLog
- WikiPage / WikiPageRevision
- TimelineEntry
- Dashboard / Source / Memory / Recall / Wiki 页面

## 本地运行

```bash
docker compose up -d

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

cd frontend
npm install
npm run dev
```

## 部署指南

### 1. 推荐方式：Docker 启动 PostgreSQL

如果你只想最快跑通数据库，直接在项目根目录执行：

```bash
docker compose up -d
```

这会启动项目自带的 PostgreSQL 服务，默认连接信息见 `.env.example`。

### 2. 一条命令安装大部分依赖

如果本机已经安装了 `Python`、`Node.js` 和 `PostgreSQL`，可以用下面的一条命令完成大部分依赖安装：

```bash
pip install -r backend/requirements.txt && cd frontend && npm install --include=dev
```

Windows PowerShell 下建议分两步执行，避免 shell 差异：

```powershell
pip install -r backend/requirements.txt
Set-Location frontend
npm install --include=dev
```

### 3. 前后端启动

后端：

```bash
cd backend
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm run dev
```

### 4. 数据库初始化

数据库启动后，可以优先直接用仓库内置快捷命令：

```bash
npm run db:init
npm run db:seed
npm run db:check
```

常用命令说明：

- `npm run db:init`：执行 `00_init.sql` 到 `06_triggers.sql`
- `npm run db:seed`：执行 `07_seed.sql` 和 `08_demo_queries.sql`
- `npm run db:reset`：重建 `public schema` 后重新执行初始化和 seed
- `npm run db:check`：检查核心表与 demo 数据
- `npm run db:setup`：等价于 `db:reset`

这些命令由跨平台的 `python scripts/db_cli.py` 统一驱动。
会优先读取当前终端的 `DATABASE_URL`，如果没设置，则自动读取项目根目录 `.env`，若 `.env` 不存在则回退读取 `.env.example`。

如果你暂时不想用快捷命令，也可以继续按顺序手动执行：

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

PowerShell 可直接写成：

```powershell
psql $env:DATABASE_URL -f database/00_init.sql
psql $env:DATABASE_URL -f database/01_schema_core.sql
psql $env:DATABASE_URL -f database/02_schema_memory.sql
psql $env:DATABASE_URL -f database/03_schema_governance.sql
psql $env:DATABASE_URL -f database/04_indexes.sql
psql $env:DATABASE_URL -f database/05_views.sql
psql $env:DATABASE_URL -f database/06_triggers.sql
psql $env:DATABASE_URL -f database/07_seed.sql
```

如果使用快捷命令，确保本机 `python` 与 `psql` 都在 PATH 中，并在项目根目录执行：

```bash
npm run db:init
```

## PostgreSQL 本机安装指南

### 1. 安装方式

如果不使用 Docker，可以直接在本机安装 PostgreSQL：

- Windows：下载安装官方安装器，安装 PostgreSQL 与 `psql`
- macOS：可用 Homebrew 安装
- Linux：可用系统包管理器安装

### 2. Windows 安装建议

安装完成后，建议：

- 记住超级用户密码
- 勾选命令行工具 `psql`
- 将 PostgreSQL 的 `bin` 目录加入系统 PATH

安装完成后可验证：

```powershell
psql --version
```

### 3. 创建本地数据库

安装 PostgreSQL 后，创建项目数据库与用户：

```sql
CREATE USER memorybase WITH PASSWORD 'memorybase';
CREATE DATABASE memorybase_db OWNER memorybase;
GRANT ALL PRIVILEGES ON DATABASE memorybase_db TO memorybase;
```

### 4. 配置环境变量

`.env.example` 是示例模板，不会被程序自动当作运行配置读取。实际使用时，应该在项目根目录复制一份并命名为 `.env`：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

然后再根据你自己的本机环境修改 `.env`。如果你本地 PostgreSQL 的用户名、密码、端口、数据库名和示例完全一致，可以直接使用；如果不一致，就需要修改 `DATABASE_URL`。

项目默认示例：

```env
DATABASE_URL=postgresql://memorybase:memorybase@localhost:5432/memorybase_db
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

常见需要修改的地方：

- 用户名不是 `memorybase`
- 密码不是 `memorybase`
- PostgreSQL 端口不是 `5432`
- 数据库名不是 `memorybase_db`
- 后端或前端端口与你本机已有服务冲突

例如，如果你的本机 PostgreSQL 用户是 `postgres`，密码是 `123456`，数据库名是 `memorybase`，那么 `.env` 可以改成：

```env
DATABASE_URL=postgresql://postgres:123456@localhost:5432/memorybase
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

如果你使用 Docker Compose 启动仓库内自带的 PostgreSQL，并且没有改默认配置，那么通常可以直接沿用示例值，不需要改动。

### 5. 验证连接

```powershell
psql postgresql://memorybase:memorybase@localhost:5432/memorybase_db -c "\dt"
```

或者直接使用：

```bash
npm run db:check
```

## 文档目录

- docs/00-project-overview\.md
- docs/01-requirements.md
- docs/02-data-flow\.md
- docs/03-data-dictionary.md
- docs/04-er-design.md
- docs/05-logical-design.md
- docs/06-physical-design.md
- docs/07-system-architecture.md
- docs/08-api-design.md
- docs/09-module-ipo.md
- docs/10-test-plan.md
- docs/11-demo-script.md
- docs/12-github-workflow\.md
- docs/13-final-report-outline.md

## GitHub Workflows

- `.github/workflows/ci.yml`
  - `push` 到 `main/dev` 时执行主线持续集成
  - 包含基础文件检查、Python/Frontend 静态检查、后端 smoke test
- `.github/workflows/pr-build-check.yml`
  - `pull_request` 到 `main/dev` 时执行 PR 构建校验
  - 包含基础文件检查、静态检查、后端检查、前端构建
- `.github/workflows/sql-check.yml`
  - 针对 `database/` 目录相关变更执行 PostgreSQL SQL 检查
  - 包含建库、建表、索引、视图、触发器加载与烟雾测试
- `.github/workflows/pages.yml`
  - `main` 分支触发 GitHub Pages 前端静态站点部署
- `.github/workflows/codeql.yml`
  - 可选安全扫描工作流
  - 对 `Python` 与 `JavaScript` 进行 CodeQL 分析

## Demo 数据

- 原始讨论记录位于 `data/raw_sources/demo_workspace/`
- 可使用 `scripts/import_demo_sources.py` 列出当前 demo 源文件
