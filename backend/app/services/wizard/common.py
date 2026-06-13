from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
import asyncio
import io
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote
from app.database import get_db, async_session
from app.models.user import User
from app.models.project import Project
from app.models.volume import Volume
from app.models.character import Character
from app.models.faction import Faction, FactionRelation
from app.models.outline import Outline, OutlineNode, ForeshadowingPlan
from app.models.chapter import Chapter, ChapterVersion, GenerationTask
from app.models.timeline import TimelineEvent, StoryStateTrail
from app.models.world_setting import WorldSetting
from app.models.writing_style_skill import WritingStyleSkill
from app.api.deps import get_current_user
from app.services.ai_service import AIService, SYSTEM_EDITOR, PROMPT_VERSION
from app.services.task_manager import start_task, get_task_persisted, list_tasks_persisted, update_progress, cancel_task, is_cancelled
from app.services.story_bible import build_story_bible
from app.services.context_builder import build_generation_context
from app.schemas.wizard import (
    AdjustOutlineChatRequest,
    AdjustOutlineRequest,
    ApplyDraftRequest,
    ApplyStateRequest,
    ApplyStoryRequest,
    AuditChapterRequest,
    ExpandArcRequest,
    ExpandVolumeArcsRequest,
    ExportManuscriptRequest,
    GenerateRequest,
    ProjectPlanChatRequest,
    RepairFromReviewRequest,
    ReviseChapterRequest,
    ReviseVolumeArcRequest,
    SplitChapterRequest,
    StorySuggestRequest,
    WriteChapterRequest,
)
from app.services.wizard.arc_tools import (
    _arc_chapter_range_guidance,
    _arc_is_important_for_chapter_budget,
    _arc_is_short_bridge,
    _arc_quality_gate,
    _build_arc_bridge_checks,
    _build_arc_continuity_index,
    _chapter_blueprint_gate,
    _normalize_narrative_arc_payload,
    _score_arc_quality,
)
from app.services.wizard.context_budget import (
    _build_budgeted_character_summary,
    _build_budgeted_faction_summary,
    _build_character_profile,
    _build_faction_profile,
    _clip_context,
    _compact_json,
    _safe_str,
    _writing_context_limits,
)
from app.services.wizard.planning import (
    _as_string_list,
    _build_wizard_planning_memory,
    _draft_meta_from_style,
    _format_stage_plan_item,
    _format_tone_profile,
    _format_type_model,
    _format_wizard_planning_memory,
    _planning_value_text,
    _selected_draft_from_project,
    _wizard_story_brief,
    _world_rule_defaults_from_project,
)
from app.services.wizard.repair_guards import (
    FULL_CHAPTER_REPAIR_MODES,
    LOCAL_REVISE_MODES,
    _split_hook_marker,
    _validate_full_chapter_revision,
)
from app.services.wizard.state_tools import (
    _build_story_state_snapshot,
    _clip_text,
    _format_chapter_continuity_payload,
    _list_preview,
    _parse_state_snapshot,
    _safe_json,
    _validate_state_extract_payload,
)
from app.services.wizard.writing_controls import (
    DEFAULT_WRITING_CONTROLS,
    _active_writing_style_skill,
    _early_grip_guidance,
    _format_project_writing_guidance,
    _merge_writing_controls,
    _readability_guidance,
    _writing_controls_guidance,
)

BATCH_WRITE_ARC_TIMEOUT_SECONDS = 5 * 60 * 60
_outline_write_locks: dict[str, asyncio.Lock] = {}


