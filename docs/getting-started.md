# 快速上手

本文档帮助你在本地启动 AI Fiction Studio，并完成第一个小说项目。

## 环境要求

- Python 3.12+
- Node.js 18+
- npm 9+
- 一个可用的 LLM API Key

默认数据库是 SQLite，启动后会在 `backend/aifiction.db` 创建本地数据库文件。

## 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

后端健康检查：

```bash
curl http://127.0.0.1:8001/api/health
```

返回示例：

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

## 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173/
```

前端开发服务器会把 `/api` 代理到 `http://localhost:8001`。

## 登录

系统首次启动会自动创建默认管理员：

```text
邮箱：admin@aifiction.com
密码：admin123
```

生产或公开部署前必须修改默认账号密码和 `JWT_SECRET_KEY`。

## 配置模型

推荐在页面右上角进入 `模型管理` 配置供应商。也可以使用环境变量：

```env
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o

DEEPSEEK_API_KEY=your-key
DEEPSEEK_MODEL=deepseek-chat

CLAUDE_API_KEY=your-key
CLAUDE_MODEL=claude-sonnet-4-20250514

JWT_SECRET_KEY=replace-this
DATABASE_URL=sqlite+aiosqlite:///./aifiction.db
CORS_ORIGINS=*
```

后端启动时会读取 `backend/.env`。

## 第一个项目

1. 进入 `创建项目`。
2. 在 `项目策划对话` 里描述你的脑洞、主角、题材、爽点或读者期待。
3. 通过多轮对话让 AI 整理候选方案。
4. 选择一个方案创建项目。
5. 进入项目向导，依次生成世界观、角色势力、全书大纲。
6. 在工作台展开卷轴弧线和章节。
7. 选择章节，点击 `写本章`。
8. 写完后点击 `审计`，根据问题清单局部修复。

## 常见问题

### 前端请求 404

如果刚新增了后端接口，但前端已经热更新，后端没有重载，会出现 404。重启后端：

```bash
cd backend
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### 没有可用模型

报错：

```text
没有可用的 LLM 配置
```

解决：

1. 在 `模型管理` 页面新增供应商。
2. 或在 `backend/.env` 设置 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `CLAUDE_API_KEY`。

### SQLite 被锁

系统已经启用 WAL、busy timeout 和外键约束。如果仍然遇到锁：

1. 确认没有多个后端实例同时写同一个 `aifiction.db`。
2. 停止旧进程后再启动。
3. 对多人部署建议迁移到 PostgreSQL。

### 重启后任务失败

当前任务系统是进程内异步任务 + 数据库持久化状态。服务重启会把运行中的任务标记为失败：

```text
服务重启，后台任务已中断，请重新发起
```

这是预期行为。长时间批量任务建议后续接入 Celery/RQ/Arq 等外部队列。
