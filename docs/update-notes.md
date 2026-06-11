# 更新说明

本文记录近期对长篇连续性、数据库迁移和开源升级流程的关键更新。升级旧项目或二次开发前建议先阅读本页。

文档维护规则：每次更新都追加独立条目；即使是同一天的多次更新，也使用时间或主题区分，不覆盖、不改写已有更新说明。

## 2026-06-11 10:55 - 弧线连续性评分与工作台详情区优化

本次更新重点解决“弧线连续性分看不懂”“检查表显示缺项但没有修复按钮”“左侧弧线区域过于拥挤”的问题。

### 追加更新：卷轴详情与卷级结构评分

工作台新增“卷轴详情”抽屉，用于判断整卷是否像一个完整的网文阶段，而不是只检查单条弧线。

新增卷级结构分，评分维度包括：

- 卷目标：这一卷主角要完成什么，阶段承诺是否明确。
- 压力升级：本卷压力是否从开局到中段、卷末逐步变强。
- 弧线链：本卷各弧线之间是否有上承下启。
- 主角变化：卷末主角是否有身份、资源、认知、关系或能力变化。
- 章节承载：弧线数量和变化台阶是否足够支撑规划章节数。
- 伏笔安排：本卷是否有伏笔铺设、推进或阶段回收。
- 卷末钩子：是否把下一卷的新压力交出去。
- 角色势力：关键角色和势力是否承担行动功能。
- 风格承接：是否承接项目创建时的题材模型和总体风格。

左侧卷区域进一步精简，只显示：

- 卷结构分。
- 问题/提醒数量。
- 弧线数量。
- 卷详情入口。
- 调整概要。
- 调整本卷。

完整的卷概要、卷大纲、张力曲线、弧线链、章节承载、章节列表、卷级问题和维度评分统一放入“卷轴详情”抽屉。

卷轴详情抽屉新增操作：

- 调整概要。
- 调整本卷。
- 重拆弧线。
- 评审整卷。
- 查看上下文。
- 从弧线链进入弧线详情。

本次追加更新没有数据库结构变更，不需要执行升级 SQL。

### 数据库升级说明

本次更新没有数据库结构变更。

未新增、修改或删除：

- 表。
- 字段。
- 索引。
- 外键。
- Alembic revision。
- 应用内 `schema_migrations` 版本。

因此本次不需要执行升级 SQL，也没有新增升级 SQL 脚本。

### 弧线质量评分更新

弧线质量评分拆分为“结构问题”和“交接提醒”：

- `issues`：真正影响结构连续性的缺口，例如缺少开局状态、终点状态、上承交接、下启钩子、因果链、变化台阶等。
- `warnings`：非阻断提醒，例如当前弧线接收物和上一弧线交出物语义可能不一致。

评分含义明确为“结构连续性分”，不是剧情质量分。80 分以上通常表示结构可继续展开章节，但不代表剧情已经足够精彩。

### 修复按钮逻辑更新

前端现在会把结构检查表的实际缺项作为第二判断来源。

即使后端评分暂时显示通过，只要前端检查表发现：

- 缺上承交接。
- 缺下启钩子。
- 缺因果链。
- 缺变化台阶。
- 缺不可替代说明。

就会显示“按连续性修复”或“修复结构缺口”按钮。

修复指令也会携带具体缺失字段，例如：

```text
缺少上承交接(handoff_from_previous)
缺少变化台阶(arc_steps)
```

避免模型只做泛泛重写，而不补关键结构字段。

### 工作台前端更新

工作台新增“弧线详情”抽屉，集中展示：

- 结构检查。
- 当前结构连续性分说明。
- 弧线说明。
- 开局状态。
- 终点状态。
- 上承交接。
- 下启钩子。
- 因果链。
- 不可替代。
- 主角变化。
- 变化台阶。
- 关键节点。
- 伏笔计划。
- 角色引入。
- 势力引入。

弧线详情抽屉提供以下操作：

- 修复结构缺口。
- 优化交接。
- 重写。
- 拉长。
- 压缩。
- 展开章节。
- 批量写。

左侧弧线展开区进一步精简为导航和状态摘要，只保留：

- 弧线状态标签。
- 缺项数量。
- 提醒数量。
- 叙事功能标签。
- 详情入口。
- 必要时显示“按连续性修复”或“优化交接”。
- 章节列表、展开章节、批量写和评审入口。