PROMPT_MODULES = [
    {"key": "continuity_rules", "name": "连续性规则", "status": "active", "used_in": ["expand_volume_arcs", "expand_arc_chapters", "write_chapter"], "checks": ["connects_from", "connects_to", "handoff", "state_delta"]},
    {"key": "arc_rules", "name": "弧线起承转交", "status": "active", "used_in": ["expand_volume_arcs", "revise_volume_arc"], "checks": ["opening_state", "ending_state", "arc_steps", "handoff_to_next"]},
    {"key": "chapter_blueprint_rules", "name": "章节蓝图闸门", "status": "active", "used_in": ["expand_arc_chapters"], "checks": ["key_events", "arc_step_refs", "state_delta", "entry_gate_checks"]},
    {"key": "anti_ai_style_rules", "name": "去 AI 味规则", "status": "active", "used_in": ["write_chapter", "revise_chapter"], "checks": ["concrete_opening", "subtext_dialogue", "sensory_detail", "specific_hook"]},
    {"key": "character_entry_rules", "name": "角色入场坡度", "status": "active", "used_in": ["expand_volume_arcs", "expand_arc_chapters"], "checks": ["first_signal", "indirect_presence", "initial_conflict", "cost_of_contact"]},
    {"key": "faction_entry_rules", "name": "组织入场坡度", "status": "active", "used_in": ["expand_volume_arcs", "expand_arc_chapters"], "checks": ["symbol_or_trace", "low_level_contact", "rule_pressure", "formal_entry_condition"]},
    {"key": "webnovel_pacing_rules", "name": "网文追读节奏", "status": "active", "used_in": ["expand_volume_arcs", "expand_arc_chapters", "write_chapter"], "checks": ["short_goal", "external_friction", "instant_feedback", "chapter_hook"]},
    {"key": "world_rule_conflict_rules", "name": "世界规则矛盾检测", "status": "active", "used_in": ["project_health", "world_rule_audit"], "checks": ["hard_rules", "constraints", "world_logic", "new_setting_conflict"]},
]



def _get_outline_write_lock(project_id: str) -> asyncio.Lock:
    lock = _outline_write_locks.get(project_id)
    if lock is None:
        lock = asyncio.Lock()
        _outline_write_locks[project_id] = lock
    return lock

def _status_after_content_change(status: str | None) -> str:
    if status in {"completed", "written", "reviewed"}:
        return status
    return "writing"

def _review_score_value(review: dict) -> int:
    try:
        return int(review.get("overall_score") or 0)
    except (TypeError, ValueError):
        return 0

def _quality_issue_severity(issue: dict | str) -> str:
    if not isinstance(issue, dict):
        return ""
    return str(issue.get("severity", "")).strip().lower()

def _cap_quality_score_by_issues(score: int, issues: list) -> int:
    severities = {_quality_issue_severity(issue) for issue in issues}
    if severities & {"critical", "致命"}:
        return min(score, 6)
    if severities & {"high", "严重"}:
        return min(score, 7)
    return score

def _normalize_quality_review_for_dashboard(review: dict) -> dict:
    normalized = dict(review or {})
    issues = list(normalized.get("issues") or [])
    if not issues:
        normalized["issues"] = []
        return normalized

    score = _review_score_value(normalized)
    capped_score = _cap_quality_score_by_issues(score, issues)
    if capped_score != score:
        normalized["overall_score"] = capped_score
        normalized["passed"] = False
        normalized["audit_policy"] = "存在致命/严重问题，综合分已按问题严重度封顶"
        score = capped_score
    blocking = [
        issue for issue in issues
        if _quality_issue_severity(issue) in {"critical", "high", "致命", "严重"}
    ]
    soft = [
        issue for issue in issues
        if issue not in blocking
    ]
    if score >= 8 and not blocking:
        suggestions = list(normalized.get("suggestions") or [])
        for issue in soft:
            if isinstance(issue, dict):
                text = issue.get("fix_suggestion") or issue.get("description") or issue.get("issue")
            else:
                text = str(issue)
            if text:
                suggestions.append(text)
        normalized["issues"] = []
        normalized["suggestions"] = suggestions[:12]
        normalized["passed"] = True
        normalized["audit_policy"] = "高分且无阻断问题，低风险建议不进入当前问题清单"
    else:
        normalized["issues"] = issues[:5]
    return normalized

def _save_quality_review_to_chapter(chapter: Chapter, review: dict) -> None:
    if not isinstance(review, dict):
        return
    review = _normalize_quality_review_for_dashboard(review)
    score = _review_score_value(review)
    if score:
        chapter.quality_score = score
    checks = dict(chapter.continuity_checks or {})
    checks["quality_review"] = review
    checks["quality_review_status"] = "completed"
    chapter.continuity_checks = checks
    flag_modified(chapter, "continuity_checks")

