# 更新说明

## 2026-06-24 创作流程整体优化

围绕「创意层套路化、写作不流畅、流程不清晰」三个老问题做了一轮系统性升级。改动按使用顺序展开，从创建项目一路覆盖到章节正文。

---

### 一、创意生成层抗陈词滥调

**问题**：以前创建小说时，AI 给的故事建议反复落入「被废秘密 / 灭门复仇 / 重生爽文 / 系统觉醒」这类老套路；3-5 个建议看起来都差不多。

**做法**
- `STORY_SUGGESTIONS_PROMPT` 重写：加陈词滥调入口母题黑名单、入口形态多样化（`story_entry_type` 7 选 1）、情绪光谱强约束（必须至少 1 个轻快/治愈/反差幽默/烟火气）、细分品类锁定（不能直接给"玄幻/都市"，必须落到修仙/职场/民俗志怪等具体细分）。
- `PROJECT_CHAT_PROMPT` 同步加细分品类硬规则、`type_model.primary_subgenre / subgenre_reader_expectation / subgenre_anti_pattern` 字段。
- `_do_plan_chat` 内部加 `boundary_locks diff` 校验：AI 擅自改 title/primary_subgenre/core_engine/protagonist_first_move 任一核心字段时，在 assistant_reply 顶部 prepend「【方向变动提醒】」。

**配套：用户拒绝方向短期记忆**
- 新表字段 `project_plan_sessions.rejected_entries` (migration `20260623_0005`)。
- 新端点 `POST /projects/plan-session/reject`：用户在 CreateProjectPage 点「👎 不喜欢这个方向」时记录被拒方向（title/primary_subgenre/story_entry_type/core_engine/reason）。
- `_do_plan_chat` + `generate_story_suggestions` 都会把已拒方向注入 prompt，下次生成 AI 必须避开。

---

### 二、角色 / 势力 / 大纲层去公式化

- `CHARACTERS_PROMPT`：强制至少 1 个「无叙事功能」角色（生活搭子 / 旁观者 / 反例对照），每个角色至少 1 个反类型特质（铁血将军会讲冷笑话等）。新字段 `non_function_role` / `anti_archetype_trait` 让 AI 自报交差。
- `FACTIONS_PROMPT`：强制至少 1 个「独立利益第三方」势力，每个强势力必须有可见的内部脆弱面 + 非典型派系。新字段 `independent_third_party` / `visible_internal_weakness` / `non_mainstream_faction`。
- `OUTLINE_PLAN_PROMPT`：新增 `emotional_arc_curve` 输出（global_shape + per_volume tone_arc + buffer_rule），每个 volume 草案带 `tone_arc / primary_emotion / buffer_required`。
- `EXPAND_VOLUME_OUTLINE_PROMPT`：接收 `tone_arc_constraint` 作为硬约束，本卷情绪走向必须严格遵守 buffer_required 标志。

---

### 三、创建流程瘦身：超长大纲与卷轴拆分解耦

**问题**：以前向导第 4 步一次性把「全书概览 + 多卷拆分 + 逐卷扩 outline」全做了，AI 调用多、时间长，且过早固化卷结构。

**做法**
- Project 模型加 `master_outline: Text` + `pending_volume_plan: JSON` (migration `20260623_0004`)。
- `_do_generate_master_outline` 只产 master_outline（六层结构：主角弧线 / 主题 / 核心对抗压力 / 关键关系演变 / 全书伏笔回收网 / 情绪节奏曲线，≥3000 字硬下限，严禁分卷叙述）+ 缓存 volumes 草案到 `pending_volume_plan`，不再创建 Volume 记录。
- `_do_split_volumes`（新）：用户在工作台主动触发，从 `pending_volume_plan` 读出草案 → 逐卷调 `expand_volume_outline` 扩到 1000+ 字 → 落表创建 Volume。
- 新端点 `POST /wizard/split-volumes`。

