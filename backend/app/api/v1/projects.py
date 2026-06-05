from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db, async_session
from app.models.user import User
from app.models.project import Project
from app.models.project_plan_session import ProjectPlanSession
from app.api.deps import get_current_user
from app.services.ai_service import AIService
from app.services.task_manager import start_task, get_task

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    genre: str = ""
    target_total_words: int | None = None
    story_suggestion: str = ""
    interests: str = ""


class ProjectPlanChatRequest(BaseModel):
    messages: list[dict]
    genres: str = ""
    current_draft: dict = {}
    intent: str = "chat"


class ProjectPlanSessionRequest(BaseModel):
    messages: list[dict] = []
    selected_genres: list[str] = []
    chat_input: str = ""
    current_draft: dict = {}
    suggestions: list[dict] = []
    selected_suggestion_index: int = 0
    next_questions: list[str] = []
    detail_options: list[str] = []


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
        "updated_at": updated_at.isoformat() if updated_at else None,
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
        payload = _session_payload(session) or {}
        await db.commit()
        return payload


async def _do_plan_chat(user_id: str, messages: list[dict], genres: str, current_draft: dict, intent: str = "chat") -> dict:
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
            extra = await ai.generate_story_suggestions(fallback_inspiration, genres)
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
    task_id = start_task(_do_plan_chat(user.id, body.messages, body.genres, body.current_draft, body.intent), "project_plan_chat")
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
    project = Project(
        user_id=user.id,
        genre=body.genre,
        target_total_words=body.target_total_words or 300000,
        story_brief=body.story_suggestion,
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
