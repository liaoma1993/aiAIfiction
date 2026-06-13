import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.models.project import Project
from app.models.volume import Volume
from app.models.writing_style_skill import WritingStyleSkill
from app.services.wizard.planning import (
    _as_string_list,
    _draft_meta_from_style,
    _format_tone_profile,
    _format_type_model,
    _selected_draft_from_project,
)

DEFAULT_WRITING_CONTROLS = {
    "readability_mode": "easy",
    "pace_mode": "standard",
    "dialogue_density": "medium",
    "description_density": "standard",
    "humor_level": "light",
    "information_density": "medium",
    "punctuation_style": "standard",
    "chapter_template": "standard",
    "early_grip_mode": "auto",
    "write_flow_mode": "fast",
    "auto_prewrite_check": "rule",
    "auto_quality_check": False,
    "auto_light_fix": False,
    "async_quality_check": True,
    "async_state_extract": True,
    "context_budget": "standard",
}

def _readability_guidance(controls: dict | None) -> str:
    controls = controls or {}
    mode = controls.get("readability_mode") or controls.get("clarity_mode") or "easy"
    guidance = {
        "simple": """
模式：简单直白。
- 每一段只推进一个动作、一个发现或一次对话，不要多线并写。
- 少用隐喻、象征、跳跃式心理描写和复杂倒叙。
- 重要信息要在角色行动或对话后立刻给出结果，让读者不用回看也能明白。
- 句子偏短，段落偏短，因果关系直接写清楚：谁做了什么，为什么，造成什么后果。
- 悬念可以保留，但不能靠故意省略关键信息制造难懂。
- 不写“意象映射”“信念地基”“时代洪流”这类抽象表达，改写成具体人和具体事。
- 开场 300 字内必须出现可见事件或麻烦，不能先抒情、先介绍背景。
""",
        "easy": """
模式：通俗易懂。
- 保留类型小说爽点和现场感，但优先让读者一遍读懂。
- 每个场景先锚定地点、人物、目标，再写冲突，不要一上来堆设定名词。
- 复杂设定拆成小块，通过动作和对话逐步露出；每次只解释当前剧情必需的一点。
- 转折前后写清因果：上一件事怎样逼出下一件事。
- 对话可以有潜台词，但关键剧情信息不要藏得太深。
- 写法按连载网文处理：短目标、强阻力、快反馈、章末具体钩子。
- 环境描写点到为止，不能连续铺陈光影、气味、象征和心理映射。
- 主角每章要有可见动作，哪怕是试探、装傻、递报告、顶一句、查一份文件。
""",
        "normal": """
模式：正常连载。
- 清晰度与文学质感平衡，允许一定潜台词和伏笔，但主线因果必须明确。
- 场景、动作、对话、心理交替推进，不要长篇解释，也不要故意写得晦涩。
- 读者可以思考伏笔，但不应该因为表达绕而看不懂当前发生了什么。
""",
        "dense": """
模式：细腻烧脑。
- 可以提高信息密度、伏笔密度和心理层次，但必须保证场景动作线清楚。
- 允许非直白表达和多重含义，但每个关键转折仍要有可追溯因果。
- 不要为了复杂而复杂；复杂来自角色动机、信息差和代价，不来自绕句子。
""",
    }
    return guidance.get(mode, guidance["easy"]).strip()

def _project_writing_controls(project: Project | None) -> dict:
    style = project.writing_style if project else {}
    if not isinstance(style, dict):
        style = {}
    saved = style.get("writing_controls") or {}
    if not isinstance(saved, dict):
        saved = {}
    if "write_flow_mode" not in saved:
        saved = {
            **saved,
            "write_flow_mode": "stable_draft",
            "auto_light_fix": False,
            "auto_quality_check": False,
            "async_quality_check": False,
        }
    return {**DEFAULT_WRITING_CONTROLS, **saved}

def _merge_writing_controls(project: Project | None, controls: dict | None) -> dict:
    merged = _project_writing_controls(project)
    if isinstance(controls, dict):
        merged.update({k: v for k, v in controls.items() if v is not None and v != ""})
    if str(merged.get("write_flow_mode") or "").lower() in {"精修", "polish", "strict", "quality"}:
        merged["auto_prewrite_check"] = "ai"
        merged["auto_quality_check"] = True
        merged["async_quality_check"] = False
        merged["async_state_extract"] = False
    return merged

