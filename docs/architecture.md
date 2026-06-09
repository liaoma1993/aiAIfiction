# 技术架构

AI Fiction Studio 当前是一个本地优先的前后端分离应用。

```text
Browser
  |
  |  React + Vite dev proxy (/api -> :8001)
  v
FastAPI
  |
  |  SQLAlchemy async
  v
SQLite (default)
  |
  |  LLM Provider Adapter
  v
OpenAI-compatible / DeepSeek / Claude
```

## 前端架构

路径：`frontend/src`

```text
frontend/src/
├── App.tsx
├── routes/
│   └── index.tsx
├── pages/
│   ├── CreateProjectPage.tsx
│   ├── ProjectWizardPage.tsx
│   ├── WorkbenchPage.tsx
│   ├── OutlinePage.tsx
│   ├── CharactersPage.tsx
│   ├── FactionsPage.tsx
│   ├── WorldSettingPage.tsx
│   ├── MemoryCenterPage.tsx
│   ├── QualityDashboardPage.tsx
│   ├── StoryGraphPage.tsx
│   ├── LandscapePage.tsx
│   └── ProvidersPage.tsx
├── services/
│   ├── api.ts
│   └── projectApi.ts
└── stores/
```

### 页面职责

| 页面 | 职责 |
|---|---|
| `CreateProjectPage` | 项目策划对话、方案生成、创建项目 |
| `ProjectWizardPage` | 世界观、角色势力、全书大纲生成向导 |
| `WorkbenchPage` | 日常写作、卷轴目录、章节编辑、审计、修复 |
| `OutlinePage` | 大纲总览、卷大纲编辑、弧线和章节蓝图 |
| `CharactersPage` | 角色管理和当前状态 |
| `FactionsPage` | 势力、组织、阵营关系 |
| `WorldSettingPage` | 世界观、硬约束、文风氛围、生成限制 |
| `MemoryCenterPage` | 项目记忆、角色状态、伏笔、事件、风险 |
| `QualityDashboardPage` | 跨章节质量审计和修复 |
| `StoryGraphPage` | 叙事图谱、关系边、因果连接 |
| `LandscapePage` | 小说景观、关键事件、卷章泳道 |
| `ProvidersPage` | LLM 供应商配置 |

### API 请求

`frontend/src/services/api.ts` 创建 Axios 实例：

- `baseURL: /api/v1`
- 自动附加 `Authorization: Bearer <token>`
- 401 自动回到登录页

开发时 Vite 代理：

```ts
server: {
  port: 5173,
  proxy: {
    '/api': { target: 'http://localhost:8001', changeOrigin: true },
    '/ws': { target: 'ws://localhost:8001', ws: true },
  },
}
```

## 后端架构

路径：`backend/app`

```text
backend/app/
├── api/v1/
│   ├── auth.py
│   ├── projects.py
│   ├── volumes.py
│   ├── chapters.py
│   ├── characters.py
│   ├── factions.py
│   ├── world_settings.py
│   ├── wizard.py
│   ├── story.py
│   ├── providers.py
│   └── router.py
├── llm/
│   ├── __init__.py
│   ├── base.py
│   └── openai_provider.py
├── models/
├── services/
│   ├── ai_service.py
│   ├── context_builder.py
│   ├── story_bible.py
│   └── task_manager.py
├── config.py
├── database.py
├── main.py
└── seed.py
```

### 启动生命周期

`app/main.py` 使用 FastAPI lifespan：

1. 创建数据库表。
2. 执行版本化 schema migration，记录到 `schema_migrations`。
3. Seed 默认账号和默认模型供应商。
4. 刷新 LLM provider cache。
5. 恢复中断任务状态。
6. 关闭时 dispose 数据库连接。

## 数据模型

核心模型：

