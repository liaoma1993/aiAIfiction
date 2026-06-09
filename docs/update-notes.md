# 更新说明

本文记录近期对长篇连续性、数据库迁移和开源升级流程的关键更新。升级旧项目或二次开发前建议先阅读本页。

文档维护规则：每次更新都追加独立条目；即使是同一天的多次更新，也使用时间或主题区分，不覆盖、不改写已有更新说明。

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