def _writing_controls_guidance(controls: dict | None) -> str:
    controls = controls or {}
    pace = {
        "slow": "节奏偏慢，允许更多生活细节和情绪铺垫，但每段仍要有叙事功能。",
        "standard": "节奏标准，场景推进、人物反应、信息揭示保持均衡。",
        "fast": "节奏偏快，减少绕路解释，冲突和结果更快落地。",
        "爽文快推": "爽文快推，压迫、反转、反馈要明确，读者获得感优先。",
    }.get(str(controls.get("pace_mode", "standard")), "节奏标准，场景推进、人物反应、信息揭示保持均衡。")
    dialogue = {
        "low": "对白比例较低，用动作和场景推进，关键对白短而有力。",
        "medium": "对白比例中等，对话服务冲突和人物关系。",
        "high": "对白比例较高，用对话推动冲突、误会、吐槽和信息交换，但不能变成问答说明书。",
    }.get(str(controls.get("dialogue_density", "medium")), "对白比例中等，对话服务冲突和人物关系。")
    description = {
        "light": "描写密度偏轻，少写静态景物，多写动作中的细节。",
        "standard": "描写密度标准，每个重要场景至少有声音、光线、气味、温度或触感中的一项。",
        "rich": "描写更细腻，但不能牺牲可读性，不要堆形容词。",
    }.get(str(controls.get("description_density", "standard")), "描写密度标准，每个重要场景至少有感官锚点。")
    humor = {
        "none": "不主动制造幽默，保持剧情气质。",
        "light": "轻微幽默，用角色反应、吐槽或尴尬细节调味，不破坏剧情。",
        "medium": "中等幽默，允许更多吐槽、反差和社死反馈，但主线仍要推进。",
        "strong": "强幽默，冲突解决和人物互动要有明显笑点，但不能让人物降智。",
    }.get(str(controls.get("humor_level", "light")), "轻微幽默，用角色反应、吐槽或尴尬细节调味。")
    info = {
        "low": "信息密度低，复杂设定必须拆开，一章只解释当前必要的信息。",
        "medium": "信息密度中等，设定、伏笔、动作交替出现。",
        "high": "信息密度高，但每个新信息都必须有上下文和后果，不能堆名词。",
    }.get(str(controls.get("information_density", "medium")), "信息密度中等，设定、伏笔、动作交替出现。")
    template = {
        "standard": "章节结构：开场承接 -> 当前目标 -> 冲突推进 -> 新信息/代价 -> 章末钩子。",
        "爽点章": "章节结构：压迫/误判 -> 主角行动 -> 反转反馈 -> 余波 -> 新威胁。",
        "搞笑章": "章节结构：正常目标 -> 意外变量 -> 社死/误会升级 -> 反向解决 -> 围观后果。",
        "悬疑章": "章节结构：异常细节 -> 错误解释 -> 新证据 -> 推翻判断 -> 更大疑点。",
        "感情章": "章节结构：表面冲突 -> 误会或试探 -> 细节泄露真心 -> 靠近/退缩 -> 情绪钩子。",
        "战斗章": "章节结构：目标 -> 地形/限制 -> 试探 -> 代价 -> 破局 -> 余波。",
        "日常过渡章": "章节结构：生活场景 -> 关系推进 -> 小伏笔 -> 主线轻推 -> 温和钩子。",
    }.get(str(controls.get("chapter_template", "standard")), "章节结构：开场承接 -> 当前目标 -> 冲突推进 -> 新信息/代价 -> 章末钩子。")
    return "\n".join([pace, dialogue, description, humor, info, template])

def _clip_style_line(value, limit: int = 360) -> str:
    text = value if isinstance(value, str) else json.dumps(value or "", ensure_ascii=False)
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "..."

