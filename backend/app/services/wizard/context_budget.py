import json
import re

from app.models.chapter import Chapter
from app.models.character import Character
from app.models.faction import Faction

def _clip_context(text: str | None, limit: int) -> str:
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n...（已按上下文预算截断，原长 {len(text)} 字）"

def _compact_json(value, limit: int = 1200) -> str:
    try:
        text = json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        text = str(value or "")
    return _clip_context(text, limit)

def _writing_context_limits(controls: dict | None) -> dict:
    mode = str((controls or {}).get("context_budget") or "standard").lower()
    presets = {
        "compact": {"characters": 4500, "factions": 2200, "volume": 1800, "state": 1200},
        "standard": {"characters": 7000, "factions": 3200, "volume": 2600, "state": 1600},
        "rich": {"characters": 11000, "factions": 5200, "volume": 4200, "state": 2400},
    }
    return presets.get(mode, presets["standard"])

def _select_relevant_names(chapter: Chapter) -> set[str]:
    names = set()
    for item in chapter.characters_in_chapter or []:
        if item:
            names.add(str(item))
    payloads = [
        chapter.summary or "",
        chapter.arc_name or "",
        _compact_json(chapter.blueprint or {}, 3000),
    ]
    text = "\n".join(payloads)
    for name in re.findall(r"[\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9·]{1,12}", text):
        if len(name) >= 2:
            names.add(name)
    return names

def _build_budgeted_character_summary(characters: list[Character], chapter: Chapter, controls: dict | None) -> str:
    limits = _writing_context_limits(controls)
    relevant = _select_relevant_names(chapter)
    ranked = sorted(
        characters,
        key=lambda c: (
            0 if c.name in relevant or c.role_type in {"主角", "男主", "女主"} else 1,
            c.first_appeared_chapter or 999999,
            c.name or "",
        ),
    )
    lines = []
    for c in ranked[:18]:
        profile = _build_character_profile(c)
        if c.name not in relevant and len("\n".join(lines)) > limits["characters"] * 0.7:
            profile = f"{c.name}({c.role_type or '角色'}): 状态={_clip_context(str(c.current_state or ''), 160)}; 语言={_clip_context(c.language_fingerprint or '', 120)}"
        lines.append(profile)
        if len("\n".join(lines)) >= limits["characters"]:
            break
    return _clip_context("\n".join(lines), limits["characters"])

def _build_budgeted_faction_summary(factions: list[Faction], chapter: Chapter, controls: dict | None) -> str:
    limits = _writing_context_limits(controls)
    chapter_text = f"{chapter.summary or ''}\n{chapter.arc_name or ''}\n{_compact_json(chapter.blueprint or {}, 2500)}"
    ranked = sorted(
        factions,
        key=lambda f: (
            0 if f.name and f.name in chapter_text else 1,
            getattr(f, "sort_order", None) or 999999,
            f.name or "",
        ),
    )
    lines = []
    for f in ranked[:10]:
        lines.append(_build_faction_profile(f))
        if len("\n".join(lines)) >= limits["factions"]:
            break
    return _clip_context("\n".join(lines), limits["factions"])

def _build_character_profile(c: Character) -> str:
    parts = [f"{c.name}({c.role_type})"]
    if c.personality:
        parts.append(f"性格：{c.personality}")
    if c.inner_conflict:
        parts.append(f"内在矛盾：{c.inner_conflict}")
    if c.motivation:
        parts.append(f"动机：{c.motivation}")
    if c.language_fingerprint:
        parts.append(f"说话风格：{c.language_fingerprint}")
    if c.behavior_pattern:
        parts.append(f"行为模式：{c.behavior_pattern}")
    if c.emotional_expression:
        parts.append(f"情感表达：{c.emotional_expression}")
    if c.background:
        parts.append(f"背景：{c.background[:150]}")
    if c.growth_arc_preset:
        parts.append(f"弧光：{c.growth_arc_preset}")
    if c.faction_rank:
        parts.append(f"势力职位：{c.faction_rank}")
    if c.relationship_dynamics:
        rel_items = c.relationship_dynamics if isinstance(c.relationship_dynamics, list) else [c.relationship_dynamics]
        parts.append(f"关系动态：{'；'.join(_safe_str(r) for r in rel_items)}")
    return " | ".join(parts)

def _build_faction_profile(f: Faction) -> str:
    parts = [f"{f.name}({f.faction_type})"]
    if f.description:
        parts.append(f"简介：{f.description[:200]}")
    if f.core_creed:
        parts.append(f"核心理念：{f.core_creed}")
    if f.core_conflict_of_interest:
        parts.append(f"核心利益：{f.core_conflict_of_interest}")
    if f.strength_trajectory:
        parts.append(f"实力趋势：{f.strength_trajectory}")
    return " | ".join(parts)

def _safe_str(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("name", item.get("description", str(item)))
    return str(item)