重复的检查网格、长描述、开局/终点、上承/下启、主角变化、不可替代、重点角色、伏笔计划等内容统一放到弧线详情抽屉中，避免左侧空间拥挤。

### 后端能力更新

弧线展开和弧线修复后，后端会重新计算每条弧线的质量门禁，并返回：

- `score`
- `passed`
- `related_issues`
- `related_warnings`

“修复连续性”和“优化交接”两类动作在提示词中被明确区分：

- 修复连续性：优先补齐缺失或不合格字段，不改变本卷主线目标、章节范围和弧线核心功能。
- 优化交接：只优化前后弧线交接表达和 `continuity_chain`，不改变核心事件、章节范围和弧线功能。

## 2026-06-10 17:05 - 小说创建题材模型与总体风格升级

本次更新重构小说创建阶段的策划逻辑，重点解决“提示词被单一案例绑死”“只补设定合理性但不像网文”“后续大纲和正文忘记创建时风格”的问题。

### 数据库升级说明

本次更新没有数据库结构变更。

未新增、修改或删除：

- 表。
- 字段。
- 索引。
- 外键。
- Alembic revision。
- 应用内 `schema_migrations` 版本。

因此本次不需要执行升级 SQL，也没有新增升级 SQL 脚本。项目总体风格、题材模型和早期事件链写入现有 `projects.writing_style` JSON 字段。

### 创建策划逻辑更新

小说创建提示词新增“题材模型 + 总体风格”双轴：

- `type_model`：描述主类型、读者期待、核心读者奖励、冲突形态、升级/反馈循环和早期阻力模式。
- `tone_profile`：描述作品总体风格、叙事质感、节奏、幽默程度、情绪温度、语言手感和后续写作禁忌。
- `readability_gate`：检查方案是否符合类型读者期待、第一卷是否有具体事件链、主角早期是否主动、压力线是否服务主类型爽点。
- `first_volume_engine`：固定第一卷承诺、主角第一主动动作、早期可见阻力、第一反馈、第一代价和卷末钩子。
- `early_event_chain`：要求输出前期可直接写成章节的具体事件链，而不是只有宏观阶段。

提示词新增硬规则：

- 先判断“这个类型为什么好看”，再修补设定合理性。
- 不再把都市、商战、病线、融资线、复仇线等单一案例逻辑套到所有题材。
- 题材和风格分离：题材决定读者期待，风格决定讲述方式。
- 同一题材可以有不同风格，例如玄幻可以轻松、热血、冷峻或史诗。
- 当用户指出漏洞时，需要判断是细节缺失、因果断裂、爽点受损、题材模型错位还是主线方向错误；如果是后几类，必须重构项目引擎，不能只补漏洞。

### 后端能力更新

项目确认创建时，现在会把以下信息保存到 `project.writing_style`：

- `tone_profile`
- `type_model`
- `readability_gate`
- `first_volume_engine`
- `early_event_chain`
- `wizard_planning_memory`

后续生成会读取项目总体风格和题材模型：

- 世界观生成会把总体风格写入默认 `tone_rules`。
- 全书大纲、分卷、弧线展开、章节展开和正文写作会同时接收“项目总体风格 + 共享写作风格 Skill”。
- 项目总体风格优先级高于共享 Skill；Skill 只作为写作方法参考，不能覆盖项目自己的类型承诺和叙事气质。

### 前端能力更新

`/projects/create` 页面新增“总体风格偏好（可选）”：

- 轻松爽文。
- 热血燃向。
- 冷峻悬疑。
- 压抑现实。
- 温暖治愈。
- 黑色幽默。
- 史诗厚重。
- 甜宠轻喜。
- 克制文艺。
- 紧张高压。
- 群像权谋。
- 日常陪伴。

当前项目草案新增展示：

- 总体风格。
- 题材模型。
- 第一卷发动机。
- 早期事件链。
- 可读性闸门。

可选方案卡片中也会展示风格标签、核心引擎和追读承诺，便于创建前判断方案是否真的像目标类型小说。

## 2026-06-10 11:10 - 模型调用记录与 Token 审计

本次更新新增模型执行记录功能，用于追踪每一次真实 LLM 调用的上下文、请求、响应和 token 使用情况。

### 数据库升级说明

本次有数据库结构变更：新增 `llm_call_logs` 表。

新增升级脚本：

