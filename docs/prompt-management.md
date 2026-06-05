# 提示词管理

AI Fiction Studio 的提示词不是孤立模板，而是围绕小说生产流程分层组织。

当前实现主要位于：

```text
backend/app/services/ai_service.py
```

## 系统角色

系统定义了四类 AI 角色：

| 常量 | 角色 | 使用场景 |
|---|---|---|
| `SYSTEM_ARCHITECT` | 小说结构顾问 | 项目策划、大纲、弧线、章节结构 |
| `SYSTEM_DESIGNER` | 世界观与人物塑造专家 | 世界观、角色、势力 |
| `SYSTEM_WRITER` | 类型小说家 | 正文写作、章节生成 |
| `SYSTEM_EDITOR` | 文学编辑 | 审计、修复、质量评估 |

这个分层的目的，是避免所有任务都用同一种“万能助手”口吻。

## Prompt 清单

| Prompt | 职责 |
|---|---|
| `STORY_SUGGESTIONS_PROMPT` | 根据灵感生成故事方案 |
| `PROJECT_CHAT_PROMPT` | 项目策划多轮对话 |
| `WORLD_SETTING_PROMPT` | 世界观生成 |
| `CHARACTERS_PROMPT` | 角色生成 |
| `FACTIONS_PROMPT` | 势力生成 |
| `OUTLINE_PLAN_PROMPT` | 全书大纲生成 |
| `EXPAND_VOLUME_ARCS_PROMPT` | 卷弧线拆分 |
| `REVISE_VOLUME_ARC_PROMPT` | 弧线拉长、压缩、重写 |
| `EXPAND_ARC_CHAPTERS_PROMPT` | 弧线展开章节 |
| `WRITE_CHAPTER_PROMPT` | 章节正文写作 |
| `CHAPTER_AUDIT_PROMPT` | 章节质量审计 |
| `REVIEW_CHAPTERS_PROMPT` | 弧线/章节结构评审 |
| `REVIEW_REPAIR_PLAN_PROMPT` | 按评审生成修复方案 |
| `CHAPTER_REVISION_PROMPT` | 章节优化、局部修复、整章重写 |
| `STATE_EXTRACT_PROMPT` | 提取章节状态变化 |
| `CHAPTER_BLUEPRINT_PROMPT` | 生成章节蓝图 |
| `GENERATE_STATE_SUMMARY_PROMPT` | 生成章节后状态摘要 |
| `SPLIT_CHAPTER_PROMPT` | 长章节智能拆分 |
| `SPLIT_CHAPTER_META_PROMPT` | 拆分后章节元信息 |
| `ADJUST_OUTLINE_PROMPT` | 大纲调整 |
| `ADJUST_OUTLINE_CHAT_PROMPT` | 对话式整理大纲调整意见 |

## Prompt 设计原则

### 1. 强制 JSON 输出

绝大多数 AI 调用要求返回 JSON。这样前端和后端可以稳定消费：

```json
{
  "summary": "...",
  "warnings": [],
  "chapters": []
}
```

`AIService._ask()` 会：

1. 调用 `llm.chat_json()`。
2. 如果 JSONDecodeError，退回普通 chat。
3. 清理 markdown code fence。
4. 再次解析 JSON。
5. 失败则抛出 `AI 返回格式异常`。

### 2. 分任务约束

不同任务必须有不同边界：

- 写章节可以扩写动作、对白、场景。
- 审计只能指出问题和定位原文。
- 局部修复只能替换选区，不能覆盖整章。
- 故事大概调整只能改卷概要。
- 大纲调整不能覆盖已写正文。

### 3. 长篇连载优先

大纲、弧线和写作提示词都要考虑：

- 长篇目标字数。
- 前 20 万字吸引力。
- 阶段性目标。
- 反派压力。
- 主角成长。
- 伏笔投放和回收。
- 章节边界和章末钩子。

### 4. 网文可读性优先

写作和修复提示词应避免：

- 抽象隐喻堆叠。
- 过度文学化。
- 场景映射过多。
- 说明书式心理总结。
- 领导讲话式对白。
- AI 模板句。

推荐要求：

- 关键动作可见。
- 目标明确。
- 冲突听得懂。
- 每段服务剧情或人物。
- 读者不用反复琢磨才能知道发生了什么。

## 对话式调整 Prompt

`ADJUST_OUTLINE_CHAT_PROMPT` 用于“先沟通，不落库”：

```text
用户说：这卷太散，前面不抓人，别合并章节。
AI 输出：
- assistant_reply：给用户看的回复。
- consolidated_instruction：可直接传给大纲调整接口的最终指令。
- next_questions：可选追问。
```

这样设计有两个好处：

1. 用户不用一次写完整需求。
2. 真正修改数据库前，有一个可读的最终调整要求。

## 局部修复 Prompt

`CHAPTER_REVISION_PROMPT` 支持多种模式：

| 模式 | 作用 |
|---|---|
| `make_easy` | 改易懂 |
| `dialogue_natural` | 对白自然化 |
| `punctuation_fix` | 标点修复 |
| `de_ai` | 去 AI 味 |
| `add_scene_texture` | 增加画面感 |
| `strengthen_hook` | 强化钩子 |
| `strengthen_readthrough` | 强追读 |
| `quality_light_fix` | 按审计轻修 |
| `audit_full_rewrite` | 按审计重写 |
| `target_sentence_fix` | 只修原句 |
| `target_paragraph_fix` | 只修段落 |
| `target_context_fix` | 深修局部上下文 |

局部修复的关键约束：

- 必须精确定位原文。
- 只返回替换后的局部文本。
- 不允许输出整章。
- 不允许改变核心剧情。
- `target_context_fix` 可以补 1-3 句因果桥，但仍然只替换局部文本块。

## Prompt 修改建议

修改提示词时建议遵循：

1. 先明确任务边界。
2. 再明确输入数据。
3. 再明确输出 JSON schema。
4. 再明确禁止行为。
5. 最后补写风格偏好。

不要把所有规则堆进一个超级 prompt。应该让不同工作流只携带必要规则。

## 未来可视化管理方案

当前提示词在代码里，适合快速迭代。开源后建议演进为：

```text
Prompt Registry
├── prompt_key
├── version
├── system_role
├── template
├── schema
├── enabled
├── project_override
├── created_by
└── updated_at
```

可以支持：

- 页面编辑。
- 版本回滚。
- Prompt diff。
- Prompt 测试样例。
- 项目级覆盖。
- 模型级覆盖。
- A/B 实验。

## Prompt 测试建议

每个关键 prompt 至少保留 3 类样例：

1. 正常输入。
2. 信息缺失输入。
3. 冲突输入。

例如大纲调整：

- 正常：用户要求加强反派压力。
- 信息缺失：用户只说“不好看”。
- 冲突：用户要求推翻已写正文。

测试目标不是“文笔最好”，而是：

- JSON 稳定。
- 不越权。
- 能定位问题。
- 能遵守已写事实。
- 能输出可执行结果。
