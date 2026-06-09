# 一键启动与 Docker 部署

AI Fiction Studio 支持三种启动方式：

1. 本地开发启动。
2. Docker Compose 单机 SQLite 版。
3. Docker Compose PostgreSQL 版。

SQLite 与 PostgreSQL 的详细差异、选择建议、备份恢复和迁移说明见：

```text
docs/database.md
```

## 数据库是否会自动创建

会。

后端启动时会执行 FastAPI lifespan：

```text
backend/app/main.py
```

启动流程：

1. 导入所有 SQLAlchemy models。
2. 执行 `Base.metadata.create_all()`。
3. 执行版本化 schema migration，记录到 `schema_migrations`。
4. Seed 默认管理员账号。
5. Seed 默认模型供应商。
6. 恢复中断任务状态。

所以第一次启动时，如果数据库文件不存在，会自动建表；如果是旧数据库，会按 migration 版本做非破坏性升级。

默认账号：

```text
邮箱：admin@aifiction.com
密码：admin123
```

生产环境必须修改默认密码和 `JWT_SECRET_KEY`。

## 数据库接入方式

数据库通过环境变量选择：

```env
DATABASE_URL=sqlite+aiosqlite:///./aifiction.db
```

当前支持：

### SQLite

本地默认：

```env
DATABASE_URL=sqlite+aiosqlite:///./aifiction.db
```

Docker 默认：

```env
DATABASE_URL=sqlite+aiosqlite:////data/aifiction.db
```

SQLite 启动时会自动设置：

- `PRAGMA foreign_keys = ON`
- `PRAGMA journal_mode = WAL`
- `PRAGMA busy_timeout = 30000`

适合：

- 本地开发。
- 单人写作。
- 快速体验。
- 小规模私有部署。

### PostgreSQL

PostgreSQL 示例：

```env
DATABASE_URL=postgresql+asyncpg://aifiction:aifiction@postgres:5432/aifiction
```

适合：

- 多人使用。
- 长期部署。
- 数据规模较大。
- 后续接入外部任务队列。

注意：当前项目启动时会先 `create_all()` 初始化新库，再执行版本化 schema migration。公开部署升级前请备份数据库；迁移策略要求只追加结构或补索引，不自动重写用户已有小说内容。

## 版本升级

从旧版本升级到新版本时建议按这个顺序操作：

1. 停止后端进程。
2. 备份数据库：
   - SQLite：备份 `backend/aifiction.db`。
   - Docker SQLite：备份挂载目录里的 `aifiction.db`。
   - PostgreSQL：使用 `pg_dump` 或托管平台快照。
3. 拉取新代码。
4. 重新安装后端依赖：

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

5. 检查当前 schema 版本：

```bash
python -m app.scripts.check_schema
```

6. 启动后端。启动时会自动执行未应用的 schema migration。
7. 再次检查 schema 版本和健康接口：

```bash
python -m app.scripts.check_schema
```

```bash
curl http://127.0.0.1:8001/api/health
```

当前 migration 策略是非破坏性的：只追加字段、补结构索引、记录版本，不自动重写旧小说正文、章节摘要、弧线、角色关系或用户手动内容。

SQLite 可以用内置脚本先做一次文件备份：

```bash
cd backend
python -m app.scripts.backup_db
```

## 本地一键开发启动

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

脚本会：

1. 创建后端 `.venv`。
2. 安装 Python 依赖。
3. 启动 FastAPI `127.0.0.1:8001`。
4. 安装前端 npm 依赖。
5. 启动 Vite `127.0.0.1:5173`。

访问：

```text
http://127.0.0.1:5173
```

## Docker Compose：SQLite 单机版

这是默认推荐的一键体验方式。

```bash
cp .env.example .env
docker compose up -d --build
```

访问：

```text
http://127.0.0.1:5173
```

数据保存在 Docker volume：

```text
aifiction_data
```

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

停止：

```bash
docker compose down
```

停止并删除 SQLite 数据卷：

```bash
docker compose down -v
```

## Docker Compose：PostgreSQL 版

```bash
cp .env.example .env
docker compose -f docker-compose.postgres.yml up -d --build
```

访问：

```text
http://127.0.0.1:5173
```

PostgreSQL 数据保存在 Docker volume：

```text
pgdata
```

查看日志：

```bash
docker compose -f docker-compose.postgres.yml logs -f backend
```

停止：

```bash
docker compose -f docker-compose.postgres.yml down
```

停止并删除 PostgreSQL 数据：

```bash
docker compose -f docker-compose.postgres.yml down -v
```

## 环境变量

常用变量：

```env
JWT_SECRET_KEY=replace-this
CORS_ORIGINS=*

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o

DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-chat

CLAUDE_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-20250514
```

也可以启动后进入 `模型管理` 页面添加模型供应商。

## 数据库 SQL 文件

仓库提供 schema 文件：

```text
docs/database-schema.sql
```

它只包含表结构，不包含你的项目数据、章节数据、API Key 或任务记录。

本地运行产生的数据库文件不会提交到 Git：

```text
backend/aifiction.db
backend/aifiction.db-shm
backend/aifiction.db-wal
```

这些文件已在 `.gitignore` 中排除。