```text
docs/sql/20260610_0003_create_llm_call_logs.sql
```

新增应用内 schema migration：

```text
20260610_0003 create llm call logs table
```

新增 Alembic revision：

```text
backend/alembic/versions/20260610_0003_create_llm_call_logs.py
```

启动后端时，应用内迁移会自动创建表；如果需要手动升级数据库，也可以执行上面的 SQL 脚本。

### 新增记录字段

`llm_call_logs` 会记录：

- 项目 ID。
- 项目名。
- 任务 ID。
- 功能名称。
- 供应商 ID。
- 供应商名称。
- 供应商类型。
- 模型名。
- 请求类型。
- 调用状态。
- 系统提示词。
- 发送提示词。
- 得到的内容。
- 错误信息。
- 入 token。
- 出 token。
- 总 token。
- 调用耗时。
- temperature。
- max_tokens。
- 请求 payload。
- 响应元信息。
- 创建时间。
- 更新时间。

### 后端能力更新

新增统一模型调用日志服务：

- `backend/app/services/llm_call_logger.py`

模型调用记录接入位置：

- OpenAI / DeepSeek / OpenAI-compatible provider。
- Claude provider。
- Gemini provider。
- 模型供应商测试。
- AIService 中的结构生成、世界观生成、角色生成、势力生成、章节写作、审计、修订、状态提取、拆章等调用。

新增查询接口：

```text
GET /api/v1/llm-call-logs
GET /api/v1/llm-call-logs/summary
GET /api/v1/llm-call-logs/{log_id}
```

列表接口支持：

- 按项目 ID 过滤。
- 按项目名过滤。
- 按功能名称过滤。
- 按模型名过滤。
- 按状态过滤。
- 按提示词/返回内容/项目名/功能名关键词搜索。
- 分页。

汇总接口返回：

- 总调用次数。
- 失败次数。
- 成功率。
- 入 token 总数。
- 出 token 总数。
- 总 token。
- 按模型聚合。
- 按功能聚合。

### 前端能力更新

首页新增入口：

```text
调用记录
```

新增页面：

```text
/settings/llm-call-logs
```

页面能力：

- 查看总调用、成功率、入 token、出 token、总 token。
- 表格展示调用时间、项目、功能、模型、状态、token、耗时、提示词预览。
- 支持搜索提示词、返回内容、项目名、功能名。
- 支持项目名、功能、模型名、状态筛选。
- 点击详情查看完整系统提示词、发送提示词、得到的内容和响应元信息。

说明：该功能从上线后的新模型调用开始记录，历史调用不会反向补录。

## 2026-06-10 10:30 - 系统诊断、长任务稳定性与规划能力增强

本次更新把上一轮提出的系统能力优化落到可用界面和后端接口里，重点是让长篇生成从“黑盒等待”变成“可诊断、可追踪、可重试、可看上下文”的工作流。

### 数据库升级说明

本次更新没有数据库结构变更。

未新增、修改或删除：

- 表。
- 字段。
- 索引。
- 外键。
- Alembic revision。
- 应用内 `schema_migrations` 版本。

因此本次不需要执行升级 SQL，也没有新增升级 SQL 脚本。部署时只需要更新代码并重启后端服务即可。

### 后端能力更新

长线规划逻辑调整：

- 项目创建/策划阶段不再把“阶段/分卷递进”理解成固定数字模板。
- 长线阶段记忆从最多 6 段扩展到最多 8 段。
- 阶段数量改为按故事体量、题材复杂度和冲突层级自然拆分，避免强行凑数字。

长任务稳定性更新：

- LLM 请求读超时提升到 1 小时。
- 后台任务超时提升到 1 小时。
- 任务失败时补充可读错误信息，避免出现 `error: ""` 的空失败。
- 失败 detail 增加阶段、错误类型和超时信息。

JSON 生成稳定性更新：

- AI 返回 JSON 解析失败时，会进入自动修复链路。
- 修复后再次解析，降低大模型偶发格式错误导致整任务失败的概率。
- 新增提示词版本号 `PROMPT_VERSION`，便于排查当前使用的是哪套生成规则。

卷弧线连续性增强：

- 展开卷弧线时加入上一卷、当前卷、下一卷的连续性上下文。
- 会读取上一卷最后弧线、上一卷最后章节、章末状态、钩子、物件状态、外部压力和必须承接的问题。
- 新增弧线质量评分，检查开局状态、终点状态、交接钩子、因果链、不可替代价值、弧线台阶等。

