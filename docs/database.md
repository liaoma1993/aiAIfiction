# 数据库说明：SQLite 与 PostgreSQL

AI Fiction Studio 通过 `DATABASE_URL` 选择数据库。当前代码同时支持 SQLite 和 PostgreSQL：

```env
DATABASE_URL=sqlite+aiosqlite:///./aifiction.db
DATABASE_URL=postgresql+asyncpg://aifiction:aifiction@localhost:5432/aifiction
```

## 结论先行

| 使用场景 | 推荐数据库 |
|---|---|
| 本地开发 | SQLite |
| 单人写作 | SQLite |
| 快速体验 Demo | SQLite |
| Docker 一键启动 | SQLite |
| 多人使用 | PostgreSQL |
| 长期部署 | PostgreSQL |
| 数据量较大 | PostgreSQL |
| 需要更强并发写入 | PostgreSQL |
| 后续接入外部任务队列 | PostgreSQL |

如果你只是自己本地写小说，用 SQLite 足够。

如果你要把项目部署给多人用，或者准备长期在线运行，建议用 PostgreSQL。

## 服务启动时会自动创建数据库吗

会自动建表，但“数据库本身”的创建方式取决于数据库类型。

### SQLite

SQLite 是文件数据库。

默认配置：

```env
DATABASE_URL=sqlite+aiosqlite:///./aifiction.db
```

如果 `backend/aifiction.db` 不存在，服务启动时会自动创建文件并建表。

后端启动流程在：

```text
backend/app/main.py
```

关键逻辑：

