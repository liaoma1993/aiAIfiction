# AI Fiction Studio

> 面向长篇网文创作的 AI 小说工作台：从脑洞策划、世界观、角色势力、卷轴大纲，到写作风格学习、章节写作、质量审计、局部修复、记忆中枢和故事景观图。

AI Fiction Studio 不是一个“输入一句话生成一篇小说”的玩具。它更像一套小说生产系统：把项目策划、长篇结构、角色状态、世界规则、伏笔、章节蓝图、正文生成、质量评审和修复流程放在同一个工作台里，让 AI 在明确边界、上下文和长期记忆中协作写作。

系统还内置共享写作风格 Skill：可以上传小说样本文本，让 AI 从中抽取作者的文笔工艺、段落推进、细节刻画、人物出场、情绪落点、场景真实感和章节生产法，形成跨项目复用的写作方法库。Skill 只学习抽象写法，不复制原文、剧情、人名、地名、组织名或专有设定。

## 核心能力

- **项目策划对话**：用聊天方式把零散脑洞整理成可执行项目方案，保留核心引擎、读者承诺、边界锁定和长篇规划。
- **世界观生成与约束管理**：生成地理、社会结构、力量体系、历史、文化、世界逻辑，并支持硬约束、文风氛围、生成限制。
- **角色与势力系统**：维护角色人设、语言指纹、成长弧、当前状态、组织结构、阵营关系和利益冲突。
- **卷轴与大纲工作流**：生成全书大纲，拆分卷、弧线和章节蓝图；支持弧线重拆、拉长、压缩、重写和对话式调整。
- **写作风格学习 Skill**：上传小说样本，后台抽取文笔工艺、段落推进、细节刻画、人物出场、情绪落点、场景真实感和章节生产法，形成全局共享 Skill，并可被不同项目引用。
- **章节写作工作台**：按章节蓝图生成正文，支持通俗易懂、简单直白、正常、烧脑细腻等可读性模式。
- **批量写作**：按弧线批量生成章节，沿用写作设置、可读性控制和上下文记忆。
- **质量仪表盘**：审计章节的可读性、标点、对白、场景清晰度、角色一致性、钩子、AI 味等维度。
- **局部修复与整章优化**：支持只修原句、修这一段、深修此问题、整章轻修、按审计重写。
- **记忆中枢**：集中查看项目记忆、角色状态、伏笔、事件、章节记忆、风险和组织信息。
- **故事图谱与景观图**：查看关键事件、角色关系、因果连接、卷章景观泳道和叙事结构。
- **多模型配置**：支持在界面中配置 OpenAI 兼容接口、DeepSeek、Claude 等模型供应商。

## 适合谁

- 想做 AI 辅助网文创作工具的开发者。
- 想研究“长篇小说上下文工程”的产品或工程团队。
- 想把 AI 生成从一次性文本变成“可持续写作流水线”的作者。
- 想二次开发提示词管理、质量审计、记忆系统、故事图谱的开源爱好者。

## 技术栈

| 层 | 当前实现 |
|---|---|
| 前端 | React 18 + TypeScript + Vite |
| UI | Ant Design 5 |
| 路由 | React Router |
| 状态/请求 | Axios + 局部 React State |
| 后端 | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.0 async |
| 默认数据库 | SQLite + WAL |
| 任务系统 | 内置异步任务管理 + `generation_tasks` 持久化 |
| LLM | OpenAI 兼容接口，支持多供应商配置 |
| 写作风格 Skill | 全局共享库 + 文件上传 + 后台抽取任务 + 多点代表性采样 |

> 当前代码以本地开发和单机创作为主。README 只描述现有可运行实现；如果你要做多人协作、分布式任务队列或对象存储，可以在此基础上扩展 PostgreSQL、Redis/Celery、S3/MinIO 等基础设施。

## 快速开始

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173/
```

默认账号：

```text
邮箱：admin@aifiction.com
密码：admin123
```

### 3. 配置模型

进入 `模型管理` 页面添加模型供应商，或在 `backend/.env` 中配置：

```env
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o

DEEPSEEK_API_KEY=your-key
DEEPSEEK_MODEL=deepseek-chat

CLAUDE_API_KEY=your-key
CLAUDE_MODEL=claude-sonnet-4-20250514
```

## 文档

- [文档中心](docs/README.md)
- [快速上手](docs/getting-started.md)
- [使用手册](docs/user-manual.md)
- [整体设计架构](docs/product-design-architecture.md)
- [技术架构](docs/architecture.md)
- [数据库说明](docs/database.md)
- [一键启动与 Docker 部署](docs/deployment.md)
- [AI 工作流](docs/ai-workflows.md)
- [写作风格 Skill](docs/writing-style-skills.md)
- [提示词管理](docs/prompt-management.md)
- [记忆管理](docs/memory-management.md)
- [开发与二次开发](docs/development.md)
- [贡献指南](CONTRIBUTING.md)

历史设计文档：

- [Wizard Design v4](docs/wizard-design-v4.md)
- [UX Wireframes](docs/ux-wireframes.md)

## 项目结构

```text
AIfiction/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI 路由
│   │   ├── llm/             # 模型供应商适配
│   │   ├── models/          # SQLAlchemy 模型
│   │   ├── services/        # AI 服务、上下文、任务、故事圣经
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # 工作台、向导、角色、质量、记忆等页面
│   │   ├── services/        # API 封装
│   │   ├── stores/          # 认证/项目状态
│   │   └── routes/
│   └── package.json
└── docs/
```

## 设计理念

### 1. 长篇优先

长篇小说最难的不是生成一章，而是 20 万字、50 万字、100 万字之后仍然不散。系统围绕卷、弧线、章节蓝图、角色状态、伏笔和近期章节记忆组织上下文。

### 2. 结构先于正文

正文生成依赖项目策划、世界规则、角色语言指纹、卷目标、弧线功能、章节承接和章末钩子。AI 不应该凭空写，而应该在结构中写。

### 3. 修复要可定位

质量审计不只给“7 分”这种结果，而要定位原文、说明问题、给出修复范围：只修原句、修段落、深修上下文或整章轻修。

### 4. 记忆不是聊天记录

系统记忆不是简单把历史对话塞进 prompt，而是把项目设定、角色状态、世界约束、伏笔、时间线、章节摘要和近期状态压缩为可控上下文。

### 5. 风格是共享方法，不是洗稿

写作风格 Skill 的目标是学习“怎么写”，而不是复制“写了什么”。样本上传后会进入后台任务，系统只做多点代表性采样和抽象写法提取，沉淀为文笔工艺、段落推进、细节工艺、人物出场、情绪落点、场景真实感、章节生产法和可复用模式。项目引用 Skill 后，Skill 只影响创建、大纲、蓝图和正文生成的写法，不覆盖项目设定和已写事实。

## 当前状态

项目处于积极迭代阶段，功能已经覆盖从策划到写作、审计、修复、记忆和图谱的主流程。部分能力仍偏实验性，尤其是：

- 大纲重构后的历史数据清理策略。
- 长篇质量评分模型的稳定性。
- 提示词配置的可视化程度。
- 写作风格 Skill 的样本覆盖度、风格混合和效果评估。
- 多用户、多项目并发任务调度。

欢迎基于 Issues / PR 参与改进。

贡献前建议阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

当前仓库未内置许可证文件。开源发布前建议补充 `LICENSE`，例如 MIT、Apache-2.0 或 AGPL-3.0，根据你的商业化和二次分发策略选择。