章节蓝图闸门增强：

- 新增章节蓝图质量闸门。
- 检查 `connects_from`、`connects_to`、`key_events`、`arc_step_refs`、`state_delta` 和角色/组织入场条件。
- 章节存在蓝图风险时，前端会直接显示提示。

项目诊断接口新增：

```text
GET /api/v1/projects/{project_id}/wizard/project-health
GET /api/v1/projects/{project_id}/wizard/state-ledger
GET /api/v1/projects/{project_id}/wizard/context-preview
GET /api/v1/projects/{project_id}/wizard/world-rule-audit
GET /api/v1/projects/{project_id}/wizard/prompt-modules
GET /api/v1/projects/{project_id}/wizard/impact/chapter/{chapter_id}
```

这些接口覆盖：

- 项目整体健康度。
- 弧线连续性问题。
- 章节蓝图问题。
- 钩子密度。
- 事件密度。
- 伏笔追踪状态。
- 长篇疲劳警告。
- 状态账本。
- 当前生成上下文预览。
- 世界规则审计。
- 提示词模块清单。
- 修改某章可能影响的后续章节。

世界规则审计新增：

- 检查 `hard_rules`、`constraints`、`world_logic`、`special_rules`。
- 标记规则缺口、潜在冲突和风险。
- 检查世界规则是否绑定核心主题。
- 检查是否缺少代价规则、信息边界规则、组织/制度执行规则。
- 输出覆盖数量和修复建议。

提示词模块清单新增：

- 连续性规则。
- 弧线起承转交规则。
- 章节蓝图闸门。
- 去 AI 味规则。
- 角色入场坡度。
- 组织入场坡度。
- 网文追读节奏。
- 世界规则矛盾检测。

角色/势力生成任务改造：

- 正式生成从并行黑盒改为分段推进。
- 任务阶段包括读取上下文、生成角色档案、生成势力与关系矩阵、写入数据库、完成。
- 任务结果返回角色数、势力数、关系数和 `generation_mode: segmented`。
- 重试任务也沿用分段模式，不再退回旧逻辑。

生成上下文增强：

- 加入角色声音库。
- 加入势力规则书。
- 让章节写作、弧线展开和上下文预览能看到更完整的连续性依据。

### 前端能力更新

工作台顶部新增：

- `系统诊断` 按钮。

系统诊断抽屉新增页签：

- `健康`：展示项目健康度、弧线连续、蓝图质量、钩子密度、事件密度、伏笔追踪、世界规则分数。
- `状态账本`：展示出场人物、开放线索、章末钩子、关系变化、物件状态、外部压力。
- `上下文`：展示当前章节或当前卷的生成上下文。
- `规则`：展示世界规则审计分数、覆盖度、冲突、缺口、风险和建议动作。
- `模块`：展示当前启用的提示词模块、覆盖生成面和检查项。

卷和弧线区域更新：

- 卷区域新增 `上下文` 快捷按钮。
- 弧线行展示连续性标签和质量分。
- 展开弧线后，如果质量闸门未通过，会显示连续性警告。

章节区域更新：

- 当前章节存在蓝图风险时，标题下方直接显示警告。
- 章节工具栏新增 `影响分析` 按钮。
- 影响分析弹窗展示可能受影响章节和建议动作。

任务结果展示更新：

- 通用任务结果展示生成模式。
- 角色/势力任务展示角色数、势力数、关系数。
- 弧线任务展示弧线数量、弧线质量分和质量问题列表。

### 验证记录

后端语法检查通过：

```bash
cd backend
python3 -m py_compile app/api/v1/wizard.py app/services/ai_service.py app/services/context_builder.py app/services/task_manager.py
```

前端 TypeScript 检查通过：

```bash
cd frontend
/Users/mac/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node node_modules/typescript/bin/tsc --noEmit
```

服务状态：

- 后端已重启并监听 `http://127.0.0.1:8001`。
- 前端 Vite 保持监听 `http://127.0.0.1:5173`。

## 2026-06-09 11:24 - 写作链路 10 项增强

本次更新继续把质量控制点前移，从“写完后审计”扩展为“写前诊断、写中硬闸、写后状态校验、长篇健康聚合”。

新增写作前置诊断接口：

