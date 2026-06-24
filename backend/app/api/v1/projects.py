import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db, async_session
from app.models.user import User
from app.models.project import Project
from app.models.project_plan_session import ProjectPlanSession
from app.models.writing_style_skill import WritingStyleSkill
from app.api.deps import get_current_user
from app.services.ai_service import AIService
from app.services.task_manager import start_task, get_task
from app.utils.timezone import isoformat as tz_isoformat

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    genre: str = ""
    target_total_words: int | None = None
    story_suggestion: str = ""
    interests: str = ""
    style_skill_id: str | None = None


class ProjectPlanChatRequest(BaseModel):
    messages: list[dict]
    genres: str = ""
    style_preferences: str = ""
    current_draft: dict = {}
    intent: str = "chat"
    style_skill_id: str | None = None


class ProjectPlanSessionRequest(BaseModel):
    messages: list[dict] = []
    selected_genres: list[str] = []
    chat_input: str = ""
    current_draft: dict = {}
    suggestions: list[dict] = []
    selected_suggestion_index: int = 0
    next_questions: list[str] = []
    detail_options: list[str] = []
    rejected_entries: list[dict] = []


class RejectSuggestionRequest(BaseModel):
    suggestion_index: int | None = None
    suggestion: dict | None = None
    reason: str = ""


class UpdateProjectRequest(BaseModel):
    title: str | None = None
    genre: str | None = None
    target_total_words: int | None = None
    story_brief: str | None = None
    core_theme: str | None = None
    secondary_themes: list[str] | None = None
    motifs: list[dict] | None = None
    narrative_lines: list[dict] | None = None
    writing_style: dict | None = None
    wizard_step: int | None = None
    status: str | None = None


async def _get_or_create_plan_session(db: AsyncSession, user_id: str) -> ProjectPlanSession:
    session = (await db.execute(select(ProjectPlanSession).where(ProjectPlanSession.user_id == user_id))).scalar_one_or_none()
    if session:
        return session
    session = ProjectPlanSession(user_id=user_id)
    db.add(session)
    await db.flush()
    return session


def _session_payload(session: ProjectPlanSession | None) -> dict | None:
    if not session:
        return None
    updated_at = session.updated_at
    return {
        "messages": session.messages or [],
        "selected_genres": session.selected_genres or [],
        "chat_input": session.chat_input or "",
        "current_draft": session.current_draft or {},
        "suggestions": session.suggestions or [],
        "selected_suggestion_index": session.selected_suggestion_index or 0,
        "next_questions": session.next_questions or [],
        "detail_options": session.detail_options or [],
        "rejected_entries": session.rejected_entries or [],
        "updated_at": tz_isoformat(updated_at) or None,
    }


async def _save_plan_session(user_id: str, body: ProjectPlanSessionRequest) -> dict:
    async with async_session() as db:
        session = await _get_or_create_plan_session(db, user_id)
        session.messages = body.messages[-60:]
        session.selected_genres = body.selected_genres[:12]
        session.chat_input = body.chat_input
        session.current_draft = body.current_draft or {}
        session.suggestions = (body.suggestions or [])[:6]
        session.selected_suggestion_index = max(0, body.selected_suggestion_index or 0)
        session.next_questions = (body.next_questions or [])[:3]
        session.detail_options = (body.detail_options or [])[:5]
        if body.rejected_entries:
            session.rejected_entries = body.rejected_entries[-20:]
        payload = _session_payload(session) or {}
        await db.commit()
        return payload


def _clip_style_text(value, limit: int = 700) -> str:
    text = value if isinstance(value, str) else str(value or "")
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "..."


