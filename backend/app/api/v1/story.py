from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.outline import ForeshadowingPlan
from app.models.timeline import TimelineEvent, StoryStateTrail
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/story", tags=["story"])


def _safe_list(value):
    return value if isinstance(value, list) else []


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _short_text(value: str | None, limit: int = 160) -> str:
    text = (value or "").strip()
    return text if len(text) <= limit else f"{text[:limit]}..."


def _quality_review(checks):
    checks = _safe_dict(checks)
    return _safe_dict(checks.get("quality_review"))


class CompleteQualityIssueRequest(BaseModel):
    chapter_id: str
    issue_index: int | None = None
    issue: str = ""


async def _load_story_base(project_id: str, db: AsyncSession):
    from app.models.project import Project
    from app.models.world_setting import WorldSetting
    from app.models.character import Character
    from app.models.faction import Faction, FactionRelation
    from app.models.volume import Volume
    from app.models.chapter import Chapter
    from app.models.relationship_event import RelationshipEvent

    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    world = (await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))).scalar_one_or_none()
    characters = (await db.execute(select(Character).where(Character.project_id == project_id).order_by(Character.created_at))).scalars().all()
    factions = (await db.execute(select(Faction).where(Faction.project_id == project_id).order_by(Faction.sort_order, Faction.created_at))).scalars().all()
    faction_relations = (await db.execute(select(FactionRelation).where(FactionRelation.project_id == project_id))).scalars().all()
    volumes = (await db.execute(select(Volume).where(Volume.project_id == project_id).order_by(Volume.sort_order, Volume.volume_number))).scalars().all()
    chapters = (await db.execute(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_number))).scalars().all()
    foreshadowing = (await db.execute(select(ForeshadowingPlan).where(ForeshadowingPlan.project_id == project_id).order_by(ForeshadowingPlan.created_at))).scalars().all()
    events = (await db.execute(select(TimelineEvent).where(TimelineEvent.project_id == project_id).order_by(TimelineEvent.absolute_day, TimelineEvent.created_at))).scalars().all()
    relation_events = (await db.execute(select(RelationshipEvent).where(RelationshipEvent.project_id == project_id).order_by(RelationshipEvent.chapter_number))).scalars().all()

    return {
        "project": project,
        "world": world,
        "characters": characters,
        "factions": factions,
        "faction_relations": faction_relations,
        "volumes": volumes,
        "chapters": chapters,
        "foreshadowing": foreshadowing,
        "events": events,
        "relation_events": relation_events,
    }


def _character_payload(c, faction_map=None):
    faction_map = faction_map or {}
    state = _safe_dict(c.current_state)
    return {
        "id": str(c.id),
        "name": c.name,
        "role_type": c.role_type or c.character_class or "配角",
        "character_class": c.character_class or c.role_type or "配角",
        "personality": c.personality or "",
        "motivation": c.motivation or "",
        "background": c.background or "",
        "behavior_pattern": c.behavior_pattern or "",
        "language_style": c.language_style or "",
        "inner_conflict": c.inner_conflict or "",
        "growth_arc": c.growth_arc or c.growth_arc_preset or "",
        "relationships": _safe_list(c.relationships),
        "relationship_dynamics": _safe_list(c.relationship_dynamics),
        "current_state": state,
        "primary_faction_id": str(c.primary_faction_id) if c.primary_faction_id else "",
        "primary_faction": faction_map.get(str(c.primary_faction_id), "") if c.primary_faction_id else "",
        "first_appeared_chapter": c.first_appeared_chapter,
    }


def _faction_payload(f):
    return {
        "id": str(f.id),
        "name": f.name,
        "faction_type": f.faction_type or "组织",
        "description": f.description or "",
        "headquarters": f.headquarters or "",
        "territory": f.territory or "",
        "core_creed": f.core_creed or "",
        "hierarchy": _safe_list(f.hierarchy),
        "notable_members": _safe_list(f.notable_members),
        "core_conflict_of_interest": f.core_conflict_of_interest or "",
        "internal_faction_cracks": f.internal_faction_cracks or "",
        "reputation_and_reality": f.reputation_and_reality or "",
    }


