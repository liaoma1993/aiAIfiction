# AI 工作流

本文档说明系统中主要 AI 任务如何串联。

## 总览

```text
灵感/对话
  -> 项目方案
  -> 世界观
  -> 角色势力
  -> 全书大纲
  -> 卷弧线
  -> 弧线章节
  -> 章节正文
  -> 质量审计
  -> 局部修复 / 整章优化
  -> 状态提取
  -> 记忆中枢
```

全局共享能力还有一条独立链路：

```text
小说样本上传
  -> 写作风格抽取任务
  -> 多点代表性采样
  -> 写法工艺拆解
  -> 共享 Skill
  -> 项目引用
  -> 注入创建 / 大纲 / 弧线 / 蓝图 / 正文写作
```

## 1. 项目策划

接口：

```text
POST /api/v1/projects/plan-chat
PUT  /api/v1/projects/plan-session
GET  /api/v1/projects/plan-session
```

输入：

- 用户多轮对话。
- 已选题材。
- 当前草案。
- 意图：`chat` / `generate`。

输出：

- assistant reply。
- project draft。
- suggestions。
- next questions。
- detail options。

目标：

- 不要每轮另起炉灶。
- 逐步加固当前项目。
- 生成候选方案时才输出多方案。

如果创建页选择了共享写作风格 Skill，项目策划会读取 Skill 的创建阶段指导，但用户当前故事核心、边界锁定和项目事实优先级更高。

## 1.1 写作风格 Skill 抽取

入口：

```text
/writing-style-skills
```

接口：

```text
POST /api/v1/writing-style-skills/analyze-upload
GET  /api/v1/writing-style-skills/task/{task_id}
GET  /api/v1/writing-style-skills/tasks
```

输入：

- 小说样本文本文件。
- Skill 名称。
- 来源备注。
- 可选补充说明。

输出：

- `task_id`。
- 后台任务完成后生成共享 Skill。

设计原因：

- 小说样本可能很大，不能把全文渲染到页面。
- AI 分析可能超过 2 分钟，不能让 HTTP 请求同步等待。
- Skill 是全局共享资产，不属于某个项目，所以它有独立任务列表。

抽取逻辑：

- 优先识别章节标题。
- 按章节位置多点取样：开篇、前期、中段、后期、结尾附近。
- 识别不到章节时按全文均匀窗口取样。
- 只把代表性样本送入 AI，不保存样本全文。

抽取重点：

- 文笔工艺。
- 段落推进。
- 细节刻画。
- 人物出场。
- 情绪落点。
- 场景真实感。
- 世界观揭示。
- 冲突组织。
- 章节生产法。
- 可复用写作模式。

## 2. 世界观生成

接口位于 wizard 工作流。

生成内容：

- 地理。
- 社会结构。
- 力量体系。
- 历史。
- 文化。
- 特殊规则。
- 世界逻辑。
- 硬约束。
- 文风氛围。
- 生成限制。

关键要求：

- 世界观不能只是名词堆砌。
- 力量体系、历史、文化和社会结构要有因果关系。
- 硬约束要能进入章节生成上下文。

## 3. 角色势力生成

角色生成关注：

- 角色类型。
- 性格。
- 背景。
- 动机。
- 行为模式。
- 语言风格。
- 语言指纹。
- 内在矛盾。
- 成长弧。
- 关系动态。

势力生成关注：

- 组织类型。
- 核心信条。
- 阶层结构。
- 利益冲突。
- 内部裂缝。
- 对外声誉与真实状态。
- 力量轨迹。

当前 UI 已尽量使用中文标签，避免用户看到 `protagonist`、`sect`、`encounter` 等英文枚举。

## 4. 全书大纲

目标：

- 根据项目方案、世界观、角色势力生成全书结构。
- 拆分卷。
- 明确每卷目标、主题、情绪弧线、章节范围和目标字数。

大纲不是正文摘要，而是创作地图。

## 5. 卷弧线拆分

接口：

```text
POST /api/v1/projects/{project_id}/wizard/expand-volume-arcs/{volume_id}
```

用途：

- 把一卷拆成多个叙事弧线。
- 每条弧线有叙事功能、开局状态、终点状态、主角变化、伏笔计划。

支持配置：

- 长篇连载型。
- 短篇紧凑型。
- 轻松单元剧型。
- 主线强推进型。
- 群像展开型。

弧线数量不需要用户手填具体章节，系统根据策略自动拆分。

## 6. 弧线章节展开

接口：