def _format_creation_style_skill(skill: WritingStyleSkill | None) -> str:
    if not skill:
        return ""
    profile = skill.style_profile or {}
    parts = [
        f"当前选中的共享写作风格 Skill：{skill.name}",
        f"核心写法：{_clip_style_text(profile.get('core_style') or skill.description, 500)}",
    ]
    if profile.get("creation_guidance"):
        parts.append(f"创建阶段指导：{_clip_style_text(profile.get('creation_guidance'), 900)}")
    if profile.get("outline_guidance"):
        parts.append(f"长线规划倾向：{_clip_style_text(profile.get('outline_guidance'), 700)}")
    for key, label in [
        ("characterization_style", "人物刻画"),
        ("emotion_style", "情绪感情"),
        ("relationship_style", "人物关系"),
        ("worldbuilding_style", "世界观揭示"),
        ("conflict_style", "冲突设计"),
        ("reader_payoff_style", "读者反馈"),
        ("language_style", "语言手感"),
        ("prose_craft_style", "文笔工艺"),
        ("detail_craft_style", "细节工艺"),
        ("character_entrance_style", "人物出场"),
        ("emotion_landing_style", "情绪落点"),
        ("scene_reality_style", "场景真实感"),
    ]:
        section = profile.get(key)
        if isinstance(section, dict):
            summary = section.get("summary") or ""
            rules = (
                section.get("rules")
                or section.get("techniques")
                or section.get("rhythm_rules")
                or section.get("detail_sources")
                or section.get("entrance_methods")
                or section.get("physical_reactions")
                or section.get("practical_obstacles")
                or []
            )
            detail = "；".join([summary, *[str(x) for x in rules[:3]]]).strip("；")
            if detail:
                parts.append(f"{label}：{_clip_style_text(detail, 420)}")
    recipe = profile.get("chapter_production_recipe")
    if isinstance(recipe, dict):
        recipe_text = []
        for key, label in [("opening", "开场"), ("conflict", "冲突"), ("emotion", "情绪"), ("ending", "结尾")]:
            value = recipe.get(key)
            if isinstance(value, list) and value:
                recipe_text.append(f"{label}：" + "；".join(str(x) for x in value[:2]))
        if recipe_text:
            parts.append(f"章节生产法：{_clip_style_text('；'.join(recipe_text), 700)}")
    parts.append("使用边界：Skill 只指导写作方法和策划侧重点，不得复制来源样本的原句、桥段、人物名、地名、组织名和专有设定。用户当前故事核心优先级最高。")
    return "\n".join(parts)


async def _load_user_style_skill(db: AsyncSession, user_id: str, skill_id: str | None) -> WritingStyleSkill | None:
    if not skill_id:
        return None
    return (await db.execute(
        select(WritingStyleSkill).where(WritingStyleSkill.id == skill_id, WritingStyleSkill.user_id == user_id, WritingStyleSkill.is_active == True)
    )).scalar_one_or_none()


def _draft_lookup(draft: dict | None, path: list[str]) -> str:
    cur = draft or {}
    for key in path:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(key)
        if cur is None:
            return ""
    return str(cur).strip() if not isinstance(cur, (list, dict)) else json.dumps(cur, ensure_ascii=False)


def _detect_direction_drift(prev_draft: dict | None, new_draft: dict | None) -> list[str]:
    """对比上一轮和本轮 project_draft 的核心方向字段；命中变化时返回可读的变动列表。"""
    if not isinstance(prev_draft, dict) or not isinstance(new_draft, dict):
        return []
    watched = [
        ("title", ["title"]),
        ("primary_subgenre", ["type_model", "primary_subgenre"]),
        ("core_engine", ["core_engine"]),
        ("protagonist_first_move", ["first_volume_engine", "protagonist_first_move"]),
    ]
    diffs: list[str] = []
    for label, path in watched:
        prev_val = _draft_lookup(prev_draft, path)
        new_val = _draft_lookup(new_draft, path)
        if prev_val and new_val and prev_val != new_val:
            diffs.append(f"{label}：{prev_val[:80]} → {new_val[:80]}")

    prev_locks = prev_draft.get("boundary_locks") or []
    new_locks = new_draft.get("boundary_locks") or []
    if isinstance(prev_locks, list) and isinstance(new_locks, list):
        removed = [str(x) for x in prev_locks if x not in new_locks]
        added = [str(x) for x in new_locks if x not in prev_locks]
        if removed:
            diffs.append("移除的 boundary_locks：" + "、".join(removed[:3]))
        if added:
            diffs.append("新增的 boundary_locks：" + "、".join(added[:3]))
    return diffs