```python
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

所以 SQLite 下：

```text
启动服务 -> 文件不存在 -> 自动创建 aifiction.db -> 自动创建表
```

### PostgreSQL

PostgreSQL 是数据库服务。

应用会自动建表，但不会自动创建 PostgreSQL server，也不会自动创建数据库实例。

你需要先有一个可连接的 PostgreSQL 数据库，例如：

```text
host: localhost
port: 5432
database: aifiction
user: aifiction
password: aifiction
```

然后配置：

```env
DATABASE_URL=postgresql+asyncpg://aifiction:aifiction@localhost:5432/aifiction
```

后端启动后会在这个数据库里自动建表。

Docker PostgreSQL 版会通过 `postgres` 容器自动创建数据库：

```yaml
POSTGRES_DB: aifiction
POSTGRES_USER: aifiction
POSTGRES_PASSWORD: aifiction
```

所以 Docker PostgreSQL 下：

```text
启动 postgres 容器 -> postgres 镜像创建 database -> 后端连接 -> 自动创建表
```

## 当前自动建表机制

当前项目使用 SQLAlchemy：

```text
backend/app/database.py
backend/app/main.py
backend/app/models/
```

启动时：

1. 导入所有模型。
2. 执行 `Base.metadata.create_all()`。
3. 执行版本化 schema migration，记录到 `schema_migrations`。
4. Seed 默认管理员。
5. Seed 默认模型供应商。

这适合开发期和本地部署。开源用户已有数据库升级时，migration 必须只做非破坏性变更：追加字段、补结构索引、保留旧小说正文和已生成大纲。

## SQLite 说明

### 优点

- 不需要安装数据库服务。
- 一个文件就是数据库。
- 本地开发最省事。
- Docker 单机部署简单。
- 备份只需要复制数据库文件。

### 缺点

- 并发写入能力有限。
- 多用户同时操作时更容易遇到锁。
- 不适合复杂权限和大规模数据。
- 不适合作为多人在线服务的长期主库。

### 当前 SQLite 优化

系统在连接 SQLite 时会设置：

```python
PRAGMA foreign_keys = ON
PRAGMA journal_mode = WAL
PRAGMA busy_timeout = 30000
```

含义：

- `foreign_keys = ON`：启用外键约束。
- `journal_mode = WAL`：提升读写并发体验。
- `busy_timeout = 30000`：遇到锁时最多等待 30 秒。

### SQLite 文件位置

本地开发默认：

```text
backend/aifiction.db
```

Docker SQLite 版默认：

```text
/data/aifiction.db
```

Docker volume：

```text
aifiction_data
```

### SQLite 不应该提交到 Git

不要提交：

```text
backend/aifiction.db
backend/aifiction.db-shm
backend/aifiction.db-wal
```

原因：

- 里面包含你的项目数据。
- 可能包含章节正文。
- 可能包含模型供应商配置。
- 可能包含任务结果和错误信息。
- 文件会越来越大。

仓库已经在 `.gitignore` 排除：

```gitignore
*.db
*.db-shm
*.db-wal
backend/aifiction.db
backend/aifiction.db-shm
backend/aifiction.db-wal
```

### SQLite 备份

如果服务已停止，可以直接复制：

```bash
cp backend/aifiction.db backup/aifiction-$(date +%Y%m%d).db
```

如果服务正在运行，推荐使用 SQLite backup：

```bash
sqlite3 backend/aifiction.db ".backup 'backup/aifiction-$(date +%Y%m%d).db'"
```

### SQLite 恢复

停止服务后替换文件：

```bash
cp backup/aifiction-20260605.db backend/aifiction.db
```

然后重新启动后端。

## PostgreSQL 说明

### 优点

- 并发能力更强。
- 更适合多人使用。
- 更适合长期在线部署。
- 备份、恢复、权限和运维工具成熟。
- 后续接任务队列、审计日志、多租户更稳。

### 缺点

- 需要数据库服务。
- 需要维护账号、密码、端口、备份。
- 本地启动复杂度比 SQLite 高。
- schema 迁移最好接 Alembic。

### PostgreSQL 连接格式

```env
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:端口/数据库名
```

示例：

```env
DATABASE_URL=postgresql+asyncpg://aifiction:aifiction@localhost:5432/aifiction
```

Docker Compose 里后端访问 postgres 容器：

```env
DATABASE_URL=postgresql+asyncpg://aifiction:aifiction@postgres:5432/aifiction
```

这里的 `postgres` 是 Compose service name，不是 localhost。

### PostgreSQL Docker 启动

```bash
cp .env.example .env
docker compose -f docker-compose.postgres.yml up -d --build
```

访问：

```text
http://127.0.0.1:5173
```

查看数据库容器：

```bash
docker compose -f docker-compose.postgres.yml ps
```

查看后端日志：

```bash
docker compose -f docker-compose.postgres.yml logs -f backend
```

### PostgreSQL 备份

```bash
docker exec aifiction-postgres pg_dump -U aifiction aifiction > backup/aifiction.sql
```

### PostgreSQL 恢复

```bash
cat backup/aifiction.sql | docker exec -i aifiction-postgres psql -U aifiction aifiction
```

## SQLite 和 PostgreSQL 的实际选择

### 推荐 SQLite 的情况

你符合这些条件时，用 SQLite：

- 只有你一个人用。
- 主要在本机写作。
- 数据库文件能接受手动备份。
- 不想维护数据库服务。
- 只是开源演示或本地试用。

推荐启动：

```bash
docker compose up -d --build
```

或：

```bash
./scripts/dev.sh
```

### 推荐 PostgreSQL 的情况

你符合这些条件时，用 PostgreSQL：

- 准备部署到服务器。
- 多人登录使用。
- 章节和任务量很大。
- 需要更可靠的备份恢复。
- 后续要做权限、协作、团队空间。
- 后续要接独立任务队列。

推荐启动：

```bash
docker compose -f docker-compose.postgres.yml up -d --build
```

## 从 SQLite 迁移到 PostgreSQL

当前仓库提供的是 schema 文件：

```text
docs/database-schema.sql
```

它是 SQLite schema，只用于查看结构，不建议直接拿去 PostgreSQL 生产导入。

更推荐的迁移路线：

1. 在 PostgreSQL 中启动一套空库。
2. 让后端自动 `create_all` 建表并执行版本化 schema migration。
3. 写一个专门的数据迁移脚本：
   - 从 SQLite 读出项目、卷、章节、角色等数据。
   - 转成 JSON 兼容结构。
   - 写入 PostgreSQL。
4. 校验项目数量、章节数量、正文数量和任务数量。

项目已包含 Alembic 基础配置。新增数据库结构变更时：

```text
cd backend
alembic revision --autogenerate -m "change description"
alembic upgrade head
```

应用启动迁移和 Alembic revision 要保持同一语义版本，例如当前首版是：

```text
20260609_0001 add narrative continuity columns
```

应用启动时会记录到 `schema_migrations`；Alembic 用于后续标准化生成和审查结构变更。

## 当前限制

当前数据库层仍处于开发友好模式：

- 启动时自动 `create_all()`。
- 启动时执行版本化 schema migration。
- Alembic 已接入基础配置，后续结构变更应补 revision 文件。
- PostgreSQL 支持已接入依赖和连接方式，但仍建议在正式部署前做完整测试。

如果你要公开部署，建议优先补：

- 数据库初始化脚本。
- 管理员密码首次启动设置。
- API Key 加密存储。
- 定期备份脚本。
- 健康检查。

## 快速对照

| 项 | SQLite | PostgreSQL |
|---|---|---|
| 启动复杂度 | 低 | 中 |
| 是否需要数据库服务 | 不需要 | 需要 |
| 自动创建表 | 支持 | 支持 |
| 自动创建数据库实例 | 文件自动创建 | Docker 容器支持，本地需手动建库 |
| 并发写入 | 弱 | 强 |
| 适合单人 | 是 | 是 |
| 适合多人 | 不推荐 | 推荐 |
| 备份方式 | 复制/backup 文件 | pg_dump |
| Git 提交 | 不能提交 db 文件 | 不提交数据 |
| 推荐用途 | 本地/演示 | 部署/多人/长期 |