def _format_writing_style_skill(skill: WritingStyleSkill | None, phase: str = "writing") -> str:
    if not skill:
        return "未启用写作风格 Skill。"
    profile = skill.style_profile or {}
    lines = [
        f"Skill 名称：{skill.name}",
        f"核心风格：{_clip_style_line(profile.get('core_style') or skill.description, 500)}",
    ]
    phase_key = {
        "creation": "creation_guidance",
        "outline": "outline_guidance",
        "writing": "writing_guidance",
    }.get(phase, "writing_guidance")
    if profile.get(phase_key):
        lines.append(f"阶段指导：{_clip_style_line(profile.get(phase_key), 700)}")
    workflow_usage = profile.get("workflow_usage")
    workflow_key = {
        "creation": "creation",
        "outline": "outline",
        "writing": "writing",
    }.get(phase, "writing")
    if isinstance(workflow_usage, dict):
        workflow_rules = workflow_usage.get(workflow_key) or []
        if isinstance(workflow_rules, list) and workflow_rules:
            lines.append(f"当前流程用法：{_clip_style_line('；'.join(str(x) for x in workflow_rules[:6]), 800)}")
    taxonomy = profile.get("technique_taxonomy")
    if isinstance(taxonomy, dict):
        taxonomy_parts = []
        for key, label in [
            ("character", "人物"),
            ("emotion", "情绪"),
            ("world", "世界"),
            ("scene", "场景"),
            ("conflict", "冲突"),
            ("relationship", "关系"),
            ("detail", "细节"),
            ("information_gap", "信息差"),
            ("payoff", "反馈"),
            ("language", "语言"),
        ]:
            values = taxonomy.get(key)
            if isinstance(values, list) and values:
                taxonomy_parts.append(f"{label}：" + "；".join(str(x) for x in values[:2]))
        if taxonomy_parts:
            lines.append(f"技法谱系：{_clip_style_line('；'.join(taxonomy_parts), 1100)}")
        must_do = taxonomy.get("must_do") or []
        if isinstance(must_do, list) and must_do:
            lines.append("必须执行：" + "；".join(str(x) for x in must_do[:6]))
        must_not_do = taxonomy.get("must_not_do") or []
        if isinstance(must_not_do, list) and must_not_do:
            lines.append("必须避免：" + "；".join(str(x) for x in must_not_do[:6]))
    if phase in {"creation", "outline"}:
        early = profile.get("early_retention_model")
        if isinstance(early, dict):
            early_parts = []
            for key, label in [
                ("chapter_1", "第1章"),
                ("first_3_chapters", "前3章"),
                ("first_10_chapters", "前10章"),
                ("first_30_chapters", "前30章"),
                ("first_50_chapters", "前50章"),
                ("payoff_cadence", "兑现节奏"),
            ]:
                values = early.get(key)
                if isinstance(values, list) and values:
                    early_parts.append(f"{label}：" + "；".join(str(x) for x in values[:2]))
            if early_parts:
                lines.append(f"前20万字留存模型：{_clip_style_line('；'.join(early_parts), 1100)}")
        length_adaptation = profile.get("length_adaptation")
        if isinstance(length_adaptation, dict):
            length_parts = []
            for key, label in [("short", "短篇"), ("medium", "中篇"), ("long", "长篇"), ("mega", "超长篇")]:
                value = length_adaptation.get(key)
                if value:
                    length_parts.append(f"{label}：{value}")
            fatigue = length_adaptation.get("fatigue_control") or []
            if isinstance(fatigue, list) and fatigue:
                length_parts.append("疲劳控制：" + "；".join(str(x) for x in fatigue[:3]))
            if length_parts:
                lines.append(f"篇幅适配：{_clip_style_line('；'.join(length_parts), 900)}")
    if phase == "writing":
        voice = profile.get("character_voice_matrix")
        if isinstance(voice, dict):
            voice_parts = []
            for key, label in [
                ("protagonist_inner_voice", "主角内心"),
                ("protagonist_spoken_voice", "主角对外"),
                ("close_relationship_voice", "亲近关系"),
                ("authority_voice", "上位者"),
                ("antagonist_voice", "阻力角色"),
                ("voice_separation_rules", "声音区分"),
            ]:
                values = voice.get(key)
                if isinstance(values, list) and values:
                    voice_parts.append(f"{label}：" + "；".join(str(x) for x in values[:2]))
            if voice_parts:
                lines.append(f"角色声音矩阵：{_clip_style_line('；'.join(voice_parts), 1000)}")
        scene_templates = profile.get("scene_templates")
        if isinstance(scene_templates, list) and scene_templates:
            template_lines = []
            for item in scene_templates[:3]:
                if isinstance(item, dict):
                    template_lines.append("；".join(str(x) for x in [
                        item.get("name", "场景模板"),
                        item.get("opening_anchor", ""),
                        item.get("friction", ""),
                        item.get("turn", ""),
                        item.get("exit_hook", ""),
                    ] if x))
                else:
                    template_lines.append(str(item))
            lines.append(f"场景施工模板：{_clip_style_line('；'.join(template_lines), 1000)}")
        repair = profile.get("repair_strategies")
        if isinstance(repair, dict):
            repair_parts = []
            for key, label in [("sentence", "原句"), ("paragraph", "段落"), ("chapter_light", "轻修"), ("continuity", "连续性")]:
                values = repair.get(key)
                if isinstance(values, list) and values:
                    repair_parts.append(f"{label}：" + "；".join(str(x) for x in values[:2]))
            if repair_parts:
                lines.append(f"修复策略：{_clip_style_line('；'.join(repair_parts), 900)}")
    for label, key in [
        ("视角", "pov_style"),
        ("节奏", "pacing_style"),
        ("章节结构", "chapter_structure_style"),
        ("场景", "scene_construction_style"),
        ("场景描写", "scene_description_style"),
        ("人物刻画", "characterization_style"),
        ("角色语言", "character_voice_style"),
        ("对白", "dialogue_style"),
        ("情绪感情", "emotion_style"),
        ("人物关系", "relationship_style"),
        ("世界观揭示", "worldbuilding_style"),
        ("信息控制", "information_control_style"),
        ("冲突", "conflict_style"),
        ("读者反馈", "reader_payoff_style"),
        ("细节", "detail_style"),
        ("语言", "language_style"),
        ("主题", "theme_style"),
        ("文笔工艺", "prose_craft_style"),
        ("段落推进", "paragraph_flow_style"),
        ("细节工艺", "detail_craft_style"),
        ("人物出场", "character_entrance_style"),
        ("情绪落点", "emotion_landing_style"),
        ("场景真实感", "scene_reality_style"),
    ]:
        section = profile.get(key)
        if isinstance(section, dict):
            summary = section.get("summary") or section.get("opening") or ""
            rules = (
                section.get("rules")
                or section.get("techniques")
                or section.get("rhythm_rules")
                or section.get("transition_methods")
                or section.get("detail_sources")
                or section.get("entrance_methods")
                or section.get("physical_reactions")
                or section.get("practical_obstacles")
                or []
            )
            parts = []
            if summary:
                parts.append(str(summary))
            if isinstance(rules, list) and rules:
                parts.append("；".join(str(x) for x in rules[:4]))
            if parts:
                lines.append(f"{label}：{_clip_style_line('；'.join(parts), 520)}")
    recipe = profile.get("chapter_production_recipe")
    if isinstance(recipe, dict):
        recipe_parts = []
        for key, label in [
            ("opening", "开场"),
            ("setup", "铺垫"),
            ("conflict", "冲突"),
            ("explanation", "解释"),
            ("emotion", "情绪"),
            ("ending", "结尾"),
        ]:
            value = recipe.get(key)
            if isinstance(value, list) and value:
                recipe_parts.append(f"{label}：" + "；".join(str(x) for x in value[:2]))
            elif isinstance(value, str) and value:
                recipe_parts.append(f"{label}：{value}")
        if recipe_parts:
            lines.append(f"章节生产法：{_clip_style_line('；'.join(recipe_parts), 900)}")
    patterns = profile.get("reusable_patterns")
    if isinstance(patterns, list) and patterns:
        pattern_lines = []
        for item in patterns[:5]:
            if isinstance(item, dict):
                steps = item.get("steps") or []
                step_text = " -> ".join(str(x) for x in steps[:3]) if isinstance(steps, list) else str(steps)
                pattern_lines.append(f"{item.get('name', '写法模式')}：{item.get('when_to_use', '')}；{step_text}")
            else:
                pattern_lines.append(str(item))
        lines.append(f"可复用写法模式：{_clip_style_line('；'.join(pattern_lines), 900)}")
    avoid = profile.get("avoid_rules") or []
    if isinstance(avoid, list) and avoid:
        lines.append("禁用：" + "；".join(str(x) for x in avoid[:8]))
    if skill.prompt_fragment:
        lines.append(f"可执行风格指令：{_clip_style_line(skill.prompt_fragment, 900)}")
    return "\n".join(lines)