```text
POST /api/v1/projects/{project_id}/wizard/diagnose-chapter/{chapter_id}
```

该接口用于在生成正文前检查章节是否可以写，重点诊断：

- 上承状态是否具体。
- 正文开场前300字是否能接住至少2个具体后果。
- 新角色/新组织是否通过入场硬闸。
- `chapter_function` 是否明确。
- 本章是否不可替代。
- 章末钩子是否具体并能改变下一章压力。
- 角色声音和信息边界是否清楚。

章节蓝图新增字段：

- `chapter_function`：承接余波、短目标推进、关系试探、信息揭露、组织预热、正式冲突、反转打脸、桥接过渡、高潮爆发、章末钩子强化等。
- `opening_requirements`：正文前300字必须接住的具体状态。
- `prewrite_diagnosis_seed`：写前诊断的风险点。
- `indispensability_check`：如果删除本章，后文会断在哪里。
- `hook_design`：钩子类型、强度、是否改变下一章开场压力。
- `character_voice_constraints`：出场角色的语言指纹、禁忌说法和知识边界。
- `information_reveal_plan`：读者、主角、配角分别知道什么，本章最多允许揭露到哪里。
- `repair_priority_hint`：L1 句子、L2 段落、L3 场景补丁、L4 蓝图、L5 弧线修复的优先级建议。

正文写作新增硬闸：

- 本章必须服从 `chapter_function`。
- 开场前300字必须接住 `opening_requirements`。
- 本章结束后必须产生不可替代的状态变化。
- 章末钩子必须落到物件、声音、消息、动作、选择、身份暴露、规则反噬、关系破裂、敌人逼近或反常发现。
- 角色对白必须遵守 `character_voice_constraints`，不能突然变成作者说明书。
- 信息揭露必须遵守 `information_reveal_plan`，不能提前泄露主角/读者不该知道的信息。

写后状态提取新增二次校验：

- `state_extract_validation` 会检查身体、关系、信息、物件、外部压力、下一章开场要求、不可替代性和钩子是否提取完整。
- 如果缺状态，会记录 `missing_state` 和 `repair_instruction`。

章节审计新增维度：

- `opening_continuity`
- `chapter_function`
- `indispensability`
- `character_voice`
- `information_reveal`
- `state_memory`

质量仪表盘新增 `longform_health`：

- `arc_continuity`
- `character_consistency`
- `faction_entry_slope`
- `protagonist_state_memory`
- `hook_strength`
- `state_delta_density`
- `info_reveal_control`
- `ai_flavor_risk`

这些更新对应 10 个写作优化目标：

1. 写作前置诊断。
2. 章节功能类型。
3. 章节不可替代性检查。
4. 正文开场硬规则。
5. 章末钩子分级。
6. 角色声音连续性。
7. 信息揭露节奏表。
8. 写后状态提取二次校验。
9. 局部修复优先级。
10. 长篇质量仪表盘。

## 2026-06-09

### 长篇连续性增强

本次更新把“弧线”从固定章节数的小故事块，调整为长篇小说里的连续变化阶段。

新增弧线结构字段：

- `arc_type`：弧线类型，例如主线目标变化、关系变化、信息揭露、组织接触、反派压力、资源状态、身份风险、余波过渡、卷核心危机。
- `closure_level`：弧线闭合程度，支持开放、半闭合、阶段闭合、完全闭合。
- `must_remain_open`：弧线结尾必须留给后文的问题、压力、关系裂痕或物件状态。
- `bridge_chapter_plan`：弧线之间是否需要桥接章，以及桥接章要处理的余波、伤势、关系反应、组织预热和新目标形成。
- `protagonist_continuity_state`：主角身体、心理、目标、风险、关系、资源和认知状态。
- `character_lifecycle_updates`：关键角色从未预热到正式登场、临时合作、稳定关系等状态变化。
- `faction_lifecycle_updates`：组织从未出现到传闻、痕迹、外围成员、规则压迫、正式接触等状态变化。
- `arc_review_targets`：后续弧线审查重点。
- `blueprint_repair_targets`：章节蓝图展开时必须优先修复的问题。
- `compatibility_notes`：旧小说兼容说明。

新的生成规则强调：

- 弧线不是默认 7-8 章一个小故事。
- 弧线之间使用“起承转交”，不是把每段都完全收束。
- 下一弧线必须由上一弧线后果逼出来。
- 关键角色和组织必须有入场坡度，不能空降、立刻给答案或立刻和主角深度绑定。
- 主角状态不能在换弧线后清零。

