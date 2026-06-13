from app.models.project import Project

def _clip_planning_text(text: str | None, limit: int = 1000) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "..."

def _as_string_list(value, limit: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _planning_value_text(item).strip()
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items

def _planning_value_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "；".join(_planning_value_text(x) for x in value if _planning_value_text(x))
    if isinstance(value, dict):
        labels = {
            "stage": "阶段",
            "title": "标题",
            "goal": "目标",
            "pressure_upgrade": "压力升级",
            "protagonist_change": "主角变化",
            "hook": "钩子",
            "event": "事件",
            "protagonist_action": "主角行动",
            "obstacle": "阻力",
            "payoff": "反馈",
            "carry_forward": "后续承接",
            "name": "名称",
            "description": "说明",
            "plant_stage": "埋设",
            "reveal_stage": "回收",
            "payoff_type": "兑现方式",
        }
        parts = []
        for key, item in value.items():
            text = _planning_value_text(item)
            if text:
                parts.append(f"{labels.get(key, key)}：{text}")
        return "；".join(parts)
    return str(value).strip()

def _format_stage_plan_item(item, idx: int) -> str:
    if not isinstance(item, dict):
        return _planning_value_text(item)
    title = item.get("stage") or item.get("title") or f"阶段{idx + 1}"
    fields = [
        ("goal", "目标"),
        ("pressure_upgrade", "压力升级"),
        ("protagonist_change", "主角变化"),
        ("hook", "阶段钩子"),
    ]
    details = [f"{label}：{_planning_value_text(item.get(key))}" for key, label in fields if item.get(key)]
    return f"{idx + 1}. {title}" + ("；" + "；".join(details) if details else "")

def _build_wizard_planning_memory(messages: list[dict], selected_draft: dict, suggestions: list[dict]) -> dict:
    clean_messages = []
    for item in (messages or [])[-30:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = _clip_planning_text(item.get("content", ""), 1000)
        if role in {"user", "assistant"} and content:
            clean_messages.append({"role": role, "content": content})
    return {
        "messages": clean_messages,
        "selected_draft": selected_draft or {},
        "suggestions": (suggestions or [])[:6],
    }

def _draft_meta_from_style(style: dict, key: str) -> dict:
    direct = style.get(key) if isinstance(style, dict) else None
    if isinstance(direct, dict) and direct:
        return direct
    memory = style.get("wizard_planning_memory") if isinstance(style, dict) else {}
    selected = memory.get("selected_draft") if isinstance(memory, dict) else {}
    value = selected.get(key) if isinstance(selected, dict) else None
    return value if isinstance(value, dict) else {}

def _selected_draft_from_project(project: Project) -> dict:
    style = project.writing_style or {}
    if not isinstance(style, dict):
        return {}
    memory = style.get("wizard_planning_memory") or {}
    selected = memory.get("selected_draft") if isinstance(memory, dict) else {}
    return selected if isinstance(selected, dict) else {}

def _format_tone_profile(tone_profile: dict, prefix: str = "") -> list[str]:
    if not isinstance(tone_profile, dict) or not tone_profile:
        return []
    lines = []
    tone_label = tone_profile.get("tone_label")
    if tone_label:
        lines.append(f"{prefix}总体风格：{tone_label}")
    field_labels = [
        ("narrative_texture", "叙事质感"),
        ("pacing", "节奏"),
        ("humor_level", "幽默程度"),
        ("emotional_temperature", "情绪温度"),
        ("language_style", "语言手感"),
    ]
    parts = [f"{label}：{tone_profile.get(key)}" for key, label in field_labels if tone_profile.get(key)]
    if parts:
        lines.append(f"{prefix}风格执行：" + "；".join(parts))
    taboos = _as_string_list(tone_profile.get("taboos"), 8)
    if taboos:
        lines.append(f"{prefix}风格禁忌：" + "；".join(taboos))
    return lines

def _format_type_model(type_model: dict, prefix: str = "") -> list[str]:
    if not isinstance(type_model, dict) or not type_model:
        return []
    field_labels = [
        ("primary_genre", "主类型模型"),
        ("reader_expectation", "读者期待"),
        ("core_reader_reward", "核心读者奖励"),
        ("main_conflict_form", "主要冲突形态"),
        ("upgrade_feedback_loop", "升级/反馈循环"),
        ("early_obstacle_pattern", "早期阻力模式"),
    ]
    return [
        f"{prefix}{label}：{_clip_planning_text(str(type_model.get(key)), 260)}"
        for key, label in field_labels
        if type_model.get(key)
    ]

def _format_wizard_planning_memory(project: Project, limit: int = 14000) -> str:
    style = project.writing_style or {}
    memory = style.get("wizard_planning_memory") if isinstance(style, dict) else {}
    if not isinstance(memory, dict) or not memory:
        return ""
    parts = []
    selected = memory.get("selected_draft") or {}
    if isinstance(selected, dict) and selected:
        parts.append("【向导阶段最终草案】")
        if selected.get("title"):
            parts.append(f"书名：{selected.get('title')}")
        if selected.get("genre"):
            parts.append(f"类型：{selected.get('genre')}")
        if selected.get("length_type"):
            parts.append(f"篇幅类型：{selected.get('length_type')}")
        parts.extend(_format_tone_profile(selected.get("tone_profile") or {}, ""))
        parts.extend(_format_type_model(selected.get("type_model") or {}, ""))
        if selected.get("reader_promise"):
            parts.append(f"读者承诺：{selected.get('reader_promise')}")
        if selected.get("core_engine"):
            parts.append(f"核心引擎：{selected.get('core_engine')}")
        first_volume_engine = selected.get("first_volume_engine") or {}
        if isinstance(first_volume_engine, dict) and first_volume_engine:
            engine_parts = []
            for key, label in [
                ("volume_promise", "第一卷承诺"),
                ("protagonist_first_move", "主角第一动作"),
                ("early_visible_opponent", "早期可见阻力"),
                ("first_reward", "第一反馈"),
                ("first_cost", "第一代价"),
                ("volume_hook", "卷末钩子"),
            ]:
                if first_volume_engine.get(key):
                    engine_parts.append(f"{label}：{first_volume_engine.get(key)}")
            if engine_parts:
                parts.append("第一卷发动机：" + "；".join(_clip_planning_text(str(x), 180) for x in engine_parts))
        early_event_chain = selected.get("early_event_chain") or []
        if isinstance(early_event_chain, list) and early_event_chain:
            event_parts = []
            for item in early_event_chain:
                if isinstance(item, dict):
                    event_parts.append(
                        " / ".join(str(x) for x in [
                            item.get("event", ""),
                            item.get("protagonist_action", ""),
                            item.get("obstacle", ""),
                            item.get("payoff", ""),
                            item.get("carry_forward", ""),
                        ] if x)
                    )
                elif item:
                    event_parts.append(str(item))
            if event_parts:
                parts.append("第一批具体事件链：" + "；".join(_clip_planning_text(x, 220) for x in event_parts))
        readability_gate = selected.get("readability_gate") or {}
        if isinstance(readability_gate, dict) and readability_gate:
            gate_parts = []
            if readability_gate.get("passed") is not None:
                gate_parts.append(f"是否通过：{readability_gate.get('passed')}")
            if readability_gate.get("risks"):
                gate_parts.append("风险：" + _planning_value_text(readability_gate.get("risks")))
            if readability_gate.get("fix_strategy"):
                gate_parts.append("修复策略：" + _planning_value_text(readability_gate.get("fix_strategy")))
            if gate_parts:
                parts.append("可读性闸门：" + "；".join(gate_parts))
        boundary_locks = selected.get("boundary_locks") or []
        if boundary_locks:
            parts.append("边界锁定：" + "；".join(_planning_value_text(x) for x in boundary_locks))
        if selected.get("brief"):
            parts.append(f"草案：{_clip_planning_text(selected.get('brief'), 900)}")
        long_term_plan = selected.get("long_term_plan") or {}
        if isinstance(long_term_plan, dict) and long_term_plan:
            if long_term_plan.get("endgame"):
                parts.append(f"终局指向：{_clip_planning_text(long_term_plan.get('endgame'), 400)}")
            stage_plan = long_term_plan.get("stage_plan") or []
            if stage_plan:
                parts.append("长线阶段：\n" + "\n".join(_format_stage_plan_item(x, idx) for idx, x in enumerate(stage_plan)))
            payoffs = long_term_plan.get("foreshadowing_payoffs") or []
            if payoffs:
                parts.append("伏笔回收：" + "；".join(_planning_value_text(x) for x in payoffs))
        tags = selected.get("tags") or []
        if tags:
            parts.append("风格标签：" + "、".join(str(x) for x in tags))
        open_questions = selected.get("open_questions") or []
        if open_questions:
            parts.append("未确认问题：" + "；".join(_planning_value_text(x) for x in open_questions))
    user_messages = [
        _clip_planning_text(item.get("content", ""), 220)
        for item in (memory.get("messages") or [])
        if isinstance(item, dict) and item.get("role") == "user" and item.get("content")
    ]
    if user_messages:
        parts.append("【作者策划沟通要点，仅用于向导生成】")
        parts.extend([f"- {text}" for text in user_messages[-10:]])
    return _clip_planning_text("\n".join(parts), limit)

def _world_rule_defaults_from_project(project: Project) -> dict:
    style = project.writing_style or {}
    selected = _selected_draft_from_project(project)
    tone_profile = _draft_meta_from_style(style if isinstance(style, dict) else {}, "tone_profile")
    type_model = _draft_meta_from_style(style if isinstance(style, dict) else {}, "type_model")
    boundary_locks = _as_string_list(selected.get("boundary_locks"), 50)
    tags = _as_string_list(selected.get("tags"), 50)
    hard_rules = []
    if selected.get("core_engine"):
        hard_rules.append(f"核心引擎不能偏离：{selected.get('core_engine')}")
    hard_rules.extend(boundary_locks)
    tone_rules = []
    tone_rules.extend(_format_tone_profile(tone_profile))
    if tags:
        tone_rules.append("文风标签必须保持：" + "、".join(tags))
    if selected.get("reader_promise"):
        tone_rules.append(f"读者承诺必须体现在章节体验里：{selected.get('reader_promise')}")
    type_lines = _format_type_model(type_model)
    if type_lines:
        tone_rules.append("题材模型必须服从：" + "；".join(type_lines[:4]))
    constraints = []
    if selected.get("length_type"):
        constraints.append(f"篇幅规划按{selected.get('length_type')}处理，不能用短篇节奏写长线，也不能把短篇强行注水成长篇。")
    long_term_plan = selected.get("long_term_plan") or {}
    if isinstance(long_term_plan, dict) and long_term_plan.get("endgame"):
        constraints.append(f"后续发展不能偏离终局指向：{long_term_plan.get('endgame')}")
    return {
        "hard_rules": hard_rules[:50],
        "tone_rules": tone_rules[:30],
        "constraints": constraints[:30],
    }

def _wizard_story_brief(project: Project, limit: int = 20000) -> str:
    planning = _format_wizard_planning_memory(project, 14000)
    brief = project.story_brief or ""
    return _clip_planning_text(f"{brief}\n\n{planning}" if planning else brief, limit)