def _format_project_writing_guidance(project: Project | None, skill: WritingStyleSkill | None, phase: str = "writing") -> str:
    if not project:
        return _format_writing_style_skill(skill, phase)
    style = project.writing_style if isinstance(project.writing_style, dict) else {}
    selected = _selected_draft_from_project(project)
    tone_profile = _draft_meta_from_style(style, "tone_profile")
    type_model = _draft_meta_from_style(style, "type_model")
    lines = ["【项目总体风格与题材模型】"]
    tone_lines = _format_tone_profile(tone_profile)
    type_lines = _format_type_model(type_model)
    if tone_lines:
        lines.extend(tone_lines)
    else:
        tags = _as_string_list(selected.get("tags"), 8)
        if tags:
            lines.append("风格标签：" + "、".join(tags))
        else:
            lines.append("总体风格：未单独固定，按项目类型和已有草案保持一致。")
    if type_lines:
        lines.extend(type_lines)
    if selected.get("reader_promise"):
        lines.append(f"读者承诺：{_clip_style_line(selected.get('reader_promise'), 420)}")
    if selected.get("core_engine"):
        lines.append(f"核心引擎：{_clip_style_line(selected.get('core_engine'), 520)}")
    if selected.get("first_volume_engine") and phase in {"creation", "outline"}:
        lines.append(f"第一卷发动机：{_clip_style_line(selected.get('first_volume_engine'), 900)}")
    if selected.get("early_event_chain") and phase in {"creation", "outline"}:
        lines.append(f"早期事件链：{_clip_style_line(selected.get('early_event_chain'), 1100)}")
    lines.append("执行优先级：项目总体风格和题材模型优先于共享 Skill；Skill 只能提供写法方法，不能改变本项目的类型承诺、风格气质和核心引擎。")
    lines.append("【共享写作风格 Skill】")
    lines.append(_format_writing_style_skill(skill, phase))
    return "\n".join(lines)

