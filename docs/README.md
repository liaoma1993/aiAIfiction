# 文档中心

这里收集 AI Fiction Studio 的使用、架构、AI 工作流和二次开发文档。

## 推荐阅读顺序

1. [快速上手](getting-started.md)
2. [使用手册](user-manual.md)
3. [AI 工作流](ai-workflows.md)
4. [记忆管理](memory-management.md)
5. [提示词管理](prompt-management.md)
6. [技术架构](architecture.md)
7. [开发与二次开发](development.md)

## 面向用户

| 文档 | 内容 |
|---|---|
| [快速上手](getting-started.md) | 本地启动、登录、模型配置、第一个项目 |
| [使用手册](user-manual.md) | 从策划到写作、审计、修复、记忆中枢的完整操作流程 |

## 面向开发者

| 文档 | 内容 |
|---|---|
| [技术架构](architecture.md) | 前后端结构、数据模型、任务系统、LLM Provider |
| [AI 工作流](ai-workflows.md) | 项目策划、世界观、角色、大纲、章节、质量审计的任务链路 |
| [提示词管理](prompt-management.md) | 当前 prompt 清单、设计原则、局部修复策略、可视化管理方案 |
| [记忆管理](memory-management.md) | Story Bible、Generation Context、角色状态、伏笔、章节记忆 |
| [开发与二次开发](development.md) | 新增 AI 任务、页面、数据迁移、PR 检查和安全建议 |

## 历史设计文档

| 文档 | 内容 |
|---|---|
| [wizard-design.md](wizard-design.md) | 早期项目向导设计 |
| [wizard-design-v4.md](wizard-design-v4.md) | v4 项目向导设计 |
| [ux-wireframes.md](ux-wireframes.md) | UX 线框和页面规划 |

## 开源发布建议

正式开源前建议补充：

- `LICENSE`
- `CODE_OF_CONDUCT.md`
- `.env.example` 清理和完善
- 截图或 GIF
- Roadmap
- Issue templates
- PR template

已提供：

- [贡献指南](../CONTRIBUTING.md)

## 推荐 Roadmap

### v0.1 本地创作闭环

- 项目策划对话。
- 世界观、角色势力、大纲生成。
- 卷弧线和章节蓝图。
- 章节写作。
- 质量审计和局部修复。
- 记忆中枢和故事景观图。

### v0.2 稳定性和提示词工程

- Prompt Registry。
- Prompt 版本管理。
- AI 任务去重。
- 老数据迁移工具。
- 章节版本 diff。
- 更稳定的 JSON 输出修复。

### v0.3 长篇记忆增强

- 章节完成后自动提取状态。
- 角色状态 diff。
- 伏笔生命周期。
- 记忆冲突检测。
- 长程检索记忆。

### v0.4 多人和部署

- PostgreSQL 支持。
- 外部任务队列。
- 项目成员和权限。
- 操作审计日志。
- API Key 加密存储。
- 额度和成本统计。
