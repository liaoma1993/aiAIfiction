# Contributing

感谢你对 AI Fiction Studio 感兴趣。这个项目的目标是把 AI 小说生成从“一次性文本生成”推进到“可维护的长篇创作系统”。

## 适合贡献的方向

- Prompt Registry 和提示词版本管理。
- 章节质量审计和修复策略。
- 记忆中枢、角色状态、伏笔生命周期。
- 卷轴大纲、弧线拆分、章节蓝图。
- 小说景观图、叙事图谱、关系边交互。
- PostgreSQL 和外部任务队列支持。
- 测试覆盖、错误处理、任务去重。
- UI 中文化和交互优化。

## 本地启动

后端：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

前端：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173/
```

## 提交前检查

```bash
cd backend
python3 -m compileall app

cd ../frontend
npm run build
```

如果你的改动影响 AI 任务，请至少手动验证：

- 任务能创建。
- 任务能轮询完成或失败。
- 失败时错误可读。
- 任务详情不是纯 JSON 噪音。
- 不会重复提交导致重复写入。

## 开发约定

### UI

- 用户可见文案优先中文。
- 不暴露英文枚举给作者，例如 `protagonist`、`encounter`、`high`。
- 长文本必须换行或滚动，不能被截断或覆盖。
- AI 任务详情优先结构化展示。
- 写作工具界面应清晰、密集、实用，不做营销式页面。

### 后端

- API 层保持薄，复杂逻辑放到 `services/`。
- AI 任务使用 `start_task()` 并写入任务状态。
- 数据库写入要考虑重复提交和并发任务。
- 局部修复必须有范围保护，不能找不到 selection 就覆盖整章。
- 已写正文是事实，不应被大纲调整静默推翻。

### Prompt

- 明确输入。
- 明确输出 JSON schema。
- 明确禁止行为。
- 明确任务边界。
- 对大纲调整、局部修复、质量审计等高风险任务必须加保护规则。

## Pull Request 建议

PR 描述建议包含：

- 解决了什么问题。
- 改了哪些页面/接口/数据结构。
- 是否影响已有项目数据。
- 是否需要迁移。
- 如何测试。
- 截图或录屏，如果是 UI 改动。

## Issue 建议

提交问题时尽量提供：

- 页面路径。
- 操作步骤。
- 请求 URL。
- 错误信息。
- 项目/章节状态。
- 期望行为。

涉及 AI 输出质量时，最好提供：

- 使用的模型。
- 输入的大纲或章节片段。
- AI 返回内容。
- 为什么不符合预期。

## 安全

不要提交：

- `.env`
- API Key
- 用户真实作品数据
- 数据库文件
- 包含隐私内容的截图

正式部署前请修改：

- 默认管理员密码。
- `JWT_SECRET_KEY`。
- CORS 配置。
- 模型供应商 API Key 存储方式。
