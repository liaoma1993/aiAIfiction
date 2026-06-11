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


def _quality_severity(score: int | float | None = None, severity: str = "") -> str:
    if severity in {"critical", "high", "medium", "low"}:
        return severity
    if score is None:
        return "medium"
    if score < 55:
        return "high"
    if score < 75:
        return "medium"
    return "low"


def _score_status(score: int | float, passed: bool = True) -> str:
    if not passed or score < 60:
        return "fail"
    if score < 75:
        return "warning"
    return "pass"


def _flatten_world_values(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            items.extend(_flatten_world_values(item))
        return items
    if isinstance(value, dict):
        items: list[str] = []
        for key, item in value.items():
            nested = _flatten_world_values(item)
            if nested:
                items.extend([f"{key}：{x}" for x in nested])
            elif item not in (None, "", [], {}):
                items.append(f"{key}：{item}")
        return items
    return [str(value)]


def _world_rule_score(world, project) -> dict:
    if not world:
        return {
            "score": 0,
            "passed": False,
            "issues": [{"field": "world_setting", "issue": "尚未生成世界观规则", "severity": "high"}],
            "warnings": [],
        }
    hard_rules = _safe_list(world.hard_rules)
    constraints = _safe_list(world.constraints)
    logic_items = _flatten_world_values(world.world_logic or {})
    issues: list[dict] = []
    warnings: list[dict] = []
    if len(hard_rules) < 4:
        issues.append({"field": "hard_rules", "issue": "hard_rules 少于4条，世界硬约束不足", "severity": "medium"})
    if len(constraints) < 3:
        issues.append({"field": "constraints", "issue": "constraints 少于3条，生成边界不足", "severity": "medium"})
    if not logic_items:
        issues.append({"field": "world_logic", "issue": "world_logic 为空，缺少世界运行逻辑", "severity": "high"})
    combined = [str(x) for x in hard_rules + constraints + logic_items]
    if project and project.core_theme and not any(project.core_theme in item for item in combined):
        warnings.append({"field": "core_theme", "issue": "世界规则未显式绑定项目核心主题，后续可能偏题", "severity": "medium"})
    if not any("代价" in item or "成本" in item for item in combined):
        warnings.append({"field": "cost_rule", "issue": "缺少能力/资源/制度代价规则，容易出现无成本开挂", "severity": "medium"})
    if not any("信息" in item or "秘密" in item or "知道" in item for item in combined):
        warnings.append({"field": "information_boundary", "issue": "缺少信息边界规则，角色可能知道不该知道的事", "severity": "medium"})
    score = max(0, 100 - len(issues) * 12 - len(warnings) * 6)
    return {"score": score, "passed": score >= 75 and not any(i.get("severity") == "high" for i in issues), "issues": issues, "warnings": warnings}


def _arc_quality_for_volume(arcs: list[dict], arc_bridge_checks: list[dict] | None = None) -> dict:
    if not arcs:
        return {"score": 35, "issues": [{"field": "narrative_arcs", "issue": "本卷还没有拆出弧线", "severity": "high"}], "warnings": []}
    issues: list[dict] = []
    warnings: list[dict] = []
    for idx, arc in enumerate(arcs):
        name = arc.get("name", f"弧线{idx + 1}") if isinstance(arc, dict) else f"弧线{idx + 1}"
        if not isinstance(arc, dict):
            issues.append({"arc_index": idx, "arc_name": name, "field": "arc", "issue": "弧线数据格式异常", "severity": "high"})
            continue
        if not arc.get("opening_state"):
            issues.append({"arc_index": idx, "arc_name": name, "field": "opening_state", "issue": "缺少弧线开局状态", "severity": "medium"})
        if not arc.get("ending_state"):
            issues.append({"arc_index": idx, "arc_name": name, "field": "ending_state", "issue": "缺少弧线终点状态", "severity": "medium"})
        if idx > 0 and not (arc.get("handoff_from_previous") or arc.get("dependence_on_previous")):
            issues.append({"arc_index": idx, "arc_name": name, "field": "handoff_from_previous", "issue": "缺少上承交接", "severity": "high"})
        if not (arc.get("handoff_to_next") or arc.get("payoff_for_next")):
            warnings.append({"arc_index": idx, "arc_name": name, "field": "handoff_to_next", "issue": "下启钩子不够明确", "severity": "medium"})
        if not arc.get("continuity_chain"):
            issues.append({"arc_index": idx, "arc_name": name, "field": "continuity_chain", "issue": "缺少因果链", "severity": "medium"})
        if not isinstance(arc.get("arc_steps"), list) or len(arc.get("arc_steps") or []) < 4:
            issues.append({"arc_index": idx, "arc_name": name, "field": "arc_steps", "issue": "变化台阶少于4个", "severity": "high"})
    for check in _safe_list(arc_bridge_checks):
        gate = _safe_dict(check.get("quality_gate") or check.get("bridge_check") or check)
        for issue in _safe_list(gate.get("related_issues") or gate.get("issues")):
            if isinstance(issue, dict):
                issues.append({**issue, "severity": issue.get("severity", "medium")})
        for warning in _safe_list(gate.get("related_warnings") or gate.get("warnings")):
            if isinstance(warning, dict):
                warnings.append({**warning, "severity": warning.get("severity", "medium")})
    score = max(0, 100 - len(issues) * 6 - len(warnings) * 3)
    return {"score": score, "issues": issues, "warnings": warnings}


def _volume_quality(volume, volume_chapters: list) -> dict:
    arcs = _safe_list(volume.narrative_arcs)
    summary_text = "\n".join([x for x in [volume.summary, volume.outline, volume.theme] if x])
    arc_quality = _arc_quality_for_volume(arcs, _safe_list(volume.arc_bridge_checks))
    arc_steps_count = sum(len(_safe_list(arc.get("arc_steps"))) for arc in arcs if isinstance(arc, dict))
    chapter_target = volume.chapter_count or max(0, (volume.chapter_range_end or 0) - (volume.chapter_range_start or 0) + 1)
    capacity_ratio = min(1, arc_steps_count / max(4, round((chapter_target or 0) / 2))) if chapter_target else (1 if arc_steps_count else 0)
    has_foreshadowing = any(_safe_list(arc.get("foreshadowing_plan")) for arc in arcs if isinstance(arc, dict))
    has_character_or_faction = any(
        _safe_list(arc.get("character_introduction_plan")) or _safe_list(arc.get("character_focus")) or _safe_list(arc.get("faction_introduction_plan")) or _safe_list(arc.get("faction_focus"))
        for arc in arcs if isinstance(arc, dict)
    )
    last_arc = arcs[-1] if arcs and isinstance(arcs[-1], dict) else {}
    dimensions = [
        {"key": "volume_goal", "label": "卷目标", "score": 90 if len(summary_text) >= 80 else 74 if len(summary_text) >= 30 else 45, "issue": "卷目标偏虚，需要写清这一卷主角要完成什么。"},
        {"key": "pressure_upgrade", "label": "压力升级", "score": 86 if len(arcs) >= 3 else 68 if len(arcs) >= 2 else 42, "issue": "压力升级不够清楚，容易变成事件平铺。"},
        {"key": "arc_chain", "label": "弧线链", "score": arc_quality["score"], "issue": "弧线链存在断点，需要优化前后交接。"},
        {"key": "protagonist_change", "label": "主角变化", "score": 84 if any(isinstance(arc, dict) and arc.get("protagonist_change") for arc in arcs) else 58, "issue": "主角阶段变化不够明确。"},
        {"key": "chapter_capacity", "label": "章节承载", "score": 35 if not arcs else round(55 + capacity_ratio * 35), "issue": "变化台阶偏少，展开章节后可能水或散。"},
        {"key": "foreshadowing", "label": "伏笔安排", "score": 82 if has_foreshadowing else 62, "issue": "伏笔安排偏弱，建议补铺设/推进/回收。"},
        {"key": "ending_hook", "label": "卷末钩子", "score": 86 if (last_arc.get("handoff_to_next") or last_arc.get("payoff_for_next") or last_arc.get("ending_state")) else 48, "issue": "卷末钩子不清楚，下一卷入口偏弱。"},
        {"key": "role_faction_usage", "label": "角色势力", "score": 82 if has_character_or_faction else 66, "issue": "角色/势力使用偏弱，容易只停留在设定名词。"},
    ]
    score = round(sum(d["score"] for d in dimensions) / len(dimensions))
    issues = [{"field": d["key"], "issue": d["issue"], "severity": _quality_severity(d["score"])} for d in dimensions if d["score"] < 60]
    warnings = [{"field": d["key"], "issue": d["issue"], "severity": _quality_severity(d["score"])} for d in dimensions if 60 <= d["score"] < 75]
    return {
        "score": score,
        "passed": score >= 75 and not issues,
        "dimensions": dimensions,
        "issues": issues,
        "warnings": warnings,
        "arc_quality": arc_quality,
        "arc_steps_count": arc_steps_count,
        "chapter_count": len(volume_chapters),
        "written_chapter_count": len([ch for ch in volume_chapters if (ch.word_count or 0) > 0]),
    }


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
    from app.models.chapter import Chapter, GenerationTask
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
    tasks = (await db.execute(select(GenerationTask).where(GenerationTask.project_id == project_id).order_by(GenerationTask.created_at.desc()).limit(80))).scalars().all()

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
        "tasks": tasks,
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
    project = data["project"]
    world = data["world"]
    volumes = data["volumes"]
    chapters = data["chapters"]
    tasks = data["tasks"]
    chapter_rows = [_chapter_payload(ch) for ch in chapters]
    scored = [c["quality_score"] for c in chapter_rows if isinstance(c["quality_score"], int)]
    written = [c for c in chapter_rows if c["word_count"] > 0 or c["status"] == "written"]

    issue_rows = []
    dimension_totals = {}
    dimension_counts = {}
    longform_flags = {
        "missing_opening": 0,
        "missing_state_validation": 0,
        "weak_hook": 0,
        "state_delta_gap": 0,
        "entry_gate_gap": 0,
        "voice_or_info_gap": 0,
    }
    for ch in chapter_rows:
        for key, value in _safe_dict(ch["quality_review"].get("scores")).items():
            if isinstance(value, (int, float)):
                dimension_totals[key] = dimension_totals.get(key, 0) + value
                dimension_counts[key] = dimension_counts.get(key, 0) + 1
        raw_ch = next((item for item in chapters if str(item.id) == ch["id"]), None)
        checks = _safe_dict(raw_ch.continuity_checks if raw_ch else {})
        blueprint = _safe_dict(raw_ch.blueprint if raw_ch else {})
        state_validation = _safe_dict(checks.get("state_extract_validation"))
        if raw_ch and (raw_ch.word_count or 0) > 0:
            if not _safe_list(blueprint.get("opening_requirements")) and not _safe_list(checks.get("opening_requirements")):
                longform_flags["missing_opening"] += 1
            if state_validation and not state_validation.get("passed", True):
                longform_flags["missing_state_validation"] += 1
            hook_design = _safe_dict(blueprint.get("hook_design") or checks.get("hook_design"))
            if hook_design and int(hook_design.get("hook_strength") or 0) < 3:
                longform_flags["weak_hook"] += 1
            indispensability = _safe_dict(blueprint.get("indispensability_check") or checks.get("indispensability_check"))
            if indispensability and not _safe_list(indispensability.get("if_deleted_what_breaks")):
                longform_flags["state_delta_gap"] += 1
            entry_gate = _safe_dict(blueprint.get("entry_gate_checks") or checks.get("entry_gate_checks"))
            if entry_gate and (entry_gate.get("blocked_sudden_functions") or entry_gate.get("failure")):
                longform_flags["entry_gate_gap"] += 1
            if not _safe_dict(blueprint.get("character_voice_constraints")) or not _safe_dict(blueprint.get("information_reveal_plan")):
                longform_flags["voice_or_info_gap"] += 1
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

    volume_chapter_map = {
        str(volume.id): [ch for ch in chapters if str(ch.volume_id or "") == str(volume.id)]
        for volume in volumes
    }
    world_quality = _world_rule_score(world, project)
    volume_quality_rows = []
    arc_quality_rows = []
    quality_scores = []
    quality_issues = []

    def add_score(scope: str, scope_id: str, scope_name: str, score_type: str, score: int, passed: bool, dimensions=None):
        quality_scores.append({
            "scope": scope,
            "scope_id": scope_id,
            "scope_name": scope_name,
            "score_type": score_type,
            "score": score,
            "passed": passed,
            "status": _score_status(score, passed),
            "dimensions": dimensions or [],
        })

    def add_issue(scope: str, scope_id: str, scope_name: str, title: str, description: str, severity: str = "medium", action: str = "", fix_action: str = "", target: dict | None = None):
        quality_issues.append({
            "scope": scope,
            "scope_id": scope_id,
            "scope_name": scope_name,
            "title": title,
            "description": description,
            "severity": severity,
            "action": action,
            "fix_action": fix_action,
            "target": target or {},
        })

    add_score("world", str(world.id) if world else "", "世界规则", "世界规则闸门", int(world_quality["score"]), bool(world_quality["passed"]))
    for item in world_quality["issues"]:
        add_issue("world", str(world.id) if world else "", "世界规则", item.get("issue", "世界规则缺口"), item.get("issue", ""), item.get("severity", "medium"), "open_world", "strengthen_world_rules")
    for item in world_quality["warnings"]:
        add_issue("world", str(world.id) if world else "", "世界规则", item.get("issue", "世界规则提醒"), item.get("issue", ""), item.get("severity", "medium"), "open_world", "strengthen_world_rules")

    outline_stage_count = len(_safe_list(project.writing_style.get("long_term_plan", {}).get("stage_plan") if isinstance(project.writing_style, dict) else []))
    outline_score = 85 if volumes and outline_stage_count else 72 if volumes else 45
    add_score("outline", str(project.id), "全书大纲", "大纲结构分", outline_score, outline_score >= 75, [
        {"key": "volume_count", "label": "分卷数量", "score": 90 if volumes else 40},
        {"key": "stage_plan", "label": "长线阶段", "score": 88 if outline_stage_count else 65},
    ])
    if not volumes:
        add_issue("outline", str(project.id), "全书大纲", "缺少分卷大纲", "项目还没有可用于后续写作的分卷结构。", "high", "open_outline", "generate_outline")
    elif not outline_stage_count:
        add_issue("outline", str(project.id), "全书大纲", "长线阶段未结构化", "项目写作风格中缺少可追踪的长线阶段计划。", "medium", "open_outline", "adjust_outline")

    for volume in volumes:
        v_chapters = volume_chapter_map.get(str(volume.id), [])
        vq = _volume_quality(volume, v_chapters)
        volume_quality_rows.append({
            "volume_id": str(volume.id),
            "volume_number": volume.volume_number,
            "title": volume.title,
            **vq,
        })
        add_score("volume", str(volume.id), f"卷{volume.volume_number} · {volume.title}", "卷级结构分", int(vq["score"]), bool(vq["passed"]), vq.get("dimensions", []))
        for item in vq.get("issues", []):
            add_issue("volume", str(volume.id), f"卷{volume.volume_number} · {volume.title}", item.get("issue", "卷结构问题"), item.get("issue", ""), item.get("severity", "medium"), "open_volume_detail", "adjust_volume")
        for item in vq.get("warnings", []):
            add_issue("volume", str(volume.id), f"卷{volume.volume_number} · {volume.title}", item.get("issue", "卷结构提醒"), item.get("issue", ""), item.get("severity", "medium"), "open_volume_detail", "adjust_volume")

        arcs = _safe_list(volume.narrative_arcs)
        arc_quality = vq.get("arc_quality", {})
        add_score("arc", str(volume.id), f"卷{volume.volume_number}弧线链", "弧线连续性分", int(arc_quality.get("score", 0)), int(arc_quality.get("score", 0)) >= 75)
        for issue in _safe_list(arc_quality.get("issues")):
            idx = issue.get("arc_index")
            arc_name = issue.get("arc_name") or (arcs[idx].get("name") if isinstance(idx, int) and idx < len(arcs) and isinstance(arcs[idx], dict) else "未命名弧线")
            row = {
                "volume_id": str(volume.id),
                "volume_number": volume.volume_number,
                "volume_title": volume.title,
                "arc_index": idx,
                "arc_name": arc_name,
                "issue": issue.get("issue", ""),
                "severity": issue.get("severity", "medium"),
            }
            arc_quality_rows.append(row)
            add_issue("arc", str(volume.id), f"卷{volume.volume_number} · {arc_name}", issue.get("issue", "弧线连续性问题"), issue.get("issue", ""), issue.get("severity", "medium"), "open_arc_detail", "repair_arc", {"volume_id": str(volume.id), "arc_index": idx})
        for warning in _safe_list(arc_quality.get("warnings")):
            idx = warning.get("arc_index")
            arc_name = warning.get("arc_name") or (arcs[idx].get("name") if isinstance(idx, int) and idx < len(arcs) and isinstance(arcs[idx], dict) else "未命名弧线")
            add_issue("arc", str(volume.id), f"卷{volume.volume_number} · {arc_name}", warning.get("issue", "弧线连续性提醒"), warning.get("issue", ""), warning.get("severity", "medium"), "open_arc_detail", "polish_arc_handoff", {"volume_id": str(volume.id), "arc_index": idx})

    for row in issue_rows:
        add_issue("chapter", row["chapter_id"], f"第{row['chapter_number']}章 · {row['chapter_title']}", row.get("issue", "章节质量问题"), row.get("fix_suggestion") or row.get("issue", ""), row.get("severity") or "medium", "open_chapter", "repair_chapter", {"chapter_id": row["chapter_id"], "issue_index": row.get("issue_index")})
    for ch in chapters:
        checks = _safe_dict(ch.continuity_checks)
        diagnosis = _safe_dict(checks.get("prewrite_diagnosis"))
        for item in _safe_list(diagnosis.get("blocking_issues")):
            if isinstance(item, dict):
                add_issue("chapter", str(ch.id), f"第{ch.chapter_number}章 · {ch.title}", item.get("problem", "写作前置诊断未通过"), item.get("fix", item.get("problem", "")), "high", "open_chapter", "inject_prewrite_fix", {"chapter_id": str(ch.id)})
    failed_tasks = [task for task in tasks if task.status == "failed"]
    for task in failed_tasks[:12]:
        add_issue("task", str(task.id), task.task_type, f"任务失败：{task.task_type}", _short_text(task.error_message or "任务失败", 220), "medium", "open_tasks", "retry_task", {"task_id": str(task.id)})

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    quality_issues.sort(key=lambda x: (severity_order.get(x.get("severity", "medium"), 2), x.get("scope", ""), x.get("scope_name", "")))

    aggregate_scores = {
        "overall": round(sum(item["score"] for item in quality_scores) / len(quality_scores)) if quality_scores else 0,
        "world": int(world_quality["score"]),
        "outline": outline_score,
        "volume": round(sum(v["score"] for v in volume_quality_rows) / len(volume_quality_rows)) if volume_quality_rows else 0,
        "arc": round(sum(v["arc_quality"]["score"] for v in volume_quality_rows) / len(volume_quality_rows)) if volume_quality_rows else 0,
        "chapter": round((sum(scored) / len(scored)) * 10) if scored else 0,
        "task": max(0, 100 - len(failed_tasks) * 8),
    }

    written_count = max(1, len(written))
    def _score_from_flags(flag_count: int) -> int:
        return max(0, min(100, round(100 - (flag_count / written_count) * 100)))

    longform_health = {
        "arc_continuity": round(dimension_totals.get("continuity", 0) / dimension_counts.get("continuity", 1) * 10) if dimension_counts.get("continuity") else _score_from_flags(longform_flags["missing_opening"]),
        "character_consistency": round(dimension_totals.get("character_consistency", 0) / dimension_counts.get("character_consistency", 1) * 10) if dimension_counts.get("character_consistency") else _score_from_flags(longform_flags["voice_or_info_gap"]),
        "faction_entry_slope": _score_from_flags(longform_flags["entry_gate_gap"]),
        "protagonist_state_memory": _score_from_flags(longform_flags["missing_state_validation"]),
        "hook_strength": round(dimension_totals.get("hook", 0) / dimension_counts.get("hook", 1) * 10) if dimension_counts.get("hook") else _score_from_flags(longform_flags["weak_hook"]),
        "state_delta_density": round(dimension_totals.get("indispensability", 0) / dimension_counts.get("indispensability", 1) * 10) if dimension_counts.get("indispensability") else _score_from_flags(longform_flags["state_delta_gap"]),
        "info_reveal_control": round(dimension_totals.get("information_reveal", 0) / dimension_counts.get("information_reveal", 1) * 10) if dimension_counts.get("information_reveal") else _score_from_flags(longform_flags["voice_or_info_gap"]),
        "ai_flavor_risk": round(100 - (dimension_totals.get("ai_flavor", 0) / dimension_counts.get("ai_flavor", 1) * 10)) if dimension_counts.get("ai_flavor") else 0,
        "flags": longform_flags,
    }

    return {
        "summary": {
            "chapter_count": len(chapter_rows),
            "written_chapter_count": len(written),
            "total_words": sum(c["word_count"] for c in chapter_rows),
            "average_words": round(sum(c["word_count"] for c in written) / len(written)) if written else 0,
            "average_quality": round(sum(scored) / len(scored), 1) if scored else None,
            "low_quality_count": len([s for s in scored if s < 7]),
            "issue_count": len(issue_rows),
            "global_issue_count": len(quality_issues),
            "high_issue_count": len([i for i in quality_issues if i.get("severity") in {"critical", "high"}]),
            "failed_task_count": len(failed_tasks),
            "overall_score": aggregate_scores["overall"],
        },
        "project": {
            "id": str(project.id),
            "title": project.title,
            "genre": project.genre,
            "core_theme": project.core_theme,
        },
        "aggregate_scores": aggregate_scores,
        "quality_scores": quality_scores,
        "quality_issues": quality_issues,
        "world_quality": world_quality,
        "volume_quality": volume_quality_rows,
        "arc_quality_issues": arc_quality_rows,
        "failed_tasks": [
            {
                "id": str(task.id),
                "task_type": task.task_type,
                "error_message": task.error_message,
                "updated_at": task.updated_at.isoformat() if task.updated_at else "",
            } for task in failed_tasks[:20]
        ],
        "chapters": chapter_rows,
        "issues": issue_rows,
        "dimensions": [
            {"name": key, "score": round(dimension_totals[key] / dimension_counts[key], 1)}
            for key in sorted(dimension_totals)
        ],
        "longform_health": longform_health,
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