async def _active_writing_style_skill(db: AsyncSession, project: Project | None) -> WritingStyleSkill | None:
    if not project:
        return None
    style = project.writing_style or {}
    if not isinstance(style, dict):
        return None
    skill_id = style.get("active_style_skill_id")
    if not skill_id:
        return None
    return (await db.execute(
        select(WritingStyleSkill).where(WritingStyleSkill.id == skill_id, WritingStyleSkill.user_id == project.user_id, WritingStyleSkill.is_active == True)
    )).scalar_one_or_none()

def _early_grip_guidance(project: Project | None, chapter: Chapter | None, volume: Volume | None, controls: dict | None) -> str:
    controls = controls or {}
    if str(controls.get("early_grip_mode", "auto")) == "off":
        return "已关闭前20万字强追读模式，按常规章节质量要求写作。"
    target_words = int(controls.get("target_words") or getattr(chapter, "target_words", None) or getattr(volume, "default_chapter_words", None) or 3500)
    chapter_number = int(getattr(chapter, "chapter_number", 1) or 1)
    estimated_position = chapter_number * max(target_words, 1000)
    target_total = int(getattr(project, "target_total_words", 0) or 0)
    is_long_form = target_total >= 300000 or str(getattr(project, "target_length", "")).lower() in {"long", "very_long", "超长篇", "长篇"}
    if estimated_position > 200000 and str(controls.get("early_grip_mode", "auto")) != "force":
        return "当前章节估算已超过前20万字，保持追读钩子，但允许更多长期铺垫和情绪沉淀。"

    form_note = "这是长篇连载的前20万字，必须优先让读者愿意追下去。" if is_long_form else "这是故事早期章节，必须快速建立可读性和期待感。"
    return f"""
{form_note}
硬要求：
- 第一屏必须有可见事件、异常结果、具体麻烦或强人物动作，不能以设定说明、背景总结、空泛心理开场。
- 本章要有清晰短目标：主角这一章想解决什么、避开什么、证明什么或占到什么便宜。
- 必须给读者即时反馈：笑点/爽点/社死/反转/小胜/翻车/新能力试用至少出现一种，且要写出旁观者或现实后果。
- 每个设定信息都必须绑定现场用途：它让主角赚了、亏了、尴尬了、暴露了、被误会了，不能单独讲课。
- 主角要主动做选择，哪怕选择很怂、很损、很社死，也不能只被剧情推着走。
- 章末钩子要具体到声音、物件、弹窗、消息、动作、人物一句话或现场发现，让读者自然想翻下一章。
- 不要为了“高级感”把情节写得绕。前20万字优先易懂、好玩、有反馈、有连续期待。
- 章节不能只靠“看见制度问题/产生不安/理想摇晃”推进，必须落到具体麻烦：材料被退、会议被怼、项目出事、钱流异常、群众堵门、同事甩锅、上级试探。
- 每章结尾要让读者问“他接下来怎么破局”，而不是只留下“他心里很复杂”。
""".strip()