```text
POST /api/v1/projects/{project_id}/wizard/expand-arc-chapters/{volume_id}
```

用途：

- 把某条弧线展开为章节。
- 每章包含标题、摘要、承接、钩子、关键事件、蓝图。

注意：

- 两个章节可以发生在同一场景。
- 同一场景不等于应该合并章节。
- 判断章节是否需要保留，应看章节功能，而不是地点是否相同。

## 7. 大纲对话式调整

接口：

```text
POST /api/v1/projects/{project_id}/wizard/adjust-outline-chat/{volume_id}
POST /api/v1/projects/{project_id}/wizard/adjust-outline/{volume_id}
```

分两步：

1. `adjust-outline-chat`：只对话整理意见，不落库。
2. `adjust-outline`：根据最终调整要求修改大纲。

调整范围：

| scope | 效果 |
|---|---|
| `summary_only` | 只保存卷概要 |
| `outline` | 调整卷概要、卷大纲、弧线、章节蓝图 |

`summary_only` 是安全模式，即使 AI 返回了弧线或章节补丁，后端也只应用 `volume.summary`。

## 8. 章节写作

接口：

```text
POST /api/v1/projects/{project_id}/wizard/write-chapter/{chapter_id}
```

上下文来自：

- `build_generation_context()`。
- 当前章节蓝图。
- 最近章节。
- 写作设置。
- 可读性模式。

输出：

- 章节正文。
- 字数。
- 状态更新。
- 可选质量审计。

写作原则：

- 网文可读性优先。
- 主线目标清楚。
- 冲突具体。
- 对白推动剧情。
- 避免过度文学化。
- 章末要有追读动力。

## 9. 批量写作

批量写作按弧线选择章节生成。

适合：

- 已经有稳定章节蓝图。
- 想快速铺出一批初稿。
- 后续再逐章审计和修复。

不适合：

- 大纲还不稳定。
- 前文角色状态未维护。
- 关键设定仍在频繁变动。

## 10. 结构前置审查

弧线展开章节前，可以先审查弧线是否像独立小故事、角色/组织是否空降、是否需要桥接章：

```text
POST /api/v1/projects/{project_id}/wizard/review-arc-structure/{volume_id}
```

章节蓝图写正文前，可以审查新角色/新组织入场、主角状态连续性、桥接章、状态增量和章末钩子：

```text
POST /api/v1/projects/{project_id}/wizard/review-chapter-blueprints/{volume_id}
```

这两个审查只写回审查结果和修复建议，不自动改旧正文、不自动重拆旧小说。

## 11. 质量审计

接口：

```text
POST /api/v1/projects/{project_id}/wizard/audit-chapter/{chapter_id}
```

审计输出：

- passed。
- overall_score。
- scores。
- highlights。
- issues。

问题字段通常包括：

- severity。
- dimension。
- target_text。
- fix_mode。
- description。
- fix_suggestion。

重要点：

- `target_text` 必须能在正文中精确定位。
- 老数据缺定位时，需要重新审计定位。

## 11. 修复

接口：

```text
POST /api/v1/projects/{project_id}/wizard/revise-chapter/{chapter_id}
```

主要模式：

- `target_sentence_fix`
- `target_paragraph_fix`
- `target_context_fix`
- `quality_light_fix`
- `audit_full_rewrite`

后端保护：

- 局部修复必须找到 selection。
- 找不到不覆盖全文。
- 修复前保存版本。
- 已完成章节不应被随意改回 `writing`。

## 12. 状态提取

接口：

```text
POST /api/v1/projects/{project_id}/wizard/extract-state/{chapter_id}
```

用途：

- 从已写正文提取角色和剧情状态变化。
- 为后续章节提供更稳定记忆。

建议流程：

```text
写本章 -> 审计 -> 修复 -> 确认 -> 提取状态 -> 写下一章
```

## 13. 失败处理

### AI 返回格式异常

常见原因：

- 模型没有严格返回 JSON。
- 输出被截断。
- 返回了 markdown 或解释文本。

处理：

- 后端会尝试清洗 code fence。
- 失败则抛出明确错误。
- 可以降低输出复杂度或拆分任务。

### 任务中断

服务重启会中断运行中任务。系统会把任务标记为失败：

```text
服务重启，后台任务已中断，请重新发起
```

### 重复任务

如果用户连续点击或前端重复提交，可能产生多个任务。需要在 UI 上禁用 loading 中按钮，并在后端对关键写入任务增加锁。

当前大纲写入有项目级锁思路，后续可以扩展到更多任务。