def _remember_resolved_quality_issue(chapter: Chapter, body: "ReviseChapterRequest", review: dict | None = None) -> None:
    issue = (body.resolved_issue or "").strip()
    controls_issue = body.controls.get("quality_resolved_issue") if isinstance(body.controls, dict) else None
    if not issue and isinstance(controls_issue, dict):
        issue = json.dumps(controls_issue.get("raw_issue") or controls_issue, ensure_ascii=False)
    if not issue:
        return

    checks = dict(chapter.continuity_checks or {})
    resolved = list(checks.get("quality_resolved_issues") or [])
    resolved.append({
        "issue": issue[:4000],
        "issue_index": body.resolved_issue_index,
        "resolved_by": "ai_revise",
        "mode": body.mode,
        "review_issue_count_after": len(review.get("issues") or []) if isinstance(review, dict) else None,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "note": "质量大盘修复后已重新审稿；当前问题清单以复审结果为准。",
    })
    checks["quality_resolved_issues"] = resolved[-100:]
    chapter.continuity_checks = checks
    flag_modified(chapter, "continuity_checks")

async def _get_previous_chapter(db: AsyncSession, project_id: str, volume_id: str | None, chapter_number: int | None) -> Chapter | None:
    if not volume_id or not chapter_number:
        return None
    result = await db.execute(
        select(Chapter)
        .where(
            Chapter.project_id == project_id,
            Chapter.volume_id == volume_id,
            Chapter.chapter_number < chapter_number,
        )
        .order_by(Chapter.chapter_number.desc(), Chapter.updated_at.desc(), Chapter.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()

async def _clear_project_volumes(db: AsyncSession, project_id: str) -> None:
    old_volumes = (await db.execute(select(Volume).where(Volume.project_id == project_id))).scalars().all()
    for volume in old_volumes:
        old_chapters = (await db.execute(select(Chapter).where(Chapter.volume_id == volume.id))).scalars().all()
        for chapter in old_chapters:
            await db.delete(chapter)
        await db.delete(volume)
    await db.flush()

def _normalize_narrative_line(value: str | None) -> str:
    text = str(value or "").strip()
    mapping = {
        "主线": "main",
        "主线推进": "main",
        "main": "main",
        "副线A": "subplot_a",
        "副线a": "subplot_a",
        "支线A": "subplot_a",
        "支线a": "subplot_a",
        "subplot_a": "subplot_a",
        "副线B": "subplot_b",
        "副线b": "subplot_b",
        "支线B": "subplot_b",
        "支线b": "subplot_b",
        "subplot_b": "subplot_b",
    }
    return mapping.get(text, "main")

def _flatten_world_values(value, prefix: str = "") -> list[str]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, str):
        return [f"{prefix}{value}" if prefix else value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_flatten_world_values(item, prefix))
        return result
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            result.extend(_flatten_world_values(item, f"{prefix}{key}："))
        return result
    return [f"{prefix}{value}" if prefix else str(value)]

def _world_rule_audit_payload(world: WorldSetting | None, project: Project | None = None) -> dict:
    if not world:
        return {
            "score": 0,
            "passed": False,
            "conflicts": [],
            "gaps": ["尚未生成世界观规则"],
            "risks": ["缺少 hard_rules / world_logic / constraints，后续生成容易临时加万能设定"],
            "recommendations": ["先生成世界观，再进行章节写作"],
        }
    hard_rules = world.hard_rules or []
    constraints = world.constraints or []
    tone_rules = world.tone_rules or []
    logic_items = _flatten_world_values(world.world_logic or {})
    special_items = _flatten_world_values(world.special_rules or {})
    conflicts: list[dict] = []
    gaps: list[str] = []
    risks: list[str] = []

    if len(hard_rules) < 4:
        gaps.append("hard_rules 少于4条，世界硬约束不足")
    if len(constraints) < 3:
        gaps.append("constraints 少于3条，生成边界不足")
    if not logic_items:
        gaps.append("world_logic 为空，缺少世界运行逻辑")
    if project and project.core_theme and not any(project.core_theme in item for item in hard_rules + constraints + logic_items):
        risks.append("世界规则未显式绑定项目核心主题，后续可能偏题")

    combined = [(str(x), "hard_rules") for x in hard_rules] + [(str(x), "constraints") for x in constraints] + [(str(x), "world_logic") for x in logic_items] + [(str(x), "special_rules") for x in special_items]
    contradiction_pairs = [("不能", "可以"), ("禁止", "允许"), ("不可", "可"), ("必须", "随意"), ("唯一", "多个"), ("无法", "能够")]
    for idx, (text_a, source_a) in enumerate(combined):
        for text_b, source_b in combined[idx + 1:]:
            shared_tokens = [token for token in re.split(r"[，。；、\s：:]+", text_a) if len(token) >= 3 and token in text_b]
            if not shared_tokens:
                continue
            if any(a in text_a and b in text_b or b in text_a and a in text_b for a, b in contradiction_pairs):
                conflicts.append({
                    "source_a": source_a,
                    "text_a": _clip_text(text_a, 180),
                    "source_b": source_b,
                    "text_b": _clip_text(text_b, 180),
                    "shared": shared_tokens[:3],
                    "risk": "可能存在规则表述互相冲突",
                })

    if not any("代价" in str(x) or "成本" in str(x) for x in hard_rules + constraints + logic_items):
        risks.append("缺少能力/资源/制度代价规则，容易出现无成本开挂")
    if not any("信息" in str(x) or "秘密" in str(x) or "知道" in str(x) for x in hard_rules + constraints + logic_items):
        risks.append("缺少信息边界规则，角色可能知道不该知道的事")
    if not any("组织" in str(x) or "势力" in str(x) or "制度" in str(x) or "流程" in str(x) for x in hard_rules + constraints + logic_items):
        risks.append("缺少组织/制度执行规则，势力可能沦为背景名词")

    issue_count = len(conflicts) + len(gaps) + len(risks)
    score = max(0, 100 - len(conflicts) * 18 - len(gaps) * 10 - len(risks) * 6)
    return {
        "score": score,
        "passed": score >= 75 and not conflicts,
        "conflicts": conflicts[:20],
        "gaps": gaps,
        "risks": risks,
        "issue_count": issue_count,
        "recommendations": [
            "把世界规则改成可执行限制：谁受限、在哪种场景受限、违反有什么代价",
            "每条强能力/强资源都补一个成本、冷却、权限或信息边界",
            "组织规则要能制造具体阻力：流程、审批、外围成员、处罚、交换代价",
        ],
        "coverage": {
            "hard_rules": len(hard_rules),
            "constraints": len(constraints),
            "tone_rules": len(tone_rules),
            "world_logic_items": len(logic_items),
            "special_rule_items": len(special_items),
        },
    }

def _parse_state_snapshot(snapshot: str) -> dict:
    if not snapshot:
        return {}
    try:
        data = json.loads(snapshot)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

async def _delete_chapters_with_related(db: AsyncSession, project_id: str, chapters: list[Chapter]) -> int:
    if not chapters:
        return 0
    chapter_ids = [str(ch.id) for ch in chapters]
    versions = (await db.execute(
        select(ChapterVersion).where(ChapterVersion.project_id == project_id, ChapterVersion.chapter_id.in_(chapter_ids))
    )).scalars().all()
    for version in versions:
        await db.delete(version)
    timeline_events = (await db.execute(
        select(TimelineEvent).where(TimelineEvent.project_id == project_id, TimelineEvent.chapter_id.in_(chapter_ids))
    )).scalars().all()
    for event in timeline_events:
        await db.delete(event)
    state_trails = (await db.execute(
        select(StoryStateTrail).where(StoryStateTrail.project_id == project_id, StoryStateTrail.chapter_id.in_(chapter_ids))
    )).scalars().all()
    for trail in state_trails:
        await db.delete(trail)
    for chapter in chapters:
        await db.delete(chapter)
    await db.flush()
    return len(chapters)

async def _clear_volume_chapters(db: AsyncSession, project_id: str, volume_id: str) -> int:
    chapters = (await db.execute(
        select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id)
    )).scalars().all()
    return await _delete_chapters_with_related(db, project_id, chapters)


__all__ = [name for name in globals() if not name.startswith('__')]
