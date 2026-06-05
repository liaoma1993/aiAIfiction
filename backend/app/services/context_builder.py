from __future__ import annotations

from app.services.story_bible import build_story_bible


def _truncate(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "..."


def _format_list(items: list[str], limit: int = 8) -> str:
    return "、".join(items[:limit])


def _compress_characters(characters: list[dict]) -> str:
    parts = []
    for c in characters[:8]:
      parts.append(
          f"{c.get('name')}({c.get('role_type')}):"
          f"性格={_truncate(c.get('personality', ''), 80)};"
          f"动机={_truncate(c.get('motivation', ''), 60)};"
          f"状态={_truncate(str(c.get('current_state', {})), 80)}"
      )
    return "\n".join(parts)


async def build_generation_context(db, project_id: str, chapter_id: str | None = None, max_recent_chapters: int = 3) -> dict:
    bible = await build_story_bible(db, project_id, chapter_id)
    current = bible.get("current_chapter") or {}
    recent = bible.get("recent_chapters") or []

    context = {
        "project_summary": {
            "title": bible["project"]["title"],
            "genre": bible["project"]["genre"],
            "story_brief": _truncate(bible["project"]["story_brief"], 700),
            "core_theme": bible["project"].get("core_theme", ""),
            "motifs": bible["project"].get("motifs", []),
            "planning_memory": bible["project"].get("planning_memory", {}),
        },
        "hard_constraints": bible["world"].get("hard_rules", []),
        "tone_rules": bible["world"].get("tone_rules", []),
        "world_logic": bible["world"].get("world_logic", {}),
        "characters": _compress_characters(bible.get("characters", [])),
        "factions": "\n".join([
            f"{f.get('name')}({f.get('faction_type')}):{_truncate(f.get('core_creed', ''), 100)}"
            for f in bible.get("factions", [])[:6]
        ]),
        "timeline": "\n".join([
            f"{e.get('time_point', '')}:{_truncate(e.get('description', ''), 100)}"
            for e in bible.get("timeline", [])[:10]
        ]),
        "foreshadowing": "\n".join([
            f"{f.get('name')}[{f.get('status')}]:{_truncate(f.get('description', ''), 100)}"
            for f in bible.get("foreshadowing", [])[:10]
        ]),
        "current_volume": bible.get("current_volume", {}),
        "current_chapter": current,
        "recent_chapters": recent[:max_recent_chapters],
    }

    if current:
        context["chapter_blueprint"] = current.get("blueprint") or {}
        context["chapter_mandates"] = {
            "connects_from": current.get("connects_from", ""),
            "connects_to": current.get("connects_to", ""),
            "hook": current.get("hook", ""),
            "characters_in_chapter": current.get("characters_in_chapter", []),
            "key_events": current.get("key_events", []),
        }
    return context