**前端**
- 向导第 4 步 `StepOutline` 重写：展示 master_outline 全文 + 分卷骨架预览卡片。
- 工作台「未拆卷态」：左侧目录顶部显示「📋 全书超长大纲」卡片 + 分卷骨架 mini 列表 + 「拆分卷轴」按钮。
- 工作台导航栏新增「📋 全书大纲」按钮，任何时候都能弹 Modal 预览全书大纲 + 分卷骨架。
- 旧「大纲」按钮重命名为「分卷大纲」避免语义混淆。

---

### 四、对话式重生成大纲（新功能）

**问题**：原本的「重新生成大纲」是一键覆盖，AI 拿到的输入跟上次完全一样，结果几乎不变，烧 token 没意义。

**做法**
- 新 prompt `MASTER_OUTLINE_REVISE_CHAT_PROMPT`：AI 扮演大纲编辑，先复述用户反馈，再根据明确程度决定给修订版本还是问澄清问题；严守 OUTLINE_PLAN_PROMPT 的六层结构 + 反陈词滥调 + 情绪光谱约束。
- 新 AI 方法 `ai.revise_master_outline_chat(messages, current_outline, current_volume_plan, ...)`。
- 新端点：
  - `POST /wizard/revise-outline-chat`（异步任务，返回 task_id；不写库）
  - `POST /wizard/apply-outline-revision`（同步落库；带 force 保护，已写正文必须 force=true）
- 工作台「重新生成大纲」Modal 改造为对话式双栏：
  - 左栏（60%）：消息流 + 4 个快捷反馈预设 + 输入框 + 提交按钮
  - 右栏（40%）：「当前大纲（已落库）」/「最新草案」Tab 切换预览
  - assistant 消息含 revised_outline 时显示「应用这一版」按钮，有正文时需输入「确认覆盖」
  - 不持久化对话状态，关 Modal 即清空

---

### 五、样章预览（新功能）

**问题**：以前用户要走完整个向导才能看到 AI 写的字，到时候才发现文笔/风格不对就晚了。

**做法**
- 新端点 `POST /wizard/preview-sample-chapter`：基于 master_outline 调 `ai.write_chapter` 写约 2500 字样章，不入库。
- 向导第 4 步 `StepOutline` 加「📝 生成首章样章预览」按钮 + Modal（可选填开场场景）。

---

### 六、章节正文流畅度三件套

**问题**：写正文时断片、不流畅、桥段重复（"她攥紧拳头"、"风掠过……"反复出现）。

**做法**
1. **前章末段原文直接喂下一章**：`prev_chapter.content[-500:]` → `[-1200:]`，并改标签为「结尾原文（语感、地点、动作、未完成对话必须延续）」，让 AI 顺着语感写，不靠猜。
2. **同弧线已写章节做"避免重复"清单**：新 helper `_collect_arc_anti_repetition_notes()` 扫同弧线最近 5 章 prev 章节的 `title / key_events / hook`，拼成「已写章节 + 已发生事件 + 已用钩子 + 换通道规则」注入 chapter_summary。
3. **写完窄口自评 + 一次重写**：新 helper `_auto_flow_repetition_pass()` 写完后跑 `audit_chapter`；只在 critical 级别命中 continuity/scene_clarity/ai_flavor/dialogue/readability/repetition 维度时才触发 `revise_chapter` 重写一次。默认开启，与原有 strict `auto_quality_check` 互斥。

---

### 七、弧线拆分硬约束

**问题**：本卷大纲明显有 5 个叙事阶段（开篇/发展/转折/高潮/收束），AI 却拆成 4 弧线，把"转折+高潮"两个独立段塞进同一条 14 章的弧线，双高潮叠加。