### 前置审查接口

新增两个结构审查任务，用于在正文生成前拦截突兀和断裂。

弧线结构审查：

```text
POST /api/v1/projects/{project_id}/wizard/review-arc-structure/{volume_id}
```

检查重点：

- 弧线是否像独立小故事块。
- 前后弧线 handoff 是否具体。
- 弧线是否过度闭合。
- 角色/组织是否有预热。
- 主角状态是否连续。
- 是否需要桥接章。

章节蓝图审查：

```text
POST /api/v1/projects/{project_id}/wizard/review-chapter-blueprints/{volume_id}
```

检查重点：

- 章节是否从上一章后果开始。
- 新角色和新组织是否通过登场硬闸。
- 主角伤势、目标、风险、关系、资源、认知是否连续。
- 是否存在删掉后前后仍可顺接的空转章节。
- 章末钩子是否具体。
- 弧线最后一章是否把未解压力交给下一弧线。

这两个审查只写回审查结果和修复建议，不自动改写旧正文、旧摘要或旧角色关系。

### 数据库迁移更新

新增应用内 schema migration 版本：

```text
20260609_0001 add narrative continuity columns and safe arc bridge metadata
20260609_0002 add project continuity compatibility version fields
```

新增 Alembic revision：

```text
backend/alembic/versions/20260609_0001_add_narrative_continuity_columns.py
backend/alembic/versions/20260609_0002_add_project_continuity_versions.py
```

启动时会：

1. 执行 `Base.metadata.create_all()`，保证新库能初始化。
2. 执行未应用的 schema migration。
3. 把版本写入 `schema_migrations`。

迁移策略是非破坏性的：

- 只追加字段。
- 只补结构索引。
- 不自动重写小说正文。
- 不自动重拆旧弧线。
- 不自动修改章节摘要。
- 不自动改变角色关系。
- AI 重新规划必须由用户主动触发。

### 旧小说兼容

`projects` 表新增兼容版本字段：

- `project_schema_mode`
- `arc_generation_version`
- `chapter_blueprint_version`
- `continuity_upgrade_notes`

旧项目默认保持 `legacy`。只有用户主动重新生成弧线或重新展开章节后，项目才会记录为 `continuity_v1`。

这意味着升级程序本身不会强制改写旧小说，只会让后续主动生成动作使用新的连续性规则。

### 升级工具

新增 schema 检查脚本：

```bash
cd backend
python -m app.scripts.check_schema
```

示例输出：

```text
expected_head: 20260609_0002
applied: 20260609_0001, 20260609_0002
missing: none
status: ok
```

新增 SQLite 备份脚本：

```bash
cd backend
python -m app.scripts.backup_db
```

该脚本只支持 SQLite。PostgreSQL 请使用 `pg_dump`、托管平台快照或数据库自带备份方案。

### 依赖补全

后端依赖文件补充：

```text
python-dotenv==1.0.1
email-validator==2.2.0
```

原因：

- `.env` 读取需要 `python-dotenv`。
- `pydantic.EmailStr` 需要 `email-validator`。

新环境升级后建议重新安装依赖：

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

### 推荐升级步骤

SQLite 本地部署：

```bash
cd backend
source .venv/bin/activate
python -m app.scripts.backup_db
pip install -r requirements.txt
python -m app.scripts.check_schema
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
python -m app.scripts.check_schema
```

Docker 或 PostgreSQL 部署：

1. 停止后端服务。
2. 备份数据库。
3. 拉取新代码。
4. 重新构建镜像或安装依赖。
5. 启动后端，让 migration 自动执行。
6. 使用 `python -m app.scripts.check_schema` 或数据库查询确认 `schema_migrations`。
7. 打开项目确认旧小说正文和章节仍保持原状。

## 注意事项

- 新审查接口不会自动修复问题，需要前端或调用方读取审查结果后决定是否重新生成弧线/章节。
- 旧项目不会自动升级为 `continuity_v1`，只有主动重新生成相关结构时才更新版本标记。
- 若用户已经手动改过正文或章节摘要，migration 不会覆盖这些内容。
- 后续仍建议补充 migration 单元测试、PostgreSQL 完整升级回归测试和更细的 UI 操作入口。