| 模型 | 作用 |
|---|---|
| `User` | 登录用户 |
| `Project` | 小说项目、简介、主题、策划记忆 |
| `ProjectPlanSession` | 创建项目前的策划对话草稿 |
| `Volume` | 卷轴、卷概要、卷大纲、弧线结构 |
| `Chapter` | 章节蓝图、正文、状态、质量分 |
| `ChapterVersion` | 章节版本备份 |
| `GenerationTask` | AI 任务状态和结果 |
| `WorldSetting` | 世界观、硬约束、文风规则、限制 |
| `Character` | 角色、人设、语言指纹、当前状态 |
| `Faction` | 势力、组织结构、利益冲突 |
| `FactionRelation` | 势力关系和变化 |
| `TimelineEvent` | 时间线事件 |
| `StoryStateTrail` | 章节后状态沉淀 |
| `ForeshadowingPlan` | 伏笔计划 |
| `LLMProvider` | 模型供应商配置 |

## AI 服务层

`backend/app/services/ai_service.py` 是主要 AI 编排层，包含：

- 系统角色定义：架构师、世界观设计师、写手、编辑。
- 项目策划提示词。
- 世界观/角色/势力/大纲提示词。
- 卷弧线和章节展开提示词。
- 正文写作提示词。
- 质量审计和修复提示词。
- 章节状态提取和记忆摘要。
- 大纲对话式调整。

AI 调用统一通过 `_ask()` / `_ask_list()`：

- 优先要求 JSON。
- JSON 解析失败时尝试清洗 markdown fence。
- 仍失败则抛出 `AI 返回格式异常`。

## 任务系统

`backend/app/services/task_manager.py` 提供内置任务管理：

- `start_task()` 启动后台异步任务。
- 任务状态先保存在进程内 `_tasks`。
- 同步写入 `generation_tasks` 表。
- 支持进度、错误、结果、取消和重试。
- 服务重启时把 running/cancelling 任务标记为失败。

任务适合本地单机开发。如果要部署多人生产环境，建议替换为：

- Celery + Redis/RabbitMQ
- RQ
- Arq
- Dramatiq
- Temporal

## LLM Provider

`backend/app/llm/__init__.py` 提供 provider 选择：

1. 优先读取数据库中的启用供应商。
2. 如果缓存过期则刷新。
3. 没有数据库配置时读取环境变量。
4. 支持 OpenAI 兼容接口。
5. Claude provider 通过兼容封装接入。

默认优先级：

```text
数据库 LLMProvider -> 环境变量 OPENAI/DEEPSEEK/CLAUDE -> 抛错
```

## API 分层

| 路由 | 职责 |
|---|---|
| `/auth` | 登录、认证 |
| `/projects` | 项目 CRUD、策划对话 |
| `/projects/{id}/volumes` | 卷管理 |
| `/projects/{id}/chapters` | 章节管理 |
| `/projects/{id}/characters` | 角色管理 |
| `/projects/{id}/factions` | 势力管理 |
| `/projects/{id}/world-setting` | 世界观管理 |
| `/projects/{id}/wizard` | AI 生成、写作、审计、修复、任务 |
| `/projects/{id}/story` | 图谱、记忆、质量仪表盘等聚合数据 |
| `/providers` | 模型供应商管理 |

## 可扩展方向

### 数据库

当前默认 SQLite。多人协作建议迁移到 PostgreSQL：

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aifiction
```

需要补充：

- PostgreSQL 升级回归测试
- JSON 字段兼容测试

### 任务队列

当前任务和后端进程绑定。生产环境建议：

- 把 `task_manager.py` 替换为队列适配层。
- 任务结果继续写入 `generation_tasks`。
- 前端轮询接口不需要大改。

### Prompt 配置化

当前提示词主要写在 `ai_service.py` 常量中。可扩展：

- 数据库 prompt registry。
- 版本号。
- A/B 测试。
- Prompt diff。
- 项目级覆盖。
- 用户自定义模板。

### 多用户协作

当前已有用户模型和项目归属，后续可扩展：

- 项目成员。
- 权限角色。
- 协同编辑锁。
- 操作审计日志。
- 评论和批注。