def _prepend_drift_warning(assistant_reply: str, diffs: list[str]) -> str:
    if not diffs:
        return assistant_reply
    header = "【方向变动提醒】本轮 AI 调整了下列固定方向，如不打算改请告诉我：\n" + "\n".join(f"- {d}" for d in diffs)
    return f"{header}\n\n{assistant_reply}"


def _format_rejected_directions(rejected_entries: list[dict] | None) -> str:
    if not rejected_entries:
        return ""
    lines: list[str] = []
    for entry in rejected_entries[-10:]:
        if not isinstance(entry, dict):
            continue
        parts = []
        if entry.get("title"):
            parts.append(f"《{entry.get('title')}》")
        if entry.get("primary_subgenre"):
            parts.append(f"[{entry.get('primary_subgenre')}]")
        if entry.get("story_entry_type"):
            parts.append(f"入口={entry.get('story_entry_type')}")
        if entry.get("core_engine"):
            parts.append(f"引擎={entry.get('core_engine')[:80]}")
        if entry.get("reason"):
            parts.append(f"理由={entry.get('reason')[:60]}")
        if parts:
            lines.append("- " + " · ".join(parts))
    if not lines:
        return ""
    return "用户已经拒绝过下列方向，请避开类似入口、母题与冲突引擎：\n" + "\n".join(lines)


async def _do_plan_chat(user_id: str, messages: list[dict], genres: str, current_draft: dict, intent: str = "chat", style_skill_id: str | None = None, style_preferences: str = "") -> dict:
    if style_preferences:
        current_draft = {**(current_draft or {}), "user_tone_preferences": style_preferences}
        genres = f"{genres}\n总体风格偏好：{style_preferences}" if genres else f"总体风格偏好：{style_preferences}"
    style_guidance = ""
    async with async_session() as db:
        plan_session = (await db.execute(select(ProjectPlanSession).where(ProjectPlanSession.user_id == user_id))).scalar_one_or_none()
        rejected_entries = list(plan_session.rejected_entries or []) if plan_session else []
        if style_skill_id:
            style_guidance = _format_creation_style_skill(await _load_user_style_skill(db, user_id, style_skill_id))
    rejected_text = _format_rejected_directions(rejected_entries)
    if rejected_text:
        current_draft = {**(current_draft or {}), "_user_rejected_directions": rejected_text}
    if style_guidance:
        current_draft = {**(current_draft or {}), "writing_style_skill_guidance": style_guidance}
    ai = AIService()
    data = await ai.chat_project_plan(messages, genres, current_draft or {}, intent)
    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    draft = data.get("project_draft") or (suggestions[0] if suggestions else {})
    if intent == "generate" and len(suggestions) < 3:
        latest_user_message = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        fallback_inspiration = latest_user_message or draft.get("brief") or (current_draft or {}).get("brief") or ""
        if fallback_inspiration:
            extra = await ai.generate_story_suggestions(fallback_inspiration, genres, rejected_directions=rejected_text)
            seen_titles = {(s.get("title") or "").strip() for s in suggestions if isinstance(s, dict)}
            for item in extra:
                title = (item.get("title") or "").strip()
                if title and title not in seen_titles:
                    suggestions.append(item)
                    seen_titles.add(title)
                if len(suggestions) >= 6:
                    break
    if draft and isinstance(suggestions, list):
        draft_title = (draft.get("title") or "").strip()
        has_draft = any((s.get("title") or "").strip() == draft_title for s in suggestions if isinstance(s, dict))
        if intent == "generate" and not has_draft:
            suggestions = [draft, *suggestions]
        data["suggestions"] = suggestions[:6] if intent == "generate" else suggestions[:1]
        data["project_draft"] = draft
    assistant_reply = data.get("assistant_reply") or "我已经根据你的补充更新了项目草案。"
    drift = _detect_direction_drift(current_draft, draft if isinstance(draft, dict) else None)
    if drift:
        assistant_reply = _prepend_drift_warning(assistant_reply, drift)
        data["assistant_reply"] = assistant_reply
        data["direction_drift"] = drift
    persisted_messages = [*messages, {"role": "assistant", "content": assistant_reply}]
    await _save_plan_session(user_id, ProjectPlanSessionRequest(
        messages=persisted_messages,
        selected_genres=[g for g in genres.split(",") if g],
        chat_input="",
        current_draft=data.get("project_draft") or {},
        suggestions=data.get("suggestions") or [],
        selected_suggestion_index=0,
        next_questions=data.get("next_questions") if isinstance(data.get("next_questions"), list) else [],
        detail_options=data.get("detail_options") if isinstance(data.get("detail_options"), list) else [],
    ))
    return data


