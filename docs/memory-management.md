# 记忆管理

AI Fiction Studio 的记忆系统目标是解决长篇小说创作中的三个问题：

1. 写到后面忘记前文设定。
2. 角色状态和关系变化断裂。
3. AI 只记得最近 prompt，不记得项目长期规划。

系统没有简单地把所有历史聊天塞进 prompt，而是把记忆拆成结构化资产。

## 记忆来源

| 来源 | 数据位置 | 用途 |
|---|---|---|
| 项目策划记忆 | `Project.writing_style.wizard_planning_memory` | 核心引擎、读者承诺、边界锁定、长篇规划 |
| 项目简介 | `Project.story_brief` | 全局故事方向 |
| 世界观 | `WorldSetting` | 地理、社会、力量体系、历史、文化、硬约束 |
| 角色 | `Character` | 人设、语言指纹、成长弧、当前状态 |
| 势力 | `Faction` / `FactionRelation` | 组织结构、利益冲突、阵营关系 |
| 卷轴 | `Volume` | 卷概要、卷大纲、主题、弧线 |
| 章节 | `Chapter` | 摘要、蓝图、钩子、正文、质量 |
| 伏笔 | `ForeshadowingPlan` | 投放阶段、揭示阶段、状态 |
| 时间线 | `TimelineEvent` | 关键事件和发生时间 |
| 状态轨迹 | `StoryStateTrail` | 章节后的状态沉淀 |

## Story Bible

核心函数：

```text
backend/app/services/story_bible.py
```

`build_story_bible(db, project_id, chapter_id)` 会聚合：

- 项目信息。
- 策划记忆。
- 世界观。
- 角色。
- 势力。
- 势力关系。
- 时间线。
- 伏笔。
- 卷轴。
- 当前卷。
- 当前章节。
- 最近章节。

返回的是完整“故事圣经”，适合页面展示或进一步压缩。

## Generation Context

核心函数：

```text
backend/app/services/context_builder.py
```

`build_generation_context()` 会把 Story Bible 压缩成适合 LLM 使用的上下文：

```json
{
  "project_summary": {},
  "hard_constraints": [],
  "tone_rules": [],
  "world_logic": {},
  "characters": "...",
  "factions": "...",
  "timeline": "...",
  "foreshadowing": "...",
  "current_volume": {},
  "current_chapter": {},
  "recent_chapters": [],
  "chapter_blueprint": {},
  "chapter_mandates": {}
}
```

压缩策略：

- 项目简介截断到可控长度。
- 角色只取前若干个关键字段。
- 时间线只取最近/重要事件。
- 伏笔只取有限条数。
- 最近章节默认取 3 章。

## 项目策划记忆

项目创建时，用户选择的方案会写入：

```text
Project.writing_style.wizard_planning_memory
```

典型字段：

```json
{
  "selected_draft": {
    "core_engine": "持续制造冲突的故事引擎",
    "reader_promise": "读者追读期待",
    "length_type": "长篇/中篇/短篇",
    "boundary_locks": ["不能违反的设定"],
    "long_term_plan": {}
  },
  "narrative_engine": {}
}
```

这些信息会进入后续章节生成上下文。

## 世界规则记忆

`WorldSetting` 中最关键的是：

- `hard_rules`：硬约束，绝对不能违背。
- `tone_rules`：文风氛围，控制叙事质感。
- `constraints`：生成限制，需要避开的内容或边界。
- `world_logic`：世界底层逻辑。

写作 prompt 会把这些作为硬上下文传入。

## 角色状态记忆

角色不仅有静态人设，还包括：

- `current_state`：当前状态。
- `language_fingerprint`：语言指纹。
- `relationship_dynamics`：关系动态。
- `growth_arc` / `growth_stages`：成长线。
- `faction_history`：组织履历。

章节生成时会压缩角色信息，避免所有角色全文塞入 prompt。

## 章节记忆

章节层记忆包括：

- `summary`：本章摘要。
- `connects_from`：承接上一章的状态。
- `connects_to`：章末给下一章留下的状态。
- `hook`：钩子。
- `story_state_snapshot`：章节状态快照。
- `blueprint`：章节蓝图。
- `key_events`：关键事件。
- `minor_events`：支线/伏笔事件。

这些字段比正文全文更适合作为长期上下文。

## 记忆中枢页面

入口：

```text
/projects/:projectId/memory-center
```

页面用于查看：

- 规则。
- 角色。
- 伏笔。
- 事件。
- 章节记忆。
- 风险。
- 组织。

记忆中枢的目标不是“展示所有数据”，而是让作者快速判断：

- 哪些设定已经锁定。
- 哪些角色状态需要维护。
- 哪些伏笔还没回收。
- 哪些章节存在连续性风险。

## 状态提取

章节完成后可以通过 `extract_state` 类任务提取状态变化：

- 角色是否获得新信息。
- 关系是否变化。
- 伏笔是否投放或回收。
- 世界状态是否改变。
- 主角目标是否更新。

相关 prompt：

```text
STATE_EXTRACT_PROMPT
GENERATE_STATE_SUMMARY_PROMPT
```

## 记忆污染问题

长篇 AI 写作容易出现记忆污染：

- AI 把临时建议当成已发生事实。
- AI 把用户吐槽当成设定。
- AI 把评审建议写进正文事实。
- AI 误认为未写章节已经发生。

应对策略：

1. 区分 `已写正文` 和 `后续规划`。
2. 区分 `用户调整意见` 和 `已落库设定`。
3. 大纲调整必须声明不会覆盖已写正文。
4. 章节生成只读取当前章之前的最近章节。
5. 修复任务必须限定替换范围。

## 未来增强

建议后续加入：

- 记忆版本历史。
- 记忆冲突检测。
- 伏笔状态自动流转。
- 角色状态 diff。
- 章节完成后自动抽取状态。
- 向量检索补充长程记忆。
- “事实库”和“草稿建议库”分离。
- 记忆编辑审计日志。

## 最佳实践

1. 不要把完整正文长期塞进 prompt。
2. 每章写完后更新摘要和状态。
3. 重要物品、能力、关系、伤势要进入角色或事件记忆。
4. 世界规则要写成可检查的硬约束。
5. 伏笔要标注投放阶段和回收阶段。
6. 角色语言指纹要具体到口头禅、句式、语气。
7. 大纲调整前先说明哪些章节已经写完。
8. 审计建议不要自动变成剧情事实。