def _chapter_payload(ch):
    review = _quality_review(ch.continuity_checks)
    scores = _safe_dict(review.get("scores"))
    issues = _safe_list(review.get("issues"))
    return {
        "id": str(ch.id),
        "chapter_number": ch.chapter_number,
        "title": ch.title or f"第{ch.chapter_number}章",
        "summary": ch.summary or "",
        "arc_name": ch.arc_name or "",
        "hook": ch.hook or "",
        "status": ch.status or "planned",
        "word_count": ch.word_count or 0,
        "target_words": ch.target_words or 0,
        "characters_in_chapter": _safe_list(ch.characters_in_chapter),
        "key_events": _safe_list(ch.key_events),
        "minor_events": _safe_list(ch.minor_events),
        "causality_links": _safe_list(ch.causality_links),
        "foreshadowing_tasks": _safe_list(ch.foreshadowing_tasks),
        "quality_score": ch.quality_score,
        "tension_actual": ch.tension_actual,
        "quality_review": {
            "overall_score": review.get("overall_score", ch.quality_score),
            "scores": scores,
            "issues": issues,
            "suggestions": _safe_list(review.get("suggestions")),
            "summary": review.get("summary", ""),
        },
    }

@router.get("/elements")
async def get_story_elements(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.character import Character
    from app.models.faction import Faction

    foreshadowing = (await db.execute(select(ForeshadowingPlan).where(ForeshadowingPlan.project_id == project_id))).scalars().all()
    events = (await db.execute(select(TimelineEvent).where(TimelineEvent.project_id == project_id).order_by(TimelineEvent.absolute_day))).scalars().all()

    chars = (await db.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
    char_map = {str(c.id): c.name for c in chars}
    facs = (await db.execute(select(Faction).where(Faction.project_id == project_id))).scalars().all()
    fac_map = {str(f.id): f.name for f in facs}

    return {
        "foreshadowing": [
            {
                "id": str(f.id), "name": f.name, "description": f.description,
                "plant_stage": f.plant_stage, "reveal_stage": f.reveal_stage, "status": f.status,
            } for f in foreshadowing
        ],
        "events": [
            {
                "id": str(e.id), "description": e.description, "time_point": e.time_point,
                "event_type": e.event_type, "is_major": e.is_major_event,
                "characters": [char_map.get(cid, cid) for cid in (e.related_character_ids or [])],
                "factions": [fac_map.get(fid, fid) for fid in (e.related_faction_ids or [])],
            } for e in events
        ],
    }


@router.get("/memory-center")
async def get_memory_center(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await _load_story_base(project_id, db)
    project = data["project"]
    world = data["world"]
    factions = data["factions"]
    faction_map = {str(f.id): f.name for f in factions}
    chapters = data["chapters"]

    risks = []
    for ch in chapters:
        review = _quality_review(ch.continuity_checks)
        for issue in _safe_list(review.get("issues"))[:5]:
            risks.append({
                "chapter_number": ch.chapter_number,
                "chapter_title": ch.title or f"第{ch.chapter_number}章",
                "issue": issue if isinstance(issue, str) else issue.get("description") or issue.get("issue") or str(issue),
                "severity": issue.get("severity", "") if isinstance(issue, dict) else "",
            })

    written_chapters = [c for c in chapters if (c.word_count or 0) > 0 or c.status == "written"]
    recent_events = data["events"][-30:]
    if not recent_events:
        recent_events = [
            type("ChapterEvent", (), {
                "id": ch.id,
                "description": ch.summary or "章节已规划，暂无摘要",
                "time_point": f"第{ch.chapter_number}章",
                "event_type": ch.arc_name or "章节",
                "is_major_event": bool(ch.key_events),
                "related_character_ids": [],
                "related_faction_ids": [],
            }) for ch in chapters[-20:]
        ]

    return {
        "project": {
            "id": str(project.id),
            "title": project.title,
            "genre": project.genre,
            "target_length": project.target_length,
            "target_total_words": project.target_total_words,
            "story_brief": project.story_brief,
            "core_theme": project.core_theme,
            "secondary_themes": _safe_list(project.secondary_themes),
            "motifs": _safe_list(project.motifs),
            "narrative_lines": _safe_list(project.narrative_lines),
            "writing_controls": _safe_dict(_safe_dict(project.writing_style).get("writing_controls")),
        },
        "world_rules": {
            "hard_rules": _safe_list(world.hard_rules) if world else [],
            "tone_rules": _safe_list(world.tone_rules) if world else [],
            "constraints": _safe_list(world.constraints) if world else [],
            "world_logic": _safe_dict(world.world_logic) if world else {},
        },
        "characters": [_character_payload(c, faction_map) for c in data["characters"]],
        "factions": [_faction_payload(f) for f in factions],
        "foreshadowing": [
            {
                "id": str(f.id),
                "name": f.name,
                "description": f.description or "",
                "plant_stage": f.plant_stage or "",
                "reveal_stage": f.reveal_stage or "",
                "plant_chapter": f.plant_chapter,
                "reveal_chapter": f.reveal_chapter,
                "status": f.status or "planted",
            } for f in data["foreshadowing"]
        ],
        "recent_events": [
            {
                "id": str(e.id),
                "description": e.description,
                "time_point": e.time_point,
                "event_type": e.event_type,
                "is_major": e.is_major_event,
            } for e in recent_events
        ],
        "chapter_memory": [_chapter_payload(ch) for ch in chapters[-40:]],
        "risks": risks[:50],
        "stats": {
            "chapter_count": len(chapters),
            "written_chapter_count": len(written_chapters),
            "character_count": len(data["characters"]),
            "faction_count": len(factions),
            "foreshadowing_count": len(data["foreshadowing"]),
            "risk_count": len(risks),
            "total_words": sum(c.word_count or 0 for c in chapters),
        },
    }


@router.get("/graph")
async def get_story_graph(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await _load_story_base(project_id, db)
    faction_map = {str(f.id): f.name for f in data["factions"]}
    char_map = {str(c.id): c.name for c in data["characters"]}

    nodes = []
    for c in data["characters"]:
        nodes.append({"id": str(c.id), "label": c.name, "type": "角色", "subtype": c.role_type or "配角", "summary": _short_text(c.motivation or c.personality)})
    for f in data["factions"]:
        nodes.append({"id": str(f.id), "label": f.name, "type": "组织", "subtype": f.faction_type or "组织", "summary": _short_text(f.core_conflict_of_interest or f.description)})
    for fp in data["foreshadowing"]:
        nodes.append({"id": str(fp.id), "label": fp.name, "type": "伏笔", "subtype": fp.status or "未定", "summary": _short_text(fp.description)})

    edges = []
    for c in data["characters"]:
        if c.primary_faction_id:
            edges.append({
                "source": str(c.id),
                "target": str(c.primary_faction_id),
                "source_label": c.name,
                "target_label": faction_map.get(str(c.primary_faction_id), "未知组织"),
                "relation": c.faction_rank or "所属",
                "type": "角色-组织",
                "weight": 5,
            })
        for rel in _safe_list(c.relationship_dynamics) + _safe_list(c.relationships):
            if not isinstance(rel, dict):
                continue
            target = rel.get("target") or rel.get("name") or rel.get("character") or rel.get("character_name")
            relation = rel.get("relation") or rel.get("type") or rel.get("description") or "关系"
            if target:
                edges.append({
                    "source": str(c.id),
                    "target": target,
                    "source_label": c.name,
                    "target_label": target,
                    "relation": _short_text(relation, 80),
                    "type": "角色关系",
                    "weight": rel.get("intensity", 5),
                })

    for r in data["relation_events"]:
        edges.append({
            "source": r.character_a_id,
            "target": r.character_b_id,
            "source_label": char_map.get(r.character_a_id, r.character_a_id),
            "target_label": char_map.get(r.character_b_id, r.character_b_id),
            "relation": r.new_relation,
            "type": r.relation_type or "关系事件",
            "chapter_number": r.chapter_number,
            "description": r.trigger_event,
            "weight": r.intensity,
        })

    for r in data["faction_relations"]:
        edges.append({
            "source": r.faction_a_id,
            "target": r.faction_b_id,
            "source_label": faction_map.get(r.faction_a_id, r.faction_a_id),
            "target_label": faction_map.get(r.faction_b_id, r.faction_b_id),
            "relation": r.relation_type,
            "type": "组织关系",
            "changes": _safe_list(r.timeline_changes),
            "weight": 6,
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "groups": {
            "characters": [_character_payload(c, faction_map) for c in data["characters"]],
            "factions": [_faction_payload(f) for f in data["factions"]],
            "foreshadowing": [
                {"id": str(fp.id), "name": fp.name, "status": fp.status, "description": fp.description or ""}
                for fp in data["foreshadowing"]
            ],
        },
    }


@router.get("/landscape")
async def get_story_landscape(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await _load_story_base(project_id, db)
    world = data["world"]
    volumes = data["volumes"]
    chapters = data["chapters"]

    volume_payloads = []
    for v in volumes:
        chapter_items = [ch for ch in chapters if ch.volume_id == str(v.id)]
        volume_payloads.append({
            "id": str(v.id),
            "volume_number": v.volume_number,
            "title": v.title,
            "summary": v.summary or "",
            "theme": v.theme or "",
            "emotional_arc_description": v.emotional_arc_description or "",
            "chapter_range": [v.chapter_range_start, v.chapter_range_end],
            "narrative_arcs": _safe_list(v.narrative_arcs),
            "chapters": [_chapter_payload(ch) for ch in chapter_items],
        })

    event_nodes = []
    for event in data["events"]:
        event_nodes.append({
            "id": str(event.id),
            "chapter_number": None,
            "chapter_title": event.time_point or "时间线事件",
            "arc_name": event.event_type or "正式事件",
            "label": _short_text(event.description, 100),
            "characters": _safe_list(event.related_character_ids),
            "hook": "",
            "source": "timeline",
            "status": "written",
            "is_planned": False,
        })
    for ch in chapters:
        is_written = bool((ch.word_count or 0) > 0 or (ch.content or "").strip() or ch.status in {"written", "completed"})
        events = _safe_list(ch.key_events) or ([ch.summary] if ch.summary else [])
        for idx, event in enumerate(events[:5]):
            event_nodes.append({
                "id": f"{ch.id}-{idx}",
                "chapter_number": ch.chapter_number,
                "chapter_title": ch.title or f"第{ch.chapter_number}章",
                "arc_name": ch.arc_name or "",
                "label": _short_text(str(event), 80),
                "characters": _safe_list(ch.characters_in_chapter),
                "hook": ch.hook or "",
                "source": "chapter",
                "status": "written" if is_written else "planned",
                "is_planned": not is_written,
            })

    return {
        "world": {
            "geography": _safe_dict(world.geography) if world else {},
            "social_structure": _safe_dict(world.social_structure) if world else {},
            "power_system": _safe_dict(world.power_system) if world else {},
            "history": _safe_dict(world.history) if world else {},
            "culture": _safe_dict(world.culture) if world else {},
            "special_rules": _safe_dict(world.special_rules) if world else {},
            "world_logic": _safe_dict(world.world_logic) if world else {},
        },
        "volumes": volume_payloads,
        "event_nodes": event_nodes,
        "scene_clusters": [
            {
                "name": arc or "未分弧线",
                "chapters": [_chapter_payload(ch) for ch in chapters if (ch.arc_name or "未分弧线") == arc],
            }
            for arc in sorted({ch.arc_name or "未分弧线" for ch in chapters})
        ],
    }


@router.get("/quality-dashboard")
async def get_quality_dashboard(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    data = await _load_story_base(project_id, db)
    chapters = data["chapters"]
    chapter_rows = [_chapter_payload(ch) for ch in chapters]
    scored = [c["quality_score"] for c in chapter_rows if isinstance(c["quality_score"], int)]
    written = [c for c in chapter_rows if c["word_count"] > 0 or c["status"] == "written"]

    issue_rows = []
    dimension_totals = {}
    dimension_counts = {}
    for ch in chapter_rows:
        for key, value in _safe_dict(ch["quality_review"].get("scores")).items():
            if isinstance(value, (int, float)):
                dimension_totals[key] = dimension_totals.get(key, 0) + value
                dimension_counts[key] = dimension_counts.get(key, 0) + 1
        for issue_index, issue in enumerate(_safe_list(ch["quality_review"].get("issues"))):
            issue_rows.append({
                "chapter_id": ch["id"],
                "issue_index": issue_index,
                "chapter_number": ch["chapter_number"],
                "chapter_title": ch["title"],
                "issue": issue if isinstance(issue, str) else issue.get("description") or issue.get("issue") or str(issue),
                "severity": issue.get("severity", "") if isinstance(issue, dict) else "",
                "target_text": issue.get("target_text", "") if isinstance(issue, dict) else "",
                "fix_mode": issue.get("fix_mode", "") if isinstance(issue, dict) else "",
                "fix_suggestion": issue.get("fix_suggestion", "") if isinstance(issue, dict) else "",
                "raw_issue": issue,
            })

    return {
        "summary": {
            "chapter_count": len(chapter_rows),
            "written_chapter_count": len(written),
            "total_words": sum(c["word_count"] for c in chapter_rows),
            "average_words": round(sum(c["word_count"] for c in written) / len(written)) if written else 0,
            "average_quality": round(sum(scored) / len(scored), 1) if scored else None,
            "low_quality_count": len([s for s in scored if s < 7]),
            "issue_count": len(issue_rows),
        },
        "chapters": chapter_rows,
        "issues": issue_rows,
        "dimensions": [
            {"name": key, "score": round(dimension_totals[key] / dimension_counts[key], 1)}
            for key in sorted(dimension_totals)
        ],
        "trends": [
            {
                "chapter_number": ch["chapter_number"],
                "quality_score": ch["quality_score"],
                "word_count": ch["word_count"],
                "tension_actual": ch["tension_actual"],
            } for ch in chapter_rows
        ],
    }


@router.post("/quality-dashboard/complete-issue")
async def complete_quality_issue(
    project_id: str,
    body: CompleteQualityIssueRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.chapter import Chapter

    chapter = (await db.execute(
        select(Chapter).where(Chapter.id == body.chapter_id, Chapter.project_id == project_id)
    )).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")

    checks = _safe_dict(chapter.continuity_checks).copy()
    review = _safe_dict(checks.get("quality_review")).copy()
    issues = list(_safe_list(review.get("issues")))
    if not issues:
        return {"ok": True, "remaining": 0}

    removed = None
    if isinstance(body.issue_index, int) and 0 <= body.issue_index < len(issues):
        removed = issues.pop(body.issue_index)
    elif body.issue:
        for idx, issue in enumerate(issues):
            text = issue if isinstance(issue, str) else issue.get("description") or issue.get("issue") or str(issue)
            if text == body.issue:
                removed = issues.pop(idx)
                break

    if removed is None:
        raise HTTPException(404, "质量问题不存在或已处理")

    review["issues"] = issues
    resolved = _safe_list(checks.get("quality_resolved_issues"))
    resolved.append({
        "issue": removed,
        "resolved_by": "manual",
        "note": "在质量仪表盘标记为修复完成",
    })
    checks["quality_review"] = review
    checks["quality_resolved_issues"] = resolved[-100:]
    chapter.continuity_checks = checks
    await db.commit()
    return {"ok": True, "remaining": len(issues)}


class CreateForeshadowingRequest(BaseModel):
    name: str
    description: str = ""
    plant_stage: str = ""
    reveal_stage: str = ""
    plant_chapter: int | None = None
    reveal_chapter: int | None = None
    status: str = "planted"


@router.post("/foreshadowing")
async def create_foreshadowing(project_id: str, body: CreateForeshadowingRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    fp = ForeshadowingPlan(project_id=project_id, **body.model_dump())
    db.add(fp)
    await db.flush()
    return {"foreshadowing": fp}


@router.delete("/foreshadowing/{fp_id}")
async def delete_foreshadowing(project_id: str, fp_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ForeshadowingPlan).where(ForeshadowingPlan.id == fp_id, ForeshadowingPlan.project_id == project_id))
    fp = result.scalar_one_or_none()
    if not fp:
        raise HTTPException(404, "伏笔不存在")
    await db.delete(fp)
    return {"success": True}


class CreateEventRequest(BaseModel):
    description: str
    time_point: str = ""
    event_type: str = "event"
    is_major: bool = False
    related_character_ids: list[str] = []
    related_faction_ids: list[str] = []


@router.post("/events")
async def create_event(project_id: str, body: CreateEventRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ev = TimelineEvent(project_id=project_id, description=body.description, time_point=body.time_point, event_type=body.event_type, is_major_event=body.is_major, related_character_ids=body.related_character_ids, related_faction_ids=body.related_faction_ids)
    db.add(ev)
    await db.flush()
    return {"event": ev}


@router.delete("/events/{ev_id}")
async def delete_event(project_id: str, ev_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TimelineEvent).where(TimelineEvent.id == ev_id, TimelineEvent.project_id == project_id))
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "事件不存在")
    await db.delete(ev)
    return {"success": True}