@router.post("/plan-chat")
async def plan_chat(body: ProjectPlanChatRequest, user: User = Depends(get_current_user)):
    task_id = start_task(_do_plan_chat(user.id, body.messages, body.genres, body.current_draft, body.intent, body.style_skill_id, body.style_preferences), "project_plan_chat")
    return {"task_id": task_id}


@router.get("/plan-session")
async def get_plan_session(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    session = (await db.execute(select(ProjectPlanSession).where(ProjectPlanSession.user_id == user.id))).scalar_one_or_none()
    return {"session": _session_payload(session)}


@router.put("/plan-session")
async def save_plan_session(body: ProjectPlanSessionRequest, user: User = Depends(get_current_user)):
    session = await _save_plan_session(user.id, body)
    return {"session": session}


@router.delete("/plan-session")
async def clear_plan_session(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    session = (await db.execute(select(ProjectPlanSession).where(ProjectPlanSession.user_id == user.id))).scalar_one_or_none()
    if session:
        await db.delete(session)
    return {"success": True}


@router.post("/plan-session/reject")
async def reject_plan_suggestion(body: RejectSuggestionRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    session = await _get_or_create_plan_session(db, user.id)
    suggestion = body.suggestion
    if suggestion is None and body.suggestion_index is not None:
        suggestions = session.suggestions or []
        if 0 <= body.suggestion_index < len(suggestions):
            suggestion = suggestions[body.suggestion_index]
    if not isinstance(suggestion, dict):
        raise HTTPException(400, "请提供 suggestion_index 或 suggestion 对象")

    type_model = suggestion.get("type_model") or {}
    entry = {
        "title": (suggestion.get("title") or "").strip()[:60],
        "story_entry_type": (suggestion.get("story_entry_type") or "").strip()[:40],
        "primary_subgenre": (type_model.get("primary_subgenre") or type_model.get("primary_genre") or "").strip()[:40],
        "core_engine": (suggestion.get("core_engine") or "").strip()[:200],
        "reason": (body.reason or "").strip()[:200],
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    }
    existing = list(session.rejected_entries or [])
    existing.append(entry)
    session.rejected_entries = existing[-20:]
    await db.commit()
    return {"session": _session_payload(session)}


@router.get("/plan-task/{task_id}")
async def poll_plan_task(task_id: str, user: User = Depends(get_current_user)):
    task = get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return {"status": task["status"], "result": task.get("result"), "error": task.get("error")}


@router.get("")
async def list_projects(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.user_id == user.id).order_by(Project.updated_at.desc())
    )
    return {"projects": result.scalars().all()}


@router.post("")
async def create_project(
    body: CreateProjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.style_skill_id:
        skill = await _load_user_style_skill(db, user.id, body.style_skill_id)
        if not skill:
            raise HTTPException(404, "写作风格 Skill 不存在")
    project = Project(
        user_id=user.id,
        genre=body.genre,
        target_total_words=body.target_total_words or 300000,
        story_brief=body.story_suggestion,
        writing_style={"active_style_skill_id": body.style_skill_id} if body.style_skill_id else {},
    )
    db.add(project)
    await db.flush()
    return {"project_id": str(project.id), "project": project}


@router.get("/{project_id}")
async def get_project(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    return {"project": project}


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    await db.flush()
    return {"project": project}


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    await db.delete(project)
    return {"success": True}
