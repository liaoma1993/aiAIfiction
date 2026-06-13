import json

from app.models.chapter import Chapter

def _safe_str(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("name") or item.get("event") or item.get("summary") or str(item)
    return str(item)

def _parse_state_snapshot(snapshot: str) -> dict:
    if not snapshot:
        return {}
    if isinstance(snapshot, dict):
        return snapshot
    try:
        return json.loads(snapshot)
    except (TypeError, json.JSONDecodeError):
        return {"summary": str(snapshot)}

def _serialize_summary(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = []
        for key in ["开场状态", "场景序列", "情绪曲线", "章末状态", "衔接钩子"]:
            if key in value:
                v = value[key]
                if isinstance(v, list):
                    v = "；".join(str(x) if isinstance(x, str) else x.get("核心冲突或对话方向", str(x)) for x in v)
                parts.append(f"{key}：{v}")
        return "\n".join(parts) if parts else str(value)
    return str(value)

def _serialize_snapshot(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("opening_state", "") + "\n" + str(value.get("summary", ""))
    return str(value)

def _build_story_state_snapshot(chapter: Chapter, prev_snapshot: str = "") -> str:
    parts = []
    if chapter.characters_in_chapter:
        parts.append(f"在场角色：{', '.join(_safe_str(c) for c in chapter.characters_in_chapter)}")
    if chapter.key_events:
        parts.append(f"核心事件：{'; '.join(_safe_str(e) for e in chapter.key_events)}")
    if chapter.connects_to:
        parts.append(f"章末状态：{chapter.connects_to}")
    if chapter.hook:
        parts.append(f"钩子：{chapter.hook}")
    checks = chapter.continuity_checks or {}
    if checks.get("state_delta"):
        parts.append(f"状态变化：{json.dumps(checks.get('state_delta'), ensure_ascii=False)[:700]}")
    if checks.get("continuity_to_next"):
        parts.append(f"下章必须继承：{json.dumps(checks.get('continuity_to_next'), ensure_ascii=False)[:500]}")
    state = _parse_state_snapshot(chapter.story_state_snapshot or "")
    for label, key in [
        ("关系变化", "relationship_changes"),
        ("物件状态", "object_states"),
        ("外部压力", "external_pressures"),
        ("下章开头要求", "opening_requirements_for_next"),
        ("下一章必须承接", "next_must_follow"),
        ("延后钩子", "deferred_hooks"),
    ]:
        value = state.get(key)
        if value:
            parts.append(f"{label}：{json.dumps(value, ensure_ascii=False)[:500]}")
    if prev_snapshot:
        parts.append(f"上章快照：{prev_snapshot[:500]}")
    return "\n".join(parts) if parts else "无"

def _format_chapter_continuity_payload(chapter: Chapter) -> str:
    payload = {
        "connects_from": chapter.connects_from or "",
        "connects_to": chapter.connects_to or "",
        "hook": chapter.hook or "",
        "blueprint_continuity": {
            "arc_step_refs": chapter.arc_step_refs or (chapter.blueprint or {}).get("arc_step_refs") or (chapter.continuity_checks or {}).get("arc_step_refs", []),
            "continuity_from_previous": chapter.continuity_from_previous or (chapter.blueprint or {}).get("continuity_from_previous") or (chapter.continuity_checks or {}).get("continuity_from_previous", []),
            "state_delta": chapter.state_delta or (chapter.blueprint or {}).get("state_delta") or (chapter.continuity_checks or {}).get("state_delta", {}),
            "continuity_to_next": chapter.continuity_to_next or (chapter.blueprint or {}).get("continuity_to_next") or (chapter.continuity_checks or {}).get("continuity_to_next", []),
            "entry_gate_checks": (chapter.blueprint or {}).get("entry_gate_checks") or (chapter.continuity_checks or {}).get("entry_gate_checks", {}),
            "chapter_function": (chapter.blueprint or {}).get("chapter_function") or (chapter.continuity_checks or {}).get("chapter_function", ""),
            "opening_requirements": (chapter.blueprint or {}).get("opening_requirements") or (chapter.continuity_checks or {}).get("opening_requirements", []),
            "indispensability_check": (chapter.blueprint or {}).get("indispensability_check") or (chapter.continuity_checks or {}).get("indispensability_check", {}),
            "hook_design": (chapter.blueprint or {}).get("hook_design") or (chapter.continuity_checks or {}).get("hook_design", {}),
            "character_voice_constraints": (chapter.blueprint or {}).get("character_voice_constraints") or (chapter.continuity_checks or {}).get("character_voice_constraints", {}),
            "information_reveal_plan": (chapter.blueprint or {}).get("information_reveal_plan") or (chapter.continuity_checks or {}).get("information_reveal_plan", {}),
            "repair_priority_hint": (chapter.blueprint or {}).get("repair_priority_hint") or (chapter.continuity_checks or {}).get("repair_priority_hint", ""),
        },
        "state_memory": {
            "relationship_changes": chapter.relationship_changes or [],
            "object_states": chapter.object_states or [],
            "external_pressures": chapter.external_pressures or [],
            "opening_requirements_for_next": chapter.opening_requirements_for_next or [],
        },
        "causality_links": chapter.causality_links or [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

def _validate_state_extract_payload(result: dict) -> dict:
    result = result if isinstance(result, dict) else {}
    missing = []
    quality = {}
    checks = {
        "body": result.get("character_changes"),
        "relationship": result.get("relationship_changes"),
        "information": result.get("facts"),
        "object": result.get("object_states"),
        "external_pressure": result.get("external_pressures"),
        "next_opening_requirements": result.get("opening_requirements_for_next") or result.get("next_must_follow"),
        "indispensability": (result.get("indispensability_check") or {}).get("if_deleted_what_breaks"),
        "hook": result.get("hook_assessment"),
    }
    for key, value in checks.items():
        ok = bool(value)
        quality[key] = "有" if ok else "缺失"
        if not ok:
            missing.append(key)
    return {
        "passed": not missing,
        "state_quality": quality,
        "missing_state": missing,
        "repair_instruction": "请只补充缺失的长期状态，不要重写正文。" if missing else "",
    }

def _safe_json(value, fallback):
    if value is None:
        return fallback
    return value

def _clip_text(text, limit: int = 600) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= limit else text[:limit] + "..."

def _list_preview(items, limit: int = 5) -> str:
    if not items:
        return ""
    if not isinstance(items, list):
        return _clip_text(str(items), 400)
    return "；".join(_clip_text(_safe_str(x), 120) for x in items[:limit])