**做法**
- `EXPAND_VOLUME_ARCS_PROMPT` 加「弧线分布硬指标」段：单弧线 ≤ `single_arc_max_chapters` 章、本卷至少 `min_arc_count` 条弧线、独立叙事段必须落到独立弧线、禁止双高潮叠加。新增 `retry_note` 占位。
- 阈值动态推导：`single_arc_max = max(8, min(12, ⌈本卷章数 × 0.35⌉))`、`min_arc_count = max(4, ⌈本卷章数 / 9⌉)`。
- 后处理硬闸：`_audit_arc_distribution()` 检测违规（超章、不足、main_change_object 重复），命中自动 retry 一次（带 retry_note 喂回违规说明，逼 AI 完全重写）。
- 重试后仍违规 → 写入 `arc_quality.distribution_violations` 不再 retry，避免成本爆炸。

---

### 八、写作风格指纹

- 新 AI 方法 `ai.extract_style_fingerprint(samples)`：提取句长分布、对白密度、心理 vs 动作比例、角色口头禅、典型句式、避免词组、情绪基调。
- 第 3 章写完后通过 `background_task_types` 自动触发提取，存到 `project.writing_style.fingerprint`。
- 第 4 章起 `write_chapter` prompt 注入「全书语言指纹——必须保持」段，解决风格漂移。

---

### 九、UX 杂项

- **任务列表排序**：`list_tasks_persisted` 从「running 全前置 + finished[:30]」改为「纯按 created_at 倒序」，running 全保留 + 最近 50 finished，时间穿插的任务不再"乱"。
- **任务列表时间显示**：从只显示「时:分:秒」改为「月-日 时:分:秒」，显式 `timeZone: 'Asia/Shanghai'`——浏览器无论哪个时区都显示东八区时间。
- **TASK_LABELS 补全**：`split_volumes / preview_sample_chapter / extract_style_fingerprint / project_plan_chat / generate_outline_draft / generate_story_bible / diagnose_chapter / revise_outline_chat` 的中文翻译。
- **重新生成大纲安全保护**：`_do_generate_master_outline` + `_do_apply_outline_revision` 都加 `force` 参数，默认拒绝在有正文的情况下覆盖（会级联清空 Volume/Chapter）。前端 Modal 需输入「确认覆盖」才放行。

---

### 数据库迁移

| revision | 内容 |
|---|---|
| `20260623_0004` | `projects` 表加 `master_outline TEXT` + `pending_volume_plan JSON` |
| `20260623_0005` | `project_plan_sessions` 表加 `rejected_entries JSON` |

升级方式：`cd backend && alembic upgrade head`

### 新增 API

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/projects/plan-session/reject` | 记录用户拒绝的故事建议 |
| POST | `/projects/{id}/wizard/split-volumes` | 从超长大纲拆出卷轴 |
| POST | `/projects/{id}/wizard/preview-sample-chapter` | 生成首章样章预览（不入库）|
| POST | `/projects/{id}/wizard/revise-outline-chat` | 对话式修订超长大纲（异步）|
| POST | `/projects/{id}/wizard/apply-outline-revision` | 应用对话中的某版草案（带 force 保护）|
| POST | `/projects/{id}/wizard/generate-outline?force=bool` | 重新生成超长大纲（带 force 保护）|

### 验证清单

1. 创建项目走故事建议 → 3-5 个方案的 `story_entry_type` 不重复，`emotional_temperature` 至少 1 个轻快/治愈，没出现"被废/灭门"扎堆
2. 在某个建议上点👎 → reject 记录入库 → 重新生成 → 不再出现同类入口
3. 向导第 4 步看到 ≥3000 字 master_outline + 分卷骨架卡片；点「样章预览」能拿到 ~2500 字正文
4. 工作台未拆卷态显示骨架 → 点「拆分卷轴」→ AI 逐卷扩写 → 左侧目录正常显示卷与章节
5. 拆卷展开弧线时，单条弧线章数被强制 ≤ 12（40 章卷场景），弧线数 ≥ 5；命中违规会自动 retry
6. 工作台点「对话修订大纲」→ 多轮反馈 → 「应用这一版」覆盖；项目有正文时需输入「确认覆盖」
7. 写完第 3 章后查 `project.writing_style.fingerprint`，第 4 章 prompt 应注入指纹
8. 任务列表按时间倒序，时间显示「月-日 时:分:秒」东八区
