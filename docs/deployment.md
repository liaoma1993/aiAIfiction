# 一键启动与 Docker 部署

AI Fiction Studio 支持三种启动方式：

1. 本地开发启动。
2. Docker Compose 单机 SQLite 版。
3. Docker Compose PostgreSQL 版。

## 数据库是否会自动创建

会。

后端启动时会执行 FastAPI lifespan：

```text
backend/app/main.py
```

启动流程：

1. 导入所有 SQLAlchemy models。
2. 执行 `Base.metadata.create_all()`。
3. 如果是 SQLite，补充部分历史新增列。
4. Seed 默认管理员账号。
5. Seed 默认模型供应商。
6. 恢复中断任务状态。

所以第一次启动时，如果数据库文件不存在，会自动建表。

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

注意：当前项目仍使用 `create_all()` 自动建表。生产环境建议后续接入 Alembic migration。

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
