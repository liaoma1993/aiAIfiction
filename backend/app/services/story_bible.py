from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.world_setting import WorldSetting
from app.models.character import Character
from app.models.faction import Faction, FactionRelation
from app.models.timeline import TimelineEvent, StoryStateTrail
from app.models.outline import ForeshadowingPlan
from app.models.volume import Volume
from app.models.chapter import Chapter


def _clip(text: str | None, limit: int = 500) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "..."


def _planning_memory(project: Project) -> dict:
    style = project.writing_style or {}
    if not isinstance(style, dict):
        return {}
    memory = style.get("wizard_planning_memory") or {}
    if not isinstance(memory, dict):
        return {}
    selected = memory.get("selected_draft") or {}
    if not isinstance(selected, dict):
        selected = {}
    return {
        "selected_draft": selected,
        "core_engine": selected.get("core_engine", ""),
        "reader_promise": selected.get("reader_promise", ""),
        "length_type": selected.get("length_type", ""),
        "boundary_locks": selected.get("boundary_locks") or [],
        "long_term_plan": selected.get("long_term_plan") or {},
        "narrative_engine": style.get("narrative_engine") or {},
    }


async def build_story_bible(db: AsyncSession, project_id: str, chapter_id: str | None = None) -> dict:
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise RuntimeError("项目不存在")

    world = (await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))).scalar_one_or_none()
    characters = (await db.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
    factions = (await db.execute(select(Faction).where(Faction.project_id == project_id))).scalars().all()
    relations = (await db.execute(select(FactionRelation).where(FactionRelation.project_id == project_id))).scalars().all()
    events = (await db.execute(select(TimelineEvent).where(TimelineEvent.project_id == project_id).order_by(TimelineEvent.created_at.desc()).limit(30))).scalars().all()
    foreshadowing = (await db.execute(select(ForeshadowingPlan).where(ForeshadowingPlan.project_id == project_id))).scalars().all()
    volumes = (await db.execute(select(Volume).where(Volume.project_id == project_id).order_by(Volume.sort_order))).scalars().all()
    current_chapter = None
    prev_chapters = []
    current_volume = None
    if chapter_id:
        current_chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if current_chapter:
            current_volume = (await db.execute(select(Volume).where(Volume.id == current_chapter.volume_id))).scalar_one_or_none()
            prev_chapters = (await db.execute(
                select(Chapter).where(
                    Chapter.project_id == project_id,
                    Chapter.volume_id == current_chapter.volume_id,
                    Chapter.chapter_number < current_chapter.chapter_number,
                ).order_by(Chapter.chapter_number.desc()).limit(3)
            )).scalars().all()

    return {
        "project": {
            "id": str(project.id),
            "title": project.title,
            "genre": project.genre,
            "story_brief": _clip(project.story_brief, 1200),
            "core_theme": project.core_theme,
            "secondary_themes": project.secondary_themes or [],
            "motifs": project.motifs or [],
            "narrative_lines": project.narrative_lines or [],
            "target_total_words": project.target_total_words,
            "planning_memory": _planning_memory(project),
        },
        "world": {
            "geography": world.geography if world else {},
            "social_structure": world.social_structure if world else {},
            "power_system": world.power_system if world else {},
            "history": world.history if world else {},
            "culture": world.culture if world else {},
            "special_rules": world.special_rules if world else {},
            "world_logic": world.world_logic if world else {},
            "hard_rules": world.hard_rules if world else [],
            "tone_rules": world.tone_rules if world else [],
            "constraints": world.constraints if world else [],
        },
        "characters": [
            {
                "id": str(c.id),
                "name": c.name,
                "role_type": c.role_type,
                "personality": _clip(c.personality, 300),
                "background": _clip(c.background, 400),
                "motivation": _clip(c.motivation, 250),
                "inner_conflict": _clip(c.inner_conflict, 250),
                "language_fingerprint": _clip(c.language_fingerprint, 200),
                "behavior_pattern": _clip(c.behavior_pattern, 200),
                "emotional_expression": _clip(c.emotional_expression, 150),
                "appearance": _clip(c.appearance, 150),
                "faction_rank": c.faction_rank,
                "growth_arc": _clip(c.growth_arc, 300),
                "growth_arc_preset": _clip(c.growth_arc_preset, 300),
                "relationships": c.relationships or [],
                "relationship_dynamics": c.relationship_dynamics or [],
                "current_state": c.current_state or {},
            } for c in characters
        ],
        "factions": [
            {
                "id": str(f.id),
                "name": f.name,
                "faction_type": f.faction_type,
                "description": _clip(f.description, 400),
                "core_creed": _clip(f.core_creed, 250),
                "headquarters": _clip(f.headquarters, 150),
                "hierarchy": f.hierarchy or [],
                "core_conflict_of_interest": _clip(f.core_conflict_of_interest, 250),
                "internal_faction_cracks": _clip(f.internal_faction_cracks, 250),
                "strength_trajectory": _clip(f.strength_trajectory, 100),
                "sort_order": f.sort_order or 0,
            } for f in factions
        ],
        "faction_relations": [
            {
                "faction_a_id": str(r.faction_a_id) if r.faction_a_id else None,
                "faction_b_id": str(r.faction_b_id) if r.faction_b_id else None,
                "relation_type": r.relation_type,
                "timeline_changes": r.timeline_changes or [],
            } for r in relations
        ],
        "timeline": [
            {
                "id": str(e.id),
                "description": _clip(e.description, 300),
                "time_point": e.time_point,
                "event_type": e.event_type,
                "is_major": e.is_major_event,
                "related_character_ids": e.related_character_ids or [],
                "related_faction_ids": e.related_faction_ids or [],
            } for e in events
        ],
        "foreshadowing": [
            {
                "id": str(f.id),
                "name": f.name,
                "description": _clip(f.description, 300),
                "plant_stage": f.plant_stage,
                "reveal_stage": f.reveal_stage,
                "status": f.status,
            } for f in foreshadowing
        ],
        "volumes": [
            {
                "id": str(v.id),
                "volume_number": v.volume_number,
                "title": v.title,
                "summary": _clip(v.summary, 500),
                "theme": v.theme,
                "outline": _clip(v.outline, 1000),
                "chapter_count": v.chapter_count,
                "target_words": v.target_words,
                "default_chapter_words": v.default_chapter_words,
                "emotional_arc_description": v.emotional_arc_description,
            } for v in volumes
        ],
        "current_volume": {
            "id": str(current_volume.id) if current_volume else None,
            "title": current_volume.title if current_volume else "",
            "outline": _clip(current_volume.outline, 1000) if current_volume else "",
            "theme": current_volume.theme if current_volume else "",
            "chapter_count": current_volume.chapter_count if current_volume else 0,
        } if current_volume else {},
        "current_chapter": {
            "id": str(current_chapter.id) if current_chapter else None,
            "chapter_number": current_chapter.chapter_number if current_chapter else 0,
            "title": current_chapter.title if current_chapter else "",
            "summary": _clip(current_chapter.summary, 500) if current_chapter else "",
            "blueprint": current_chapter.blueprint if current_chapter else {},
            "connects_from": current_chapter.connects_from if current_chapter else "",
            "connects_to": current_chapter.connects_to if current_chapter else "",
            "hook": current_chapter.hook if current_chapter else "",
            "characters_in_chapter": current_chapter.characters_in_chapter if current_chapter else [],
            "key_events": current_chapter.key_events if current_chapter else [],
        } if current_chapter else {},
        "recent_chapters": [
            {
                "chapter_number": c.chapter_number,
                "title": c.title,
                "summary": _clip(c.summary, 400),
                "hook": c.hook,
                "story_state_snapshot": _clip(c.story_state_snapshot, 600),
            } for c in prev_chapters
        ],
    }
