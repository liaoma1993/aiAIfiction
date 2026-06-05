from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
import asyncio
import io
import json
import re
import uuid
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
from app.api.deps import get_current_user
from app.services.ai_service import AIService, SYSTEM_EDITOR
from app.services.task_manager import start_task, get_task_persisted, list_tasks_persisted, update_progress, cancel_task, is_cancelled
from app.services.story_bible import build_story_bible
from app.services.context_builder import build_generation_context

router = APIRouter(prefix="/projects/{project_id}/wizard", tags=["wizard"])
BATCH_WRITE_ARC_TIMEOUT_SECONDS = 5 * 60 * 60
_outline_write_locks: dict[str, asyncio.Lock] = {}

DEFAULT_WRITING_CONTROLS = {
    "readability_mode": "easy",
    "pace_mode": "standard",
    "dialogue_density": "medium",
    "description_density": "standard",
    "humor_level": "light",
    "information_density": "medium",
    "punctuation_style": "standard",
    "chapter_template": "standard",
    "early_grip_mode": "auto",
    "auto_quality_check": True,
    "auto_light_fix": True,
}


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


class StorySuggestRequest(BaseModel):
    inspiration: str
    genres: str = ""


class ProjectPlanChatRequest(BaseModel):
    messages: list[dict]
    genres: str = ""
    current_draft: dict = {}


class WriteChapterRequest(BaseModel):
    mode: str = "append"
    instruction: str = ""
    controls: dict = {}
    preview: bool = False


class ReviseChapterRequest(BaseModel):
    mode: str = "polish"
    instruction: str = ""
    selection: str = ""
    controls: dict = {}
    apply: bool = False


LOCAL_REVISE_MODES = {"target_sentence_fix", "target_paragraph_fix", "target_context_fix"}


class RepairFromReviewRequest(BaseModel):
    review_result: dict
    review_scope: str = ""
    apply: bool = True
    reaudit: bool = False
    resume_chapters: list[int] = []


class SplitChapterRequest(BaseModel):
    target_words: int = 3500
    apply: bool = True


class ExportManuscriptRequest(BaseModel):
    scope: str = "volume"  # volume / arc
    volume_id: str
    arc_name: str = ""
    format: str = "md"  # md / txt / json
    include_empty: bool = False


class AdjustOutlineRequest(BaseModel):
    instruction: str
    arc_index: int | None = None
    apply: bool = True
    adjust_scope: str = "outline"  # outline / summary_only


class AdjustOutlineChatRequest(BaseModel):
    messages: list[dict]
    arc_index: int | None = None
    adjust_scope: str = "outline"  # outline / summary_only


class ApplyDraftRequest(BaseModel):
    draft_type: str
    payload: dict


class ApplyStateRequest(BaseModel):
    payload: dict


async def _do_suggest_stories(project_id: str, inspiration: str, genres: str) -> dict:
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "story_brief": project.story_brief,
            "core_theme": project.core_theme,
        }
    ai = AIService()
    suggestions = await ai.generate_story_suggestions(inspiration, genres)
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        project.title = suggestions[0].get("title", snapshot["title"]) if suggestions else snapshot["title"]
        project.story_brief = suggestions[0].get("brief", snapshot["story_brief"]) if suggestions else snapshot["story_brief"]
        project.genre = suggestions[0].get("genre", snapshot["genre"]) if suggestions else snapshot["genre"]
        project.target_total_words = suggestions[0].get("total_words", project.target_total_words) if suggestions else project.target_total_words
        project.writing_style = {"tags": suggestions[0].get("tags", [])} if suggestions else project.writing_style
        await db.commit()
        return {"suggestions": suggestions}


@router.post("/suggest-stories")
async def suggest_stories(project_id: str, body: StorySuggestRequest, user: User = Depends(get_current_user)):
    task_id = start_task(_do_suggest_stories(project_id, body.inspiration, body.genres))
    return {"task_id": task_id}


async def _do_project_plan_chat(project_id: str, messages: list[dict], genres: str, current_draft: dict) -> dict:
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        project_draft = {
            "title": project.title,
            "genre": project.genre,
            "brief": project.story_brief,
            "tags": (project.writing_style or {}).get("tags", []) if isinstance(project.writing_style, dict) else [],
            "total_words": project.target_total_words,
        }
    merged_draft = {**project_draft, **(current_draft or {})}
    ai = AIService()
    data = await ai.chat_project_plan(messages, genres, merged_draft)
    suggestions = data.get("suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    draft = data.get("project_draft") or (suggestions[0] if suggestions else {})
    if len(suggestions) < 3:
        latest_user_message = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        fallback_inspiration = latest_user_message or draft.get("brief") or merged_draft.get("brief") or ""
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
        if not has_draft:
            suggestions = [draft, *suggestions]
        data["suggestions"] = suggestions[:6]
        data["project_draft"] = draft
    if draft:
        async with async_session() as db:
            project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
            if project:
                project.title = draft.get("title") or project.title
                project.genre = draft.get("genre") or project.genre
                project.story_brief = draft.get("brief") or project.story_brief
                project.target_total_words = draft.get("total_words") or project.target_total_words
                tags = draft.get("tags")
                if isinstance(tags, list):
                    style = project.writing_style or {}
                    if not isinstance(style, dict):
                        style = {}
                    style["tags"] = tags
                    project.writing_style = style
                await db.commit()
    return data


@router.post("/project-plan-chat")
async def project_plan_chat(project_id: str, body: ProjectPlanChatRequest, user: User = Depends(get_current_user)):
    task_id = start_task(_do_project_plan_chat(project_id, body.messages, body.genres, body.current_draft), "project_plan_chat", project_id)
    return {"task_id": task_id}


class ApplyStoryRequest(BaseModel):
    title: str
    genre: str = ""
    brief: str = ""
    tags: list[str] = []
    total_words: int = 300000
    planning_messages: list[dict] = []
    planning_suggestions: list[dict] = []
    selected_draft: dict = {}


def _clip_planning_text(text: str | None, limit: int = 1000) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "..."


def _as_string_list(value, limit: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items


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


def _format_wizard_planning_memory(project: Project, limit: int = 2400) -> str:
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
        if selected.get("reader_promise"):
            parts.append(f"读者承诺：{selected.get('reader_promise')}")
        if selected.get("core_engine"):
            parts.append(f"核心引擎：{selected.get('core_engine')}")
        boundary_locks = selected.get("boundary_locks") or []
        if boundary_locks:
            parts.append("边界锁定：" + "；".join(str(x) for x in boundary_locks[:8]))
        if selected.get("brief"):
            parts.append(f"草案：{_clip_planning_text(selected.get('brief'), 900)}")
        long_term_plan = selected.get("long_term_plan") or {}
        if isinstance(long_term_plan, dict) and long_term_plan:
            if long_term_plan.get("endgame"):
                parts.append(f"终局指向：{_clip_planning_text(long_term_plan.get('endgame'), 400)}")
            stage_plan = long_term_plan.get("stage_plan") or []
            if stage_plan:
                parts.append("长线阶段：" + "；".join(_clip_planning_text(str(x), 260) for x in stage_plan[:6]))
            payoffs = long_term_plan.get("foreshadowing_payoffs") or []
            if payoffs:
                parts.append("伏笔回收：" + "；".join(_clip_planning_text(str(x), 180) for x in payoffs[:6]))
        tags = selected.get("tags") or []
        if tags:
            parts.append("风格标签：" + "、".join(str(x) for x in tags[:10]))
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
    memory = style.get("wizard_planning_memory") if isinstance(style, dict) else {}
    selected = memory.get("selected_draft") if isinstance(memory, dict) else {}
    if not isinstance(selected, dict):
        selected = {}
    boundary_locks = _as_string_list(selected.get("boundary_locks"), 8)
    tags = _as_string_list(selected.get("tags"), 8)
    hard_rules = []
    if selected.get("core_engine"):
        hard_rules.append(f"核心引擎不能偏离：{selected.get('core_engine')}")
    hard_rules.extend(boundary_locks)
    tone_rules = []
    if tags:
        tone_rules.append("文风标签必须保持：" + "、".join(tags))
    if selected.get("reader_promise"):
        tone_rules.append(f"读者承诺必须体现在章节体验里：{selected.get('reader_promise')}")
    constraints = []
    if selected.get("length_type"):
        constraints.append(f"篇幅规划按{selected.get('length_type')}处理，不能用短篇节奏写长线，也不能把短篇强行注水成长篇。")
    long_term_plan = selected.get("long_term_plan") or {}
    if isinstance(long_term_plan, dict) and long_term_plan.get("endgame"):
        constraints.append(f"后续发展不能偏离终局指向：{long_term_plan.get('endgame')}")
    return {
        "hard_rules": hard_rules[:10],
        "tone_rules": tone_rules[:8],
        "constraints": constraints[:8],
    }


def _wizard_story_brief(project: Project, limit: int = 5000) -> str:
    planning = _format_wizard_planning_memory(project, 3200)
    brief = project.story_brief or ""
    return _clip_planning_text(f"{brief}\n\n{planning}" if planning else brief, limit)


def _readability_guidance(controls: dict | None) -> str:
    controls = controls or {}
    mode = controls.get("readability_mode") or controls.get("clarity_mode") or "easy"
    guidance = {
        "simple": """
模式：简单直白。
- 每一段只推进一个动作、一个发现或一次对话，不要多线并写。
- 少用隐喻、象征、跳跃式心理描写和复杂倒叙。
- 重要信息要在角色行动或对话后立刻给出结果，让读者不用回看也能明白。
- 句子偏短，段落偏短，因果关系直接写清楚：谁做了什么，为什么，造成什么后果。
- 悬念可以保留，但不能靠故意省略关键信息制造难懂。
- 不写“意象映射”“信念地基”“时代洪流”这类抽象表达，改写成具体人和具体事。
- 开场 300 字内必须出现可见事件或麻烦，不能先抒情、先介绍背景。
""",
        "easy": """
模式：通俗易懂。
- 保留类型小说爽点和现场感，但优先让读者一遍读懂。
- 每个场景先锚定地点、人物、目标，再写冲突，不要一上来堆设定名词。
- 复杂设定拆成小块，通过动作和对话逐步露出；每次只解释当前剧情必需的一点。
- 转折前后写清因果：上一件事怎样逼出下一件事。
- 对话可以有潜台词，但关键剧情信息不要藏得太深。
- 写法按连载网文处理：短目标、强阻力、快反馈、章末具体钩子。
- 环境描写点到为止，不能连续铺陈光影、气味、象征和心理映射。
- 主角每章要有可见动作，哪怕是试探、装傻、递报告、顶一句、查一份文件。
""",
        "normal": """
模式：正常连载。
- 清晰度与文学质感平衡，允许一定潜台词和伏笔，但主线因果必须明确。
- 场景、动作、对话、心理交替推进，不要长篇解释，也不要故意写得晦涩。
- 读者可以思考伏笔，但不应该因为表达绕而看不懂当前发生了什么。
""",
        "dense": """
模式：细腻烧脑。
- 可以提高信息密度、伏笔密度和心理层次，但必须保证场景动作线清楚。
- 允许非直白表达和多重含义，但每个关键转折仍要有可追溯因果。
- 不要为了复杂而复杂；复杂来自角色动机、信息差和代价，不来自绕句子。
""",
    }
    return guidance.get(mode, guidance["easy"]).strip()


def _project_writing_controls(project: Project | None) -> dict:
    style = project.writing_style if project else {}
    if not isinstance(style, dict):
        style = {}
    saved = style.get("writing_controls") or {}
    if not isinstance(saved, dict):
        saved = {}
    return {**DEFAULT_WRITING_CONTROLS, **saved}


def _merge_writing_controls(project: Project | None, controls: dict | None) -> dict:
    merged = _project_writing_controls(project)
    if isinstance(controls, dict):
        merged.update({k: v for k, v in controls.items() if v is not None and v != ""})
    return merged


def _writing_controls_guidance(controls: dict | None) -> str:
    controls = controls or {}
    pace = {
        "slow": "节奏偏慢，允许更多生活细节和情绪铺垫，但每段仍要有叙事功能。",
        "standard": "节奏标准，场景推进、人物反应、信息揭示保持均衡。",
        "fast": "节奏偏快，减少绕路解释，冲突和结果更快落地。",
        "爽文快推": "爽文快推，压迫、反转、反馈要明确，读者获得感优先。",
    }.get(str(controls.get("pace_mode", "standard")), "节奏标准，场景推进、人物反应、信息揭示保持均衡。")
    dialogue = {
        "low": "对白比例较低，用动作和场景推进，关键对白短而有力。",
        "medium": "对白比例中等，对话服务冲突和人物关系。",
        "high": "对白比例较高，用对话推动冲突、误会、吐槽和信息交换，但不能变成问答说明书。",
    }.get(str(controls.get("dialogue_density", "medium")), "对白比例中等，对话服务冲突和人物关系。")
    description = {
        "light": "描写密度偏轻，少写静态景物，多写动作中的细节。",
        "standard": "描写密度标准，每个重要场景至少有声音、光线、气味、温度或触感中的一项。",
        "rich": "描写更细腻，但不能牺牲可读性，不要堆形容词。",
    }.get(str(controls.get("description_density", "standard")), "描写密度标准，每个重要场景至少有感官锚点。")
    humor = {
        "none": "不主动制造幽默，保持剧情气质。",
        "light": "轻微幽默，用角色反应、吐槽或尴尬细节调味，不破坏剧情。",
        "medium": "中等幽默，允许更多吐槽、反差和社死反馈，但主线仍要推进。",
        "strong": "强幽默，冲突解决和人物互动要有明显笑点，但不能让人物降智。",
    }.get(str(controls.get("humor_level", "light")), "轻微幽默，用角色反应、吐槽或尴尬细节调味。")
    info = {
        "low": "信息密度低，复杂设定必须拆开，一章只解释当前必要的信息。",
        "medium": "信息密度中等，设定、伏笔、动作交替出现。",
        "high": "信息密度高，但每个新信息都必须有上下文和后果，不能堆名词。",
    }.get(str(controls.get("information_density", "medium")), "信息密度中等，设定、伏笔、动作交替出现。")
    template = {
        "standard": "章节结构：开场承接 -> 当前目标 -> 冲突推进 -> 新信息/代价 -> 章末钩子。",
        "爽点章": "章节结构：压迫/误判 -> 主角行动 -> 反转反馈 -> 余波 -> 新威胁。",
        "搞笑章": "章节结构：正常目标 -> 意外变量 -> 社死/误会升级 -> 反向解决 -> 围观后果。",
        "悬疑章": "章节结构：异常细节 -> 错误解释 -> 新证据 -> 推翻判断 -> 更大疑点。",
        "感情章": "章节结构：表面冲突 -> 误会或试探 -> 细节泄露真心 -> 靠近/退缩 -> 情绪钩子。",
        "战斗章": "章节结构：目标 -> 地形/限制 -> 试探 -> 代价 -> 破局 -> 余波。",
        "日常过渡章": "章节结构：生活场景 -> 关系推进 -> 小伏笔 -> 主线轻推 -> 温和钩子。",
    }.get(str(controls.get("chapter_template", "standard")), "章节结构：开场承接 -> 当前目标 -> 冲突推进 -> 新信息/代价 -> 章末钩子。")
    return "\n".join([pace, dialogue, description, humor, info, template])


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


def _early_grip_guidance(project: Project | None, chapter: Chapter | None, volume: Volume | None, controls: dict | None) -> str:
    controls = controls or {}
    if str(controls.get("early_grip_mode", "auto")) == "off":
        return "已关闭前20万字强追读模式，按常规章节质量要求写作。"
    target_words = int(controls.get("target_words") or getattr(chapter, "target_words", None) or getattr(volume, "default_chapter_words", None) or 3500)
    chapter_number = int(getattr(chapter, "chapter_number", 1) or 1)
    estimated_position = chapter_number * max(target_words, 1000)
    target_total = int(getattr(project, "target_total_words", 0) or 0)
    is_long_form = target_total >= 300000 or str(getattr(project, "target_length", "")).lower() in {"long", "very_long", "超长篇", "长篇"}
    if estimated_position > 200000 and str(controls.get("early_grip_mode", "auto")) != "force":
        return "当前章节估算已超过前20万字，保持追读钩子，但允许更多长期铺垫和情绪沉淀。"

    form_note = "这是长篇连载的前20万字，必须优先让读者愿意追下去。" if is_long_form else "这是故事早期章节，必须快速建立可读性和期待感。"
    return f"""
{form_note}
硬要求：
- 第一屏必须有可见事件、异常结果、具体麻烦或强人物动作，不能以设定说明、背景总结、空泛心理开场。
- 本章要有清晰短目标：主角这一章想解决什么、避开什么、证明什么或占到什么便宜。
- 必须给读者即时反馈：笑点/爽点/社死/反转/小胜/翻车/新能力试用至少出现一种，且要写出旁观者或现实后果。
- 每个设定信息都必须绑定现场用途：它让主角赚了、亏了、尴尬了、暴露了、被误会了，不能单独讲课。
- 主角要主动做选择，哪怕选择很怂、很损、很社死，也不能只被剧情推着走。
- 章末钩子要具体到声音、物件、弹窗、消息、动作、人物一句话或现场发现，让读者自然想翻下一章。
- 不要为了“高级感”把情节写得绕。前20万字优先易懂、好玩、有反馈、有连续期待。
- 章节不能只靠“看见制度问题/产生不安/理想摇晃”推进，必须落到具体麻烦：材料被退、会议被怼、项目出事、钱流异常、群众堵门、同事甩锅、上级试探。
- 每章结尾要让读者问“他接下来怎么破局”，而不是只留下“他心里很复杂”。
""".strip()


def _quality_needs_fix(review: dict | None) -> bool:
    if not isinstance(review, dict):
        return False
    if review.get("audit_error"):
        return False
    score = review.get("overall_score")
    try:
        if int(score or 0) < 8:
            return True
    except (TypeError, ValueError):
        pass
    for issue in review.get("issues") or []:
        if isinstance(issue, dict) and issue.get("severity") in {"critical", "high"}:
            return True
    return False


async def _review_and_light_fix_chapter(
    ai: AIService,
    project: Project,
    chapter: Chapter,
    content: str,
    previous_ending: str,
    story_state_snapshot: str,
    controls: dict,
) -> tuple[str, dict | None]:
    if not controls.get("auto_quality_check", True):
        return content, None
    review = await ai.audit_chapter(previous_ending, chapter.hook or "", story_state_snapshot, content)
    if controls.get("auto_light_fix", True) and _quality_needs_fix(review):
        result = await ai.revise_chapter(
            project.title,
            project.genre,
            chapter.chapter_number,
            chapter.title or "",
            chapter.summary or "",
            content,
            "quality_light_fix",
            instruction=(
                "根据质量审稿做轻量修正：优先修复难懂、标点、断句、AI味、对话不自然、上承下接不清。"
                "不得改变本章核心剧情、人物关系、关键信息和章末钩子。"
            ),
            selection="",
            previous_ending=previous_ending,
            controls=controls,
            repair_context=json.dumps(review or {}, ensure_ascii=False),
        )
        fixed = result.get("content") if isinstance(result, dict) else ""
        if fixed:
            content = fixed
            second_review = await ai.audit_chapter(previous_ending, chapter.hook or "", story_state_snapshot, content)
            if isinstance(second_review, dict):
                second_review["light_fix_applied"] = True
                second_review["before_fix"] = review
            review = second_review
    return content, review


def _volume_outline_needs_completion(outline: str | None) -> bool:
    text = (outline or "").strip()
    if len(text) < 300:
        return True
    placeholder_patterns = [
        "详细描述",
        "约1000字本卷大纲",
        "1000字本卷大纲",
        "待补充",
        "待完善",
        "略",
        "TODO",
    ]
    return any(pattern in text for pattern in placeholder_patterns)


@router.post("/apply-story")
async def apply_story(project_id: str, body: ApplyStoryRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    project.title = body.title
    project.genre = body.genre
    project.story_brief = body.brief
    project.target_total_words = body.total_words
    project.writing_style = {
        "tags": body.tags,
        "wizard_planning_memory": _build_wizard_planning_memory(
            body.planning_messages,
            body.selected_draft or {"title": body.title, "genre": body.genre, "brief": body.brief, "tags": body.tags, "total_words": body.total_words},
            body.planning_suggestions,
        ),
    }
    project.wizard_step = 1
    await db.flush()
    return {"project": project}


async def _do_generate_world(project_id: str) -> dict:
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        snapshot = {"title": project.title, "genre": project.genre, "story_brief": _wizard_story_brief(project), "core_theme": project.core_theme}
    ai = AIService()
    data = await ai.generate_world_setting(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"])
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        ws_result = await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))
        ws = ws_result.scalar_one_or_none()
        if not ws:
            ws = WorldSetting(project_id=project_id)
            db.add(ws)
        for key in ["geography", "social_structure", "power_system", "history", "culture", "special_rules", "world_logic"]:
            setattr(ws, key, data.get(key, {"content": ""}))
        defaults = _world_rule_defaults_from_project(project)
        for key in ["hard_rules", "tone_rules", "constraints"]:
            generated = _as_string_list(data.get(key), 12)
            setattr(ws, key, generated or defaults.get(key, []))
        project.wizard_step = max(project.wizard_step, 2)
        await db.commit()
        return {"success": True}


async def _do_generate_world_draft(project_id: str) -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        snapshot = {"title": project.title, "genre": project.genre, "story_brief": _wizard_story_brief(project), "core_theme": project.core_theme}
    ai = AIService()
    return await ai.generate_world_setting(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"])


@router.post("/generate-world")
async def generate_world(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_world(project_id), "generate_world", project_id)
    return {"task_id": task_id}


@router.post("/generate-world-draft")
async def generate_world_draft(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_world_draft(project_id), "generate_world_draft", project_id)
    return {"task_id": task_id}


class GenerateRequest(BaseModel):
    char_count: int = 6
    faction_count: int = 3


FACTION_FIELDS = {"name", "faction_type", "description", "headquarters", "territory", "core_creed", "hierarchy", "notable_members", "faction_timeline", "emblem_description", "color_scheme", "core_conflict_of_interest", "internal_faction_cracks", "reputation_and_reality", "strength_trajectory", "sort_order"}

CHARACTER_FIELDS = {"name", "role_type", "personality", "background", "motivation", "behavior_pattern", "language_style", "emotional_expression", "appearance", "faction_rank", "faction_history", "growth_arc", "inner_conflict", "language_fingerprint", "relationship_dynamics", "growth_arc_preset", "first_appeared_chapter", "first_appeared_title", "character_class"}
ROLE_TYPE_ALIASES = {
    "protagonist": "主角",
    "hero": "主角",
    "antagonist": "反派",
    "villain": "反派",
    "supporting": "配角",
    "sidekick": "配角",
    "mentor": "导师",
    "master": "导师",
    "love_interest": "恋人",
    "love interest": "恋人",
    "comic_relief": "搞笑担当",
    "other": "其他",
}

FACTION_TYPE_ALIASES = {
    "sect": "门派",
    "family": "家族",
    "empire": "帝国",
    "guild": "商会",
    "merchant_guild": "商会",
    "dark_org": "暗组织",
    "race": "种族",
    "tribe": "部落",
    "alliance": "联盟",
    "temple": "神殿",
    "academy": "学院",
    "court": "朝廷",
}


def _normalize_role_type(role_type: str | None) -> str:
    role = (role_type or "配角").strip()
    return ROLE_TYPE_ALIASES.get(role.lower(), ROLE_TYPE_ALIASES.get(role, role))


def _normalize_faction_type(faction_type: str | None) -> str:
    value = (faction_type or "组织").strip()
    return FACTION_TYPE_ALIASES.get(value.lower(), FACTION_TYPE_ALIASES.get(value, value))


def _normalize_entity_name(name: str | None) -> str:
    return re.sub(r"\s+", "", (name or "").strip()).lower()


def _merge_model_fields(model, data: dict, fields: set[str]):
    for field in fields:
        if field == "name" or field not in data:
            continue
        value = data.get(field)
        if value in (None, "", [], {}):
            continue
        setattr(model, field, value)


async def _upsert_character(db: AsyncSession, project_id: str, cdata: dict, existing_by_name: dict[str, Character]) -> Character | None:
    clean = {k: v for k, v in (cdata or {}).items() if k in CHARACTER_FIELDS}
    clean["role_type"] = _normalize_role_type(clean.get("role_type"))
    name = (clean.get("name") or "").strip()
    key = _normalize_entity_name(name)
    if not key:
        return None
    char = existing_by_name.get(key)
    if char:
        _merge_model_fields(char, clean, CHARACTER_FIELDS)
        return char
    char = Character(project_id=project_id, growth_stages=[], **clean)
    db.add(char)
    await db.flush()
    existing_by_name[key] = char
    return char


async def _upsert_faction(db: AsyncSession, project_id: str, fdata: dict, existing_by_name: dict[str, Faction]) -> Faction | None:
    clean = {k: v for k, v in (fdata or {}).items() if k in FACTION_FIELDS}
    clean["faction_type"] = _normalize_faction_type(clean.get("faction_type"))
    name = (clean.get("name") or "").strip()
    key = _normalize_entity_name(name)
    if not key:
        return None
    faction = existing_by_name.get(key)
    if faction:
        _merge_model_fields(faction, clean, FACTION_FIELDS)
        return faction
    faction = Faction(project_id=project_id, **clean)
    db.add(faction)
    await db.flush()
    existing_by_name[key] = faction
    return faction


async def _do_generate_characters(project_id: str, char_count: int, faction_count: int) -> dict:
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        snapshot = {"title": project.title, "genre": project.genre, "story_brief": _wizard_story_brief(project), "core_theme": project.core_theme}
        existing_characters = (await db.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
        existing_characters_summary = "\n".join([
            f"- {c.name}（{c.role_type}）：{_clip_text(getattr(c, 'growth_arc_preset', '') or getattr(c, 'growth_arc', '') or c.personality, 180)}"
            for c in existing_characters
        ]) or "无"
    ai = AIService()
    chars_data, facs_result = await asyncio.gather(
        ai.generate_characters(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], char_count, existing_characters_summary),
        ai.generate_factions(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], faction_count),
    )

    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        facs_data = facs_result.get("factions", []) if isinstance(facs_result, dict) else []
        cross_matrix = facs_result.get("cross_faction_matrix", []) if isinstance(facs_result, dict) else []

        existing_factions = (await db.execute(select(Faction).where(Faction.project_id == project_id))).scalars().all()
        existing_characters = (await db.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
        faction_by_name = {_normalize_entity_name(f.name): f for f in existing_factions if _normalize_entity_name(f.name)}
        character_by_name = {_normalize_entity_name(c.name): c for c in existing_characters if _normalize_entity_name(c.name)}

        faction_map = {}
        seen_faction_names = set()
        for fdata in facs_data:
            name = fdata.get("name", "")
            key = _normalize_entity_name(name)
            if not key or key in seen_faction_names:
                continue
            seen_faction_names.add(key)
            faction = await _upsert_faction(db, project_id, fdata, faction_by_name)
            if faction:
                faction_map[name] = faction

        for rel in cross_matrix:
            a_name = rel.get("faction_a", "")
            b_name = rel.get("faction_b", "")
            if a_name in faction_map and b_name in faction_map:
                db.add(FactionRelation(
                    project_id=project_id,
                    faction_a_id=faction_map[a_name].id,
                    faction_b_id=faction_map[b_name].id,
                    relation_type=rel.get("relationship", ""),
                    timeline_changes=[{"tension_level": rel.get("tension_level", 5), "volatility": rel.get("volatility", "中")}],
                ))

        seen_char_names = set()
        for cdata in chars_data:
            name = cdata.get("name", "")
            key = _normalize_entity_name(name)
            if not key or key in seen_char_names:
                continue
            seen_char_names.add(key)
            await _upsert_character(db, project_id, cdata, character_by_name)

        project.wizard_step = max(project.wizard_step, 3)
        await db.commit()
        return {"success": True}


async def _do_generate_characters_draft(project_id: str, char_count: int, faction_count: int) -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        snapshot = {"title": project.title, "genre": project.genre, "story_brief": _wizard_story_brief(project), "core_theme": project.core_theme}
        existing_characters = (await db.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
        existing_characters_summary = "\n".join([
            f"- {c.name}（{c.role_type}）：{_clip_text(getattr(c, 'growth_arc_preset', '') or getattr(c, 'growth_arc', '') or c.personality, 180)}"
            for c in existing_characters
        ]) or "无"
    ai = AIService()
    chars_data, facs_result = await asyncio.gather(
        ai.generate_characters(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], char_count, existing_characters_summary),
        ai.generate_factions(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], faction_count),
    )
    return {"characters": chars_data, "factions": facs_result.get("factions", []) if isinstance(facs_result, dict) else [], "cross_faction_matrix": facs_result.get("cross_faction_matrix", []) if isinstance(facs_result, dict) else []}


@router.post("/generate-characters")
async def generate_characters(project_id: str, body: GenerateRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_generate_characters(project_id, body.char_count, body.faction_count),
        "generate_characters",
        project_id,
        {"char_count": body.char_count, "faction_count": body.faction_count},
    )
    return {"task_id": task_id}


@router.post("/generate-characters-draft")
async def generate_characters_draft(project_id: str, body: GenerateRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_generate_characters_draft(project_id, body.char_count, body.faction_count),
        "generate_characters_draft",
        project_id,
        {"char_count": body.char_count, "faction_count": body.faction_count},
    )
    return {"task_id": task_id}


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
    if prev_snapshot:
        parts.append(f"上章快照：{prev_snapshot[:500]}")
    return "\n".join(parts) if parts else "无"


def _safe_json(value, fallback):
    if value is None:
        return fallback
    return value


def _clip_text(text, limit: int = 600) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= limit else text[:limit] + "..."


def _parse_state_snapshot(snapshot: str) -> dict:
    if not snapshot:
        return {}
    try:
        data = json.loads(snapshot)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _format_arc_bridge(prev_arc: dict, prev_chapters: list[Chapter], next_arc: dict | None = None) -> str:
    if not prev_chapters:
        return ""

    last = prev_chapters[-1]
    recent = prev_chapters[-3:]
    state = _parse_state_snapshot(last.story_state_snapshot or "")
    next_must_follow = state.get("next_must_follow") or []
    facts = state.get("facts") or []

    parts = [
        f"【上一弧线】{prev_arc.get('name', '')}",
        f"叙事功能：{prev_arc.get('narrative_function', '')}",
        f"弧线概要：{_clip_text(prev_arc.get('description', ''), 500)}",
    ]
    if recent:
        parts.append("【上一弧线最近章节主内容】")
        for ch in recent:
            events = "；".join(_safe_str(e) for e in (ch.key_events or [])[:4])
            parts.append(f"- 第{ch.chapter_number}章《{ch.title or ''}》：{_clip_text(ch.summary or '', 220)}")
            if events:
                parts.append(f"  核心事件：{events}")
    parts.extend([
        "【上一弧线终点状态】",
        _clip_text(last.connects_to or last.summary or "", 500),
    ])
    if last.hook:
        parts.append(f"【上一弧线最后钩子】{_clip_text(last.hook, 300)}")
    if facts:
        parts.append("【长期事实变化】" + "；".join(_safe_str(x) for x in facts[:6]))
    if next_must_follow:
        parts.append("【下一弧线必须承接】" + "；".join(_safe_str(x) for x in next_must_follow[:6]))
    if next_arc:
        parts.extend([
            f"【下一弧线】{next_arc.get('name', '')}",
            f"对上一弧线的依赖：{_clip_text(next_arc.get('dependence_on_previous', ''), 400)}",
            f"下一弧线起点：{_clip_text(next_arc.get('description', ''), 400)}",
        ])
    return "\n".join(p for p in parts if p)


async def _build_arc_bridge_context(db: AsyncSession, volume: Volume, arc_index: int) -> str:
    arcs = volume.narrative_arcs or []
    if arc_index <= 0 or arc_index >= len(arcs):
        return ""
    prev_arc = arcs[arc_index - 1]
    current_arc = arcs[arc_index]
    if current_arc.get("bridge_from_previous"):
        return current_arc.get("bridge_from_previous", "")
    prev_chapters = (await db.execute(
        select(Chapter)
        .where(Chapter.volume_id == volume.id, Chapter.arc_name == prev_arc.get("name", ""))
        .order_by(Chapter.chapter_number)
    )).scalars().all()
    return _format_arc_bridge(prev_arc, prev_chapters, current_arc)


def _arc_index(volume: Volume | None, arc_name: str) -> int:
    if not volume or not arc_name:
        return -1
    for idx, arc in enumerate(volume.narrative_arcs or []):
        if arc.get("name") == arc_name:
            return idx
    return -1


async def _refresh_volume_arc_bridges(db: AsyncSession, volume: Volume):
    arcs = [dict(a) for a in (volume.narrative_arcs or [])]
    if not arcs:
        return
    for idx, arc in enumerate(arcs):
        if idx == 0:
            arc["bridge_from_previous"] = "无（本卷第一条弧线）"
        else:
            prev_arc = arcs[idx - 1]
            prev_chapters = (await db.execute(
                select(Chapter)
                .where(Chapter.volume_id == volume.id, Chapter.arc_name == prev_arc.get("name", ""))
                .order_by(Chapter.chapter_number)
            )).scalars().all()
            bridge = _format_arc_bridge(prev_arc, prev_chapters, arc)
            if bridge:
                arc["bridge_from_previous"] = bridge
                prev_arc["bridge_to_next"] = bridge
    volume.narrative_arcs = arcs


async def _generate_chapter_blueprint(db: AsyncSession, project_id: str, chapter: Chapter, prev_chapter: Chapter | None, vol: Volume | None) -> dict:
    bible = await build_story_bible(db, project_id, chapter.id)
    context = await build_generation_context(db, project_id, chapter.id)
    bridge_context = await _build_arc_bridge_context(db, vol, _arc_index(vol, chapter.arc_name)) if vol else ""
    ai = AIService()
    blueprint = await ai.generate_chapter_blueprint(
        story_context=bible,
        chapter_context={
            "current_chapter": context.get("current_chapter", {}),
            "current_volume": context.get("current_volume", {}),
            "recent_chapters": context.get("recent_chapters", []),
            "mandates": context.get("chapter_mandates", {}),
            "hard_constraints": context.get("hard_constraints", []),
            "tone_rules": context.get("tone_rules", []),
            "arc_bridge_context": bridge_context,
        },
    )
    if bridge_context:
        blueprint["arc_bridge_context"] = bridge_context
    chapter.blueprint = blueprint
    chapter.summary = blueprint.get("summary", chapter.summary or "")
    chapter.connects_from = prev_chapter.connects_to if prev_chapter and prev_chapter.connects_to else chapter.connects_from
    if bridge_context and (not chapter.connects_from or chapter.connects_from.startswith("无")):
        chapter.connects_from = bridge_context
    chapter.connects_to = blueprint.get("ending_hook", chapter.connects_to or "")
    chapter.key_events = blueprint.get("must_include", chapter.key_events or [])
    chapter.minor_events = blueprint.get("foreshadowing_tasks", chapter.minor_events or [])
    chapter.continuity_checks = blueprint.get("continuity_checks", {})
    chapter.causality_links = blueprint.get("causality_links", [])
    chapter.foreshadowing_tasks = blueprint.get("foreshadowing_tasks", [])
    chapter.rhythm_profile = blueprint.get("rhythm_profile", {})
    chapter.scene_count = len(blueprint.get("scene_beats", []))
    chapter.narrative_line = chapter.narrative_line or "main"
    return blueprint


async def _extract_and_apply_state(db: AsyncSession, project_id: str, chapter: Chapter, content: str) -> dict:
    bible = await build_story_bible(db, project_id, chapter.id)
    context = await build_generation_context(db, project_id, chapter.id)
    ai = AIService()
    result = await ai.summarize_state(
        story_context=bible,
        chapter_context={
            "current_chapter": context.get("current_chapter", {}),
            "current_volume": context.get("current_volume", {}),
            "recent_chapters": context.get("recent_chapters", []),
            "hard_constraints": context.get("hard_constraints", []),
            "tone_rules": context.get("tone_rules", []),
        },
        content=content,
    )
    chapter.story_state_snapshot = json.dumps(result, ensure_ascii=False)[:3000]

    chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
    chars = {c.name: c for c in chars_result.scalars().all()}
    for change in result.get("character_changes", []):
        name = change.get("name")
        if name in chars:
            chars[name].current_state = change.get("current_state", {})
            db.add(StoryStateTrail(
                project_id=project_id,
                chapter_id=chapter.id,
                chapter_number=chapter.chapter_number,
                state_snapshot=change,
                change_description=change.get("change", ""),
            ))

    for event in result.get("timeline_events", []):
        db.add(TimelineEvent(
            project_id=project_id,
            chapter_id=chapter.id,
            time_point=event.get("time_point", f"第{chapter.chapter_number}章"),
            description=event.get("description", ""),
            event_type=event.get("event_type", "event"),
            is_major_event=event.get("is_major", False),
        ))

    return result


async def _save_chapter_version(db: AsyncSession, chapter: Chapter, source: str, note: str = "", config: dict | None = None):
    if not chapter.content:
        return
    with db.no_autoflush:
        max_version = await db.scalar(
            select(func.max(ChapterVersion.version_number)).where(ChapterVersion.chapter_id == chapter.id)
        ) or 0
    db.add(ChapterVersion(
        project_id=chapter.project_id,
        chapter_id=chapter.id,
        version_number=max_version + 1,
        title=chapter.title or "",
        content=chapter.content or "",
        word_count=chapter.word_count or len(chapter.content or ""),
        source=source,
        note=note,
        generation_config=config or {},
    ))


async def _commit_with_retry(db: AsyncSession, attempts: int = 4):
    for i in range(attempts):
        try:
            await db.commit()
            return
        except OperationalError as e:
            if "database is locked" not in str(e).lower() or i == attempts - 1:
                raise
            await db.rollback()
            await asyncio.sleep(0.35 * (i + 1))


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


async def _do_write_chapter(project_id: str, chapter_id: str, mode: str = "append", instruction: str = "", controls: dict | None = None, preview: bool = False) -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if not chapter:
            raise RuntimeError("章节不存在")
        vol = (await db.execute(select(Volume).where(Volume.id == chapter.volume_id))).scalar_one_or_none()
        arc_idx = _arc_index(vol, chapter.arc_name)
        bridge_context = await _build_arc_bridge_context(db, vol, arc_idx) if vol else ""

        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars = chars_result.scalars().all()
        chars_summary = "\n".join([_build_character_profile(c) for c in chars])

        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs = facs_result.scalars().all()
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs])

        prev_chapter = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)

        previous_ending = "无（这是第一章）"
        story_state_snapshot = "无（这是第一章）"
        if prev_chapter and prev_chapter.content:
            opening = prev_chapter.content[:300] if len(prev_chapter.content) > 300 else prev_chapter.content
            ending = prev_chapter.content[-500:] if len(prev_chapter.content) > 500 else prev_chapter.content
            previous_ending = f"【开头】{opening}\n\n……\n\n【结尾】{ending}"
            if prev_chapter.hook:
                previous_ending += f"\n\n【上章钩子】{prev_chapter.hook}"
            story_state_snapshot = _build_story_state_snapshot(prev_chapter, prev_chapter.story_state_snapshot or "")
        elif chapter.connects_from:
            previous_ending = chapter.connects_from
        if bridge_context and (arc_idx > 0):
            previous_ending = f"【跨弧线桥接记忆——必须承接】\n{bridge_context}\n\n【上一章/上承状态】\n{previous_ending}"
            story_state_snapshot = f"{story_state_snapshot}\n\n【跨弧线长期记忆】\n{bridge_context}"[:3000]

        pov_char = "主角"
        if chapter.characters_in_chapter:
            pov_char = chapter.characters_in_chapter[0] if chapter.characters_in_chapter else "主角"

        controls = _merge_writing_controls(project, controls)
        target_words = controls.get("target_words") or chapter.target_words or 3000
        if not chapter.blueprint:
            await _generate_chapter_blueprint(db, project_id, chapter, prev_chapter, vol)
        context = await build_generation_context(db, project_id, chapter.id)
        ai = AIService()
        if controls:
            extra = "；".join([f"{k}:{v}" for k, v in controls.items() if v not in [None, ""]])
            chapter_summary = f"{chapter.summary or ''}\n\n【本次写作控制】{extra}\n{_writing_controls_guidance(controls)}\n【用户要求】{instruction or '无'}"
        else:
            chapter_summary = chapter.summary or instruction or ""
        if bridge_context and arc_idx > 0:
            chapter_summary = f"{chapter_summary}\n\n【跨弧线桥接要求】\n{bridge_context}"

        text, hook, new_characters = await ai.write_chapter(
            project.title, project.genre, _wizard_story_brief(project),
            chapter.chapter_number, chapter.title or "", chapter_summary,
            vol.outline if vol else "", chars_summary, facs_summary,
            min_words=target_words, written_so_far=len(chapter.content or ""),
            previous_ending=previous_ending,
            story_state_snapshot=(json.dumps(context.get("recent_chapters", []), ensure_ascii=False) + "\n" + bridge_context)[:1600] if context else story_state_snapshot,
            pov_character=pov_char,
            readability_guidance=_readability_guidance(controls),
            early_grip_guidance=_early_grip_guidance(project, chapter, vol, controls),
        )
        text, quality_review = await _review_and_light_fix_chapter(
            ai,
            project,
            chapter,
            text,
            previous_ending,
            story_state_snapshot,
            controls,
        )
        if preview:
            return {"content": text, "hook": hook, "new_characters": new_characters, "mode": mode, "blueprint": chapter.blueprint, "quality_review": quality_review}

        await _save_chapter_version(db, chapter, "ai_write", f"AI 写作前备份：{mode}", {"mode": mode, "instruction": instruction, "controls": controls})
        if mode in {"replace", "rewrite", "from_scratch"}:
            chapter.content = text
        else:
            chapter.content = (chapter.content or "") + text
        chapter.hook = hook
        chapter.word_count = len(chapter.content)
        if isinstance(quality_review, dict):
            chapter.quality_score = int(quality_review.get("overall_score") or 0) or chapter.quality_score
            checks = chapter.continuity_checks or {}
            checks["quality_review"] = quality_review
            chapter.continuity_checks = checks
        chapter.status = _status_after_content_change(chapter.status)
        chapter.version = (chapter.version or 1) + 1
        with db.no_autoflush:
            await _extract_and_apply_state(db, project_id, chapter, chapter.content)
        if vol:
            await _refresh_volume_arc_bridges(db, vol)

        if new_characters:
            existing_names = {c.name for c in chars}
            for nc in new_characters:
                if nc["name"] not in existing_names:
                    db.add(Character(project_id=project_id, name=nc["name"], role_type=_normalize_role_type(nc.get("role_type", "配角")),
                        personality=nc.get("description", ""), growth_stages=[],
                        first_appeared_chapter=chapter.chapter_number, first_appeared_title=chapter.title or "",
                        character_class="one_off"))
                    existing_names.add(nc["name"])

        await db.commit()
        return {"content": text, "new_characters": new_characters, "mode": mode, "blueprint": chapter.blueprint}


def _normalize_split_segments(data: dict, fallback_title: str) -> list[dict]:
    raw_segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(raw_segments, list):
        raw_segments = []
    segments = []
    for idx, item in enumerate(raw_segments, start=1):
        if not isinstance(item, dict):
            continue
        content = (item.get("content") or "").strip()
        if not content:
            continue
        segments.append({
            "title": (item.get("title") or f"{fallback_title}·{idx}").strip()[:100],
            "summary": (item.get("summary") or "").strip()[:2000],
            "connects_from": (item.get("connects_from") or "").strip()[:500],
            "connects_to": (item.get("connects_to") or "").strip()[:500],
            "hook": (item.get("hook") or item.get("connects_to") or "").strip()[:500],
            "content": content,
        })
    return segments


def _normalize_split_metadata(data: dict, fallback_title: str) -> list[dict]:
    raw_segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(raw_segments, list):
        raw_segments = []
    segments = []
    for idx, item in enumerate(raw_segments, start=1):
        if not isinstance(item, dict):
            continue
        segments.append({
            "title": (item.get("title") or f"{fallback_title}·{idx}").strip()[:100],
            "summary": (item.get("summary") or "").strip()[:2000],
            "connects_from": (item.get("connects_from") or "").strip()[:500],
            "connects_to": (item.get("connects_to") or "").strip()[:500],
            "hook": (item.get("hook") or item.get("connects_to") or "").strip()[:500],
        })
    return segments


def _text_split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；;])", text)
    return [p.strip() for p in parts if p and p.strip()]


def _hard_split_text(text: str, target_chars: int, min_chars: int, max_chars: int) -> list[str]:
    text = (text or "").strip()
    chunks: list[str] = []
    pos = 0
    n = len(text)
    punctuation = "。！？!?；;\n"
    while pos < n:
        remaining = n - pos
        if chunks and remaining < min_chars:
            chunks[-1] = f"{chunks[-1].rstrip()}\n\n{text[pos:].lstrip()}".strip()
            break
        if remaining <= max_chars:
            chunks.append(text[pos:].strip())
            break

        ideal = min(pos + target_chars, n)
        left = max(pos + min_chars, pos + int(target_chars * 0.75))
        right = min(pos + max_chars, n)
        cut = -1
        for i in range(ideal, left, -1):
            if text[i - 1] in punctuation:
                cut = i
                break
        if cut < 0:
            for i in range(ideal, right):
                if text[i - 1] in punctuation:
                    cut = i
                    break
        if cut < 0:
            cut = ideal

        chunks.append(text[pos:cut].strip())
        pos = cut

    return [chunk for chunk in chunks if chunk]


def _force_two_way_split(text: str) -> list[str]:
    source = (text or "").strip()
    if len(source) < 2:
        return [source] if source else []

    mid = len(source) // 2
    left_search = max(0, mid - 600)
    right_search = min(len(source), mid + 600)
    punctuation = "。！？!?；;\n"

    cut = -1
    for i in range(mid, left_search, -1):
        if source[i - 1] in punctuation:
            cut = i
            break
    if cut < 0:
        for i in range(mid, right_search):
            if source[i - 1] in punctuation:
                cut = i
                break
    if cut < 0:
        cut = mid

    left = source[:cut].strip()
    right = source[cut:].strip()
    if not left or not right:
        cut = max(1, min(len(source) - 1, mid))
        left = source[:cut].strip()
        right = source[cut:].strip()
    return [seg for seg in [left, right] if seg]


def _build_deterministic_split_segments(content: str, target_words: int) -> list[dict]:
    text = (content or "").strip()
    if not text:
        return []

    target_chars = max(2400, int(target_words * 1.05))
    min_chars = max(2200, int(target_words * 0.7))
    last_min_chars = max(1600, int(target_words * 0.45))
    max_chars = max(target_chars, int(target_words * 1.45))

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if len(paragraphs) == 1 and len(paragraphs[0]) > max_chars:
        single_line_parts = [p.strip() for p in re.split(r"\n+", paragraphs[0]) if p.strip()]
        if len(single_line_parts) > 1:
            paragraphs = single_line_parts
    if len(paragraphs) == 1 and len(paragraphs[0]) > max_chars * 1.4:
        paragraphs = _text_split_sentences(paragraphs[0])

    segments: list[str] = []
    current = ""

    def flush_current():
        nonlocal current
        if current.strip():
            segments.append(current.strip())
        current = ""

    for para in paragraphs:
        if not current:
            current = para
            continue

        candidate = f"{current}\n\n{para}".strip()
        if len(candidate) <= max_chars or len(current) < min_chars:
            current = candidate
            continue

        flush_current()
        current = para

    flush_current()

    if len(segments) > 1 and len(segments[-1]) < last_min_chars:
        segments[-2] = f"{segments[-2].rstrip()}\n\n{segments[-1].lstrip()}".strip()
        segments.pop()

    merged: list[str] = []
    for seg in segments:
        if merged and len(seg) < min_chars:
            merged[-1] = f"{merged[-1].rstrip()}\n\n{seg.lstrip()}".strip()
        else:
            merged.append(seg)

    if len(merged) == 1 and len(merged[0]) > max_chars * 1.4:
        source = merged.pop()
        sentences = _text_split_sentences(source)
        current = ""
        for sentence in sentences:
            candidate = f"{current}{sentence}".strip()
            if not current:
                current = sentence.strip()
                continue
            if len(candidate) <= max_chars or len(current) < min_chars:
                current = candidate
            else:
                merged.append(current.strip())
                current = sentence.strip()
        if current.strip():
            merged.append(current.strip())

    if len(merged) <= 1 and len(text) > max_chars:
        merged = _hard_split_text(text, target_chars, min_chars, max_chars)

    if len(merged) <= 1 and len(text) > target_chars:
        merged = _force_two_way_split(text)

    if len(merged) > 1 and len(merged[-1]) < last_min_chars:
        merged[-2] = f"{merged[-2].rstrip()}\n\n{merged[-1].lstrip()}".strip()
        merged.pop()

    if len(merged) > 1:
        # Final safety pass: absorb any tiny tail or middle fragment.
        final_segments: list[str] = []
        for idx, seg in enumerate(merged):
            current_min = last_min_chars if idx == len(merged) - 1 else min_chars
            if final_segments and len(seg) < current_min:
                final_segments[-1] = f"{final_segments[-1].rstrip()}\n\n{seg.lstrip()}".strip()
            else:
                final_segments.append(seg)
        merged = final_segments

    return [{"content": seg} for seg in merged if seg.strip()]


def _merge_split_segment(left: dict, right: dict) -> dict:
    left["content"] = f"{left.get('content', '').rstrip()}\n\n{right.get('content', '').lstrip()}".strip()
    if right.get("summary"):
        left["summary"] = (f"{left.get('summary', '').rstrip()}；{right.get('summary', '').lstrip()}").strip("；")[:2000]
    left["connects_to"] = right.get("connects_to") or left.get("connects_to", "")
    left["hook"] = right.get("hook") or left.get("hook", "")
    return left


def _rebalance_split_segments(segments: list[dict], target_words: int) -> list[dict]:
    if len(segments) <= 1:
        return segments
    min_words = max(2200, int(target_words * 0.65))
    last_min_words = max(1600, int(target_words * 0.45))

    balanced: list[dict] = []
    for segment in segments:
        if balanced and len(segment.get("content", "")) < min_words:
            balanced[-1] = _merge_split_segment(balanced[-1], segment)
        else:
            balanced.append(segment)

    if len(balanced) > 1 and len(balanced[-1].get("content", "")) < last_min_words:
        tail = balanced.pop()
        balanced[-1] = _merge_split_segment(balanced[-1], tail)

    # A first pass can make the previous segment too large, but that is still better
    # than creating unusable micro chapters. Only repeat while it removes short items.
    changed = True
    while changed and len(balanced) > 1:
        changed = False
        next_segments: list[dict] = []
        for idx, segment in enumerate(balanced):
            current_min = last_min_words if idx == len(balanced) - 1 else min_words
            if next_segments and len(segment.get("content", "")) < current_min:
                next_segments[-1] = _merge_split_segment(next_segments[-1], segment)
                changed = True
            else:
                next_segments.append(segment)
        balanced = next_segments

    return balanced


async def _do_split_chapter(project_id: str, chapter_id: str, body: SplitChapterRequest) -> dict:
    target_words = max(3000, min(body.target_words or 3500, 5200))
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if not project or not chapter:
            raise RuntimeError("章节不存在")
        if not chapter.content or len(chapter.content) < target_words * 1.35:
            raise RuntimeError("当前章节字数不长，暂不需要拆分")
        original = {
            "chapter_number": chapter.chapter_number,
            "title": chapter.title or "",
            "summary": chapter.summary or "",
            "content": chapter.content or "",
            "volume_id": chapter.volume_id,
            "arc_name": chapter.arc_name or "",
            "target_words": chapter.target_words or target_words,
            "narrative_line": chapter.narrative_line or "main",
            "tension_actual": chapter.tension_actual,
        }

    ai = AIService()
    raw_segments = _build_deterministic_split_segments(original["content"], target_words)
    if len(raw_segments) <= 1:
        raise RuntimeError("当前章节无法拆成多个合理片段")

    meta_result = {}
    try:
        meta_result = await ai.split_chapter_metadata(
            project.title, project.genre, original["chapter_number"], original["title"],
            raw_segments, target_words,
        )
    except Exception:
        meta_result = {}

    meta_segments = _normalize_split_metadata(meta_result, original["title"] or f"第{original['chapter_number']}章")
    if len(meta_segments) == len(raw_segments):
        for idx, segment in enumerate(raw_segments):
            segment.update({k: meta_segments[idx].get(k, segment.get(k, "")) for k in ["title", "summary", "connects_from", "connects_to", "hook"]})
    else:
        for idx, segment in enumerate(raw_segments, start=1):
            segment.update({
                "title": f"{original['title'] or f'第{original['chapter_number']}章'}·{idx}",
                "summary": "",
                "connects_from": "",
                "connects_to": "",
                "hook": "",
            })

    segments = _rebalance_split_segments(raw_segments, target_words)
    if len(segments) <= 1:
        fallback_parts = _force_two_way_split(original["content"])
        if len(fallback_parts) >= 2:
            segments = [{"content": part} for part in fallback_parts]
        else:
            raise RuntimeError("正文无法拆成多个合理章节，请检查正文格式或降低拆分阈值")

    if not body.apply:
        return {
            "segments": segments,
            "count": len(segments),
            "raw_count": len(raw_segments),
            "merged_short_segments": len(raw_segments) - len(segments),
            "applied": False,
        }

    async with async_session() as db:
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if not chapter:
            raise RuntimeError("章节不存在")
        await _save_chapter_version(db, chapter, "smart_split", "智能拆分前自动备份", {
            "target_words": target_words,
            "segment_count": len(segments),
        })

        added_count = len(segments) - 1
        later_chapters = (await db.execute(
            select(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number > chapter.chapter_number,
            ).order_by(Chapter.chapter_number.desc())
        )).scalars().all()
        for later in later_chapters:
            later.chapter_number = later.chapter_number + added_count

        first = segments[0]
        chapter.title = first["title"]
        chapter.summary = first["summary"] or chapter.summary
        chapter.connects_from = first["connects_from"] or chapter.connects_from
        chapter.connects_to = first["connects_to"]
        chapter.hook = first["hook"]
        chapter.content = first["content"]
        chapter.word_count = len(first["content"])
        chapter.target_words = target_words
        chapter.status = _status_after_content_change(chapter.status)
        chapter.version = (chapter.version or 1) + 1

        created = []
        previous_number = chapter.chapter_number
        for offset, segment in enumerate(segments[1:], start=1):
            new_chapter = Chapter(
                project_id=project_id,
                volume_id=chapter.volume_id,
                chapter_number=chapter.chapter_number + offset,
                title=segment["title"],
                summary=segment["summary"],
                arc_name=chapter.arc_name or "",
                connects_from=segment["connects_from"] or segments[offset - 1].get("connects_to", ""),
                connects_to=segment["connects_to"],
                hook=segment["hook"],
                characters_in_chapter=chapter.characters_in_chapter or [],
                key_events=[],
                minor_events=[],
                content=segment["content"],
                word_count=len(segment["content"]),
                target_words=target_words,
                status=_status_after_content_change(chapter.status),
                narrative_line=chapter.narrative_line or "main",
                tension_actual=chapter.tension_actual,
            )
            db.add(new_chapter)
            await db.flush()
            created.append({
                "id": str(new_chapter.id),
                "chapter_number": new_chapter.chapter_number,
                "title": new_chapter.title,
                "word_count": new_chapter.word_count,
            })
            previous_number = new_chapter.chapter_number

        await db.commit()
        return {
            "applied": True,
            "source_chapter_id": chapter_id,
            "source_chapter_number": original["chapter_number"],
            "segment_count": len(segments),
            "raw_segment_count": len(raw_segments),
            "merged_short_segments": len(raw_segments) - len(segments),
            "created": created,
            "chapters": [
                {"chapter_number": original["chapter_number"] + idx, "title": seg["title"], "word_count": len(seg["content"])}
                for idx, seg in enumerate(segments)
            ],
        }


def _render_export_payload(title: str, scope_label: str, chapters: list[dict], fmt: str) -> tuple[bytes, str, str]:
    fmt = (fmt or "md").lower()
    if fmt not in {"md", "txt", "json"}:
        fmt = "md"

    if fmt == "json":
        payload = {
            "title": title,
            "scope": scope_label,
            "chapter_count": len(chapters),
            "chapters": chapters,
        }
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return data, "application/json; charset=utf-8", "json"

    lines: list[str] = []
    if fmt == "md":
        lines.append(f"# {title}")
        lines.append(f"## {scope_label}")
    else:
        lines.append(f"{title}")
        lines.append(f"{scope_label}")
        lines.append("")

    for ch in chapters:
        chapter_head = f"第{ch['chapter_number']}章 {ch['title'] or ''}".strip()
        if fmt == "md":
            lines.extend([f"## {chapter_head}", ""])
            if ch.get("summary"):
                lines.extend([f"> {ch['summary']}", ""])
        else:
            lines.extend([chapter_head, ""])
            if ch.get("summary"):
                lines.extend([f"摘要：{ch['summary']}", ""])
        if ch.get("content"):
            lines.append(ch["content"])
        if fmt == "md":
            lines.append("")
        else:
            lines.extend(["", ""])

    data = "\n".join(lines).strip().encode("utf-8")
    media_type = "text/markdown; charset=utf-8" if fmt == "md" else "text/plain; charset=utf-8"
    return data, media_type, fmt


@router.post("/export-manuscript")
async def export_manuscript(project_id: str, body: ExportManuscriptRequest, user: User = Depends(get_current_user)):
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))).scalar_one_or_none()
        if not project:
            raise HTTPException(404, "项目不存在")
        volume = (await db.execute(select(Volume).where(Volume.id == body.volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume:
            raise HTTPException(404, "卷不存在")

        chapters_stmt = select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume.id)
        scope_label = f"卷《{volume.title or f'卷{volume.volume_number}'}》"
        export_name_base = f"{project.title or '小说'}-卷{volume.volume_number}"

        if body.scope == "arc":
            if not body.arc_name:
                raise HTTPException(400, "请提供弧线名称")
            chapters_stmt = chapters_stmt.where(Chapter.arc_name == body.arc_name)
            scope_label = f"{scope_label} · 弧线《{body.arc_name}》"
            safe_arc = re.sub(r"[^\w\u4e00-\u9fa5-]+", "_", body.arc_name).strip("_") or "arc"
            export_name_base = f"{export_name_base}-{safe_arc}"

        chapters = (await db.execute(chapters_stmt.order_by(Chapter.chapter_number))).scalars().all()
        if not chapters:
            raise HTTPException(404, "没有可导出的章节")

        chapter_payload = [
            {
                "id": str(ch.id),
                "chapter_number": ch.chapter_number,
                "title": ch.title or "",
                "summary": ch.summary or "",
                "arc_name": ch.arc_name or "",
                "content": ch.content or "",
                "word_count": ch.word_count or len(ch.content or ""),
                "target_words": ch.target_words or 0,
            }
            for ch in chapters
            if body.include_empty or ch.content
        ]

    data, media_type, ext = _render_export_payload(project.title or "小说", scope_label, chapter_payload, body.format)
    filename = f"{export_name_base}.{ext}"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }
    return StreamingResponse(io.BytesIO(data), media_type=media_type, headers=headers)


async def _do_batch_write_arc(project_id: str, volume_id: str, arc_index: int, task_id: str = "", chapter_ids: list[str] | None = None, readability_mode: str = "easy", controls: dict | None = None) -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("请先生成弧线和章节")
        arc = volume.narrative_arcs[arc_index]

        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars = chars_result.scalars().all()
        chars_summary = "\n".join([_build_character_profile(c) for c in chars])

        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs = facs_result.scalars().all()
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs])

        chapters = (await db.execute(
            select(Chapter).where(Chapter.volume_id == volume_id, Chapter.arc_name == arc.get("name", "")).order_by(Chapter.chapter_number)
        )).scalars().all()

        if not chapters:
            raise RuntimeError("请先展开章节")

        todo = [c for c in chapters if not c.content]
        if chapter_ids:
            todo = [c for c in todo if c.id in chapter_ids]
        if not todo:
            return {"total": 0, "done": 0}

        write_controls = _merge_writing_controls(project, controls or {"readability_mode": readability_mode})
        write_controls["readability_mode"] = readability_mode or write_controls.get("readability_mode", "easy")
        ai = AIService()
        total_words = 0
        done = 0
        total = len(todo)
        known_names = {c.name for c in chars}
        if task_id:
            update_progress(task_id, 0, f"准备批量写作：{arc.get('name', '')}，共 {total} 章", {
                "arc_name": arc.get("name", ""),
                "total": total,
                "done": 0,
                "chapter_numbers": [c.chapter_number for c in todo],
            })
        previous_ending = "无（这是第一章）"
        story_state_snapshot = "无（这是第一章）"
        previous_hook = ""
        arc_bridge_context = await _build_arc_bridge_context(db, volume, arc_index)
        if arc_bridge_context and arc_index > 0:
            previous_ending = f"【跨弧线桥接记忆——本弧线必须从这里接】\n{arc_bridge_context}"
            story_state_snapshot = arc_bridge_context[:3000]

        for all_ch in chapters:
            if all_ch.content:
                ending = all_ch.content[-500:] if len(all_ch.content) > 500 else all_ch.content
                previous_ending = ending
                previous_hook = all_ch.hook or ""
                story_state_snapshot = _build_story_state_snapshot(all_ch, story_state_snapshot)
                total_words += len(all_ch.content)
                continue

        for ch in todo:
            ending_context = f"【前一章结尾——从这里接】\n{previous_ending}"
            if previous_hook:
                ending_context += f"\n\n【上一章钩子——必须从这个悬念开始续写】\n{previous_hook}"
            if ch.connects_from:
                ending_context += f"\n\n【蓝图要求的上承状态】\n{ch.connects_from}"
            if arc_bridge_context and ch == todo[0]:
                ending_context = f"【跨弧线桥接记忆——必须优先承接】\n{arc_bridge_context}\n\n{ending_context}"
            final_ending = ending_context
            if task_id:
                if is_cancelled(task_id):
                    update_progress(task_id, done / total if total else 0, f"已取消：停在第{ch.chapter_number}章《{ch.title or ''}》", {
                        "arc_name": arc.get("name", ""),
                        "total": total,
                        "done": done,
                        "current_chapter_number": ch.chapter_number,
                        "current_chapter_title": ch.title or "",
                    })
                    return {"total": total, "done": done, "cancelled": True}
                update_progress(task_id, done / total if total else 0, f"正在写第{ch.chapter_number}章《{ch.title or ''}》... ({done + 1}/{total})", {
                    "arc_name": arc.get("name", ""),
                    "total": total,
                    "done": done,
                    "current_chapter_id": str(ch.id),
                    "current_chapter_number": ch.chapter_number,
                    "current_chapter_title": ch.title or "",
                    "stage": "writing",
                })

            if not ch.blueprint:
                await _generate_chapter_blueprint(db, project_id, ch, None, volume)
            if arc_bridge_context and isinstance(ch.blueprint, dict):
                ch.blueprint["arc_bridge_context"] = arc_bridge_context

            pov_char = "主角"
            if ch.characters_in_chapter:
                pov_char = ch.characters_in_chapter[0] if ch.characters_in_chapter else "主角"

            text, hook, new_characters = await ai.write_chapter(
                project.title, project.genre, _wizard_story_brief(project),
                ch.chapter_number, ch.title or "", f"{ch.summary or ''}\n\n【本次写作控制】\n{_writing_controls_guidance(write_controls)}",
                volume.outline or "", chars_summary, facs_summary,
                min_words=ch.target_words or 3000, written_so_far=0,
                previous_ending=final_ending,
                story_state_snapshot=story_state_snapshot,
                pov_character=pov_char,
                readability_guidance=_readability_guidance(write_controls),
                early_grip_guidance=_early_grip_guidance(project, ch, volume, write_controls),
            )
            text, quality_review = await _review_and_light_fix_chapter(
                ai,
                project,
                ch,
                text,
                final_ending,
                story_state_snapshot,
                write_controls,
            )
            ch.content = text
            ch.hook = hook
            ch.word_count = len(text)
            if isinstance(quality_review, dict):
                ch.quality_score = int(quality_review.get("overall_score") or 0) or ch.quality_score
                checks = ch.continuity_checks or {}
                checks["quality_review"] = quality_review
                ch.continuity_checks = checks
            ch.status = "completed"
            ch.story_state_snapshot = _build_story_state_snapshot(ch, story_state_snapshot)
            total_words += len(text)
            await _refresh_volume_arc_bridges(db, volume)
            await db.commit()

            # propagate ending to next chapter
            previous_ending = text[-500:] if len(text) > 500 else text
            previous_hook = hook or ""
            story_state_snapshot = _build_story_state_snapshot(ch, story_state_snapshot)

            with db.no_autoflush:
                await _extract_and_apply_state(db, project_id, ch, ch.content)

            if new_characters:
                for nc in new_characters:
                    if nc["name"] not in known_names:
                        db.add(Character(project_id=project_id, name=nc["name"], role_type=_normalize_role_type(nc.get("role_type", "配角")),
                            personality=nc.get("description", ""), growth_stages=[],
                            first_appeared_chapter=ch.chapter_number, first_appeared_title=ch.title or "",
                            character_class="one_off"))
                        known_names.add(nc["name"])
            done += 1
            if task_id:
                update_progress(task_id, done / total if total else 1, f"已完成第{ch.chapter_number}章《{ch.title or ''}》 ({done}/{total})", {
                    "arc_name": arc.get("name", ""),
                    "total": total,
                    "done": done,
                    "current_chapter_id": str(ch.id),
                    "current_chapter_number": ch.chapter_number,
                    "current_chapter_title": ch.title or "",
                    "current_word_count": len(text),
                    "total_words": total_words,
                    "stage": "completed_chapter",
                })
            opening = text[:300] if len(text) > 300 else text
            ending = text[-500:] if len(text) > 500 else text
            previous_ending = f"【开头】{opening}\n\n……\n\n【结尾】{ending}"
            if hook:
                previous_ending += f"\n\n【上章钩子】{hook}"
            story_state_snapshot = ch.story_state_snapshot

        await db.commit()
        if task_id:
            update_progress(task_id, 1, f"批量写作完成：{arc.get('name', '')}，共 {done}/{total} 章", {
                "arc_name": arc.get("name", ""),
                "total": total,
                "done": done,
                "total_words": total_words,
                "stage": "completed",
            })
        return {"chapter_count": len(chapters), "total_words": total_words}


async def _do_expand_volume_arcs(
    project_id: str,
    volume_id: str,
    arc_strategy: str = "标准长篇策划",
    arc_density: str = "标准弧线",
    style_focus: str = "主线清晰，角色自然成长",
    length_control: str = "按全书体量和本卷复杂度自主判断",
    clear_existing_chapters: bool = False,
) -> dict:
    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume:
            raise RuntimeError("卷不存在")
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = ", ".join([f"{c.name}({c.role_type})" for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = ", ".join([f"{f.name}({f.faction_type})" for f in facs_result.scalars().all()])
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "volume_title": volume.title,
            "volume_outline": volume.outline or "",
            "chapter_count": volume.chapter_count,
            "chars_summary": chars_summary,
            "facs_summary": facs_summary,
            "arc_strategy": arc_strategy,
            "arc_density": arc_density,
            "style_focus": style_focus,
            "length_control": length_control,
        }

    ai = AIService()
    arcs = await ai.expand_volume_arcs(
        snapshot["title"],
        snapshot["genre"],
        snapshot["volume_title"],
        snapshot["volume_outline"],
        snapshot["chars_summary"],
        snapshot["facs_summary"],
        snapshot["chapter_count"],
        arc_strategy=snapshot["arc_strategy"],
        arc_density=snapshot["arc_density"],
        style_focus=snapshot["style_focus"],
        length_control=snapshot["length_control"],
    )

    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume:
            raise RuntimeError("卷已被重新生成或删除，请刷新页面后重新展开弧线")
        cleared_chapters = 0
        if clear_existing_chapters:
            cleared_chapters = await _clear_volume_chapters(db, project_id, volume_id)
        volume.narrative_arcs = arcs
        await db.commit()
        return {"arcs": arcs, "cleared_chapters": cleared_chapters}


async def _do_revise_volume_arc(project_id: str, volume_id: str, arc_index: int, action: str, instruction: str = "", regenerate_chapters: bool = False) -> dict:
    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("请先生成弧线")
        arcs = list(volume.narrative_arcs or [])
        if arc_index < 0 or arc_index >= len(arcs):
            raise RuntimeError("弧线索引无效")
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = ", ".join([f"{c.name}({c.role_type})" for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = ", ".join([f"{f.name}({f.faction_type})" for f in facs_result.scalars().all()])
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "volume_title": volume.title,
            "volume_outline": volume.outline or "",
            "characters_summary": chars_summary,
            "factions_summary": facs_summary,
            "previous_arc": arcs[arc_index - 1] if arc_index > 0 else {},
            "current_arc": arcs[arc_index],
            "next_arc": arcs[arc_index + 1] if arc_index + 1 < len(arcs) else {},
            "arc_name": arcs[arc_index].get("name", ""),
            "has_chapters": bool((await db.execute(
                select(Chapter.id).where(Chapter.volume_id == volume_id, Chapter.arc_name == arcs[arc_index].get("name", "")).limit(1)
            )).scalar_one_or_none()),
        }

    ai = AIService()
    revised = await ai.revise_volume_arc(
        snapshot["title"],
        snapshot["genre"],
        snapshot["volume_title"],
        snapshot["volume_outline"],
        snapshot["characters_summary"],
        snapshot["factions_summary"],
        snapshot["previous_arc"],
        snapshot["current_arc"],
        snapshot["next_arc"],
        action,
        instruction,
    )

    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("卷已变化，请刷新页面后重试")
        arcs = list(volume.narrative_arcs or [])
        if arc_index >= len(arcs) or arcs[arc_index].get("name", "") != snapshot["arc_name"]:
            raise RuntimeError("弧线已变化，请刷新页面后重试")
        old_arc = arcs[arc_index]
        old_arc_name = old_arc.get("name", "")
        revised.setdefault("chapter_start", old_arc.get("chapter_start"))
        revised.setdefault("chapter_end", old_arc.get("chapter_end"))
        revised.setdefault("chapter_count", old_arc.get("chapter_count"))
        arcs[arc_index] = revised
        volume.narrative_arcs = arcs
        await db.commit()

    chapters_result = None
    if regenerate_chapters:
        async with async_session() as db:
            old_chapters = (await db.execute(
                select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id, Chapter.arc_name == old_arc_name)
            )).scalars().all()
            deleted = await _delete_chapters_with_related(db, project_id, old_chapters)
            if deleted:
                await db.commit()
        chapters_result = await _do_expand_arc_chapters(
            project_id,
            volume_id,
            arc_index,
            pacing="fast",
            event_density="high",
            expansion_scale="standard",
        )

    return {
        "arc": revised,
        "arc_index": arc_index,
        "regenerated_chapters": bool(regenerate_chapters),
        "chapters": chapters_result,
    }


async def _normalize_volume_arc_chapters(db: AsyncSession, volume: Volume):
    """Keep chapter numbers and cross-arc handoff continuous inside one volume."""
    arcs = volume.narrative_arcs or []
    if not arcs:
        return

    chapter_no = volume.chapter_range_start or 1
    previous_ending = ""
    for arc_index, arc in enumerate(arcs):
        arc_name = arc.get("name", "")
        chapters = (await db.execute(
            select(Chapter)
            .where(Chapter.volume_id == volume.id, Chapter.arc_name == arc_name)
            .order_by(Chapter.chapter_number, Chapter.created_at)
        )).scalars().all()
        if not chapters:
            continue

        if arc_index > 0 and previous_ending:
            first = chapters[0]
            if not first.connects_from or first.connects_from.startswith("无"):
                first.connects_from = previous_ending

        for ch in chapters:
            ch.chapter_number = chapter_no
            chapter_no += 1

        last = chapters[-1]
        previous_ending = last.connects_to or last.summary or previous_ending


def _arc_chapter_range_guidance(arc: dict, expansion_scale: str) -> str:
    base = int(arc.get("chapter_count") or 8)
    if expansion_scale == "compact":
        low, high = max(4, round(base * 0.65)), max(6, round(base * 0.9))
    elif expansion_scale == "long":
        low, high = max(8, round(base * 1.25)), max(12, round(base * 1.7))
    elif expansion_scale == "detailed":
        low, high = max(12, round(base * 1.7)), max(16, round(base * 2.4))
    else:
        low, high = max(6, round(base * 0.9)), max(8, round(base * 1.25))
    if high < low:
        high = low + 2
    return f"建议 {low}-{high} 章；这是内部范围，不要向用户询问具体章数。若弧线复杂度明显更高，可以超过上限，但必须保证每章有明确叙事功能。"


async def _do_expand_arc_chapters(project_id: str, volume_id: str, arc_index: int, pacing: str = "medium", event_density: str = "medium", expansion_scale: str = "standard") -> dict:
    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("请先生成弧线")
        if arc_index < 0 or arc_index >= len(volume.narrative_arcs):
            raise RuntimeError("弧线索引无效")
        arc = dict(volume.narrative_arcs[arc_index])
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = ", ".join([f"{c.name}({c.role_type})" for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = ", ".join([f"{f.name}({f.faction_type})" for f in facs_result.scalars().all()])

        previous_arc_ending = "无（这是第一条弧线）"
        start_chapter_number = volume.chapter_range_start or 1
        if arc_index > 0:
            bridge_context = await _build_arc_bridge_context(db, volume, arc_index)
            prev_arc = volume.narrative_arcs[arc_index - 1]
            prev_chapters = (await db.execute(
                select(Chapter).where(Chapter.volume_id == volume_id, Chapter.arc_name == prev_arc.get("name", ""))
                .order_by(Chapter.chapter_number.desc()).limit(1)
            )).scalars().all()
            if bridge_context:
                previous_arc_ending = bridge_context
            elif prev_chapters and prev_chapters[0].connects_to:
                previous_arc_ending = prev_chapters[0].connects_to
            elif prev_chapters and prev_chapters[0].summary:
                previous_arc_ending = prev_chapters[0].summary
            previous_arc_names = [a.get("name", "") for a in volume.narrative_arcs[:arc_index]]
            previous_max = (await db.execute(
                select(func.max(Chapter.chapter_number)).where(
                    Chapter.volume_id == volume_id,
                    Chapter.arc_name.in_(previous_arc_names),
                )
            )).scalar()
            if previous_max:
                start_chapter_number = previous_max + 1
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "volume_title": volume.title,
            "volume_outline": volume.outline or "",
            "default_chapter_words": volume.default_chapter_words,
            "arc": arc,
            "arc_name": arc.get("name", ""),
            "previous_arc_ending": previous_arc_ending,
            "start_chapter_number": start_chapter_number,
            "chars_summary": chars_summary,
            "facs_summary": facs_summary,
        }

    ai = AIService()
    nodes = await ai.expand_arc_chapters(
        snapshot["title"], snapshot["genre"], snapshot["volume_title"], snapshot["volume_outline"],
        snapshot["arc"].get("name", ""), snapshot["arc"].get("description", ""),
        snapshot["arc"].get("tension_curve", ""), snapshot["arc"].get("key_milestones", []),
        snapshot["previous_arc_ending"],
        snapshot["chars_summary"], snapshot["facs_summary"], pacing, event_density,
        expansion_scale=expansion_scale,
        chapter_range_guidance=_arc_chapter_range_guidance(snapshot["arc"], expansion_scale),
        narrative_function=snapshot["arc"].get("narrative_function", ""),
        emotional_color=snapshot["arc"].get("emotional_color", ""),
        dependence_on_previous=snapshot["arc"].get("dependence_on_previous", ""),
        payoff_for_next=snapshot["arc"].get("payoff_for_next", ""),
    )

    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("卷已被重新生成或删除，请刷新页面后重新展开章节")
        current_arcs = volume.narrative_arcs or []
        if arc_index >= len(current_arcs) or current_arcs[arc_index].get("name", "") != snapshot["arc_name"]:
            raise RuntimeError("弧线已变化，请刷新页面后重新展开章节")
        old_chapters = (await db.execute(select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id, Chapter.arc_name == snapshot["arc_name"]))).scalars().all()
        await _delete_chapters_with_related(db, project_id, old_chapters)
        for idx, node_data in enumerate(nodes):
            connects_from = _safe_str(node_data.get("connects_from", ""))
            if idx == 0 and arc_index > 0 and (not connects_from or connects_from.startswith("无")):
                connects_from = snapshot["previous_arc_ending"]
            ch = Chapter(
                project_id=project_id, volume_id=volume_id,
                chapter_number=snapshot["start_chapter_number"] + idx,
                title=node_data.get("title", ""),
                summary=_serialize_summary(node_data.get("summary", "")),
                connects_from=connects_from,
                connects_to=_safe_str(node_data.get("connects_to", "")),
                story_state_snapshot=_serialize_snapshot(node_data.get("opening_state", node_data.get("blueprint", ""))),
                arc_name=snapshot["arc_name"],
                characters_in_chapter=node_data.get("characters_in_chapter", []),
                key_events=node_data.get("key_events", []),
                minor_events=node_data.get("minor_events", []),
                scene_count=node_data.get("scene_count", 3),
                blueprint={
                    "opening_state": node_data.get("connects_from", ""),
                    "summary": node_data.get("summary", ""),
                    "scene_beats": node_data.get("scene_beats", []),
                    "ending_hook": node_data.get("connects_to", ""),
                    "must_include": node_data.get("key_events", []),
                    "foreshadowing_tasks": node_data.get("minor_events", []),
                    "rhythm_profile": {
                        "tension": node_data.get("tension_level", 5),
                        "emotion": node_data.get("emotion_intensity", 5),
                        "action": node_data.get("action_density", 5),
                        "reveal": node_data.get("information_reveal", 5),
                        "relationship": node_data.get("relationship_change", 5),
                    },
                    "arc_bridge_context": snapshot["previous_arc_ending"] if idx == 0 and arc_index > 0 else "",
                },
                foreshadowing_tasks=node_data.get("minor_events", []),
                rhythm_profile={"tension": node_data.get("tension_level", 5)},
                target_words=snapshot["default_chapter_words"],
                narrative_line=_normalize_narrative_line(node_data.get("narrative_line", "main")),
                tension_actual=node_data.get("tension_level", 5),
                status="planned",
            )
            db.add(ch)

        await db.flush()
        await _normalize_volume_arc_chapters(db, volume)
        await _refresh_volume_arc_bridges(db, volume)
        await db.commit()
        return {"chapter_count": len(nodes), "chapters": nodes}


async def _do_generate_volumes(project_id: str) -> dict:
    async with async_session() as db:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        await _clear_project_volumes(db, project_id)
        await db.commit()
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = ", ".join([f"{c.name}({c.role_type})" for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = ", ".join([f"{f.name}({f.faction_type})" for f in facs_result.scalars().all()])

        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "story_brief": _wizard_story_brief(project),
            "core_theme": project.core_theme,
            "target_total_words": project.target_total_words,
        }

    ai = AIService()
    data = await ai.generate_outline_plan(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], snapshot["target_total_words"], chars_summary, facs_summary)
    volume_data = data.get("volumes", []) if isinstance(data.get("volumes"), list) else []
    for idx, vdata in enumerate(volume_data):
        if not isinstance(vdata, dict) or not _volume_outline_needs_completion(vdata.get("outline", "")):
            continue
        neighbors = []
        if idx > 0 and isinstance(volume_data[idx - 1], dict):
            neighbors.append({
                "position": "previous",
                "title": volume_data[idx - 1].get("title", ""),
                "summary": volume_data[idx - 1].get("summary", ""),
                "cliffhanger": volume_data[idx - 1].get("volume_cliffhanger", ""),
            })
        if idx + 1 < len(volume_data) and isinstance(volume_data[idx + 1], dict):
            neighbors.append({
                "position": "next",
                "title": volume_data[idx + 1].get("title", ""),
                "summary": volume_data[idx + 1].get("summary", ""),
                "mission": volume_data[idx + 1].get("narrative_mission", ""),
            })
        expanded = await ai.expand_volume_outline(
            snapshot["title"],
            snapshot["genre"],
            snapshot["story_brief"],
            snapshot["core_theme"],
            chars_summary,
            facs_summary,
            data.get("narrative_engine", {}),
            vdata,
            neighbors,
        )
        outline = expanded.get("outline") if isinstance(expanded, dict) else ""
        if outline and not _volume_outline_needs_completion(outline):
            vdata["outline"] = outline

    async with _get_outline_write_lock(project_id):
      async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        await _clear_project_volumes(db, project_id)
        project.story_brief = project.story_brief or ""
        if data.get("story_overview"):
            project.story_brief = project.story_brief + "\n\n【全书大纲】\n" + data["story_overview"]
        if data.get("narrative_engine"):
            style = {**(project.writing_style or {})}
            style["narrative_engine"] = data["narrative_engine"]
            project.writing_style = style
        else:
            style = {**(project.writing_style or {})}
            project.writing_style = style

        for fdata in data.get("foreshadowing", []):
            db.add(ForeshadowingPlan(project_id=project_id, name=fdata.get("name", ""), description=fdata.get("description", ""), plant_stage=fdata.get("plant_stage", ""), reveal_stage=fdata.get("reveal_stage", ""), plant_chapter=0))

        for edata in data.get("key_events", []):
            db.add(TimelineEvent(project_id=project_id, description=edata.get("description", ""), event_type=edata.get("event_type", "event"), is_major_event=edata.get("is_major", False), time_point=edata.get("time_point", "")))

        chapter_num = 1
        volume_data = data.get("volumes", [])
        seen = set()
        deduped = []
        for vd in volume_data:
            vn = vd.get("volume_number", 0)
            if vn in seen:
                break
            seen.add(vn)
            deduped.append(vd)

        for i, vdata in enumerate(deduped):
            vol_chapter_count = vdata.get("chapter_count", 30)
            volume = Volume(project_id=project_id, sort_order=i,
                volume_number=i + 1,
                title=vdata.get("title", f"第{i+1}卷"),
                summary=vdata.get("summary", ""),
                theme=vdata.get("theme", ""),
                outline=vdata.get("outline", ""),
                target_words=vdata.get("target_words", project.target_total_words // max(1, len(data.get("volumes", [1])))),
                default_chapter_words=vdata.get("default_chapter_words", 3500),
                chapter_count=vol_chapter_count,
                chapter_range_start=chapter_num,
                chapter_range_end=chapter_num + vol_chapter_count - 1,
                emotional_arc_description=vdata.get("emotional_arc_description", ""),
            )
            db.add(volume)
            await db.flush()
            chapter_num += vol_chapter_count

        project.wizard_step = 4
        await db.commit()
        return {"volume_count": len(data.get("volumes", [])), "chapter_count": chapter_num - 1, "story_overview": data.get("story_overview", "")}


async def _do_review_project_structure(project_id: str) -> dict:
    async with async_session() as db:
        bible = await build_story_bible(db, project_id)
        ai = AIService()
        structure_payload = {
            "project": bible.get("project", {}),
            "world": bible.get("world", {}),
            "characters": bible.get("characters", []),
            "factions": bible.get("factions", []),
            "timeline": bible.get("timeline", []),
            "foreshadowing": bible.get("foreshadowing", []),
            "volumes": bible.get("volumes", []),
        }
        return await ai._ask(
            """
你是小说总结构审计师。请评估整部作品的完整性、因果链、主题闭环、伏笔回收、角色弧光和卷间连续性。

故事结构数据：
{structure}

返回 JSON：
{{
  "overall_score": 1-10,
  "summary": "总体意见",
  "structure_issues": [{{"dimension":"...","severity":"...","description":"...","fix_suggestion":"..."}}],
  "missing_payoffs": ["..."],
  "weak_volumes": ["..."],
  "recommended_rewrites": ["..."],
  "next_actions": ["..."]
}}
            """,
            system=SYSTEM_EDITOR,
            max_tokens=8192,
            structure=json.dumps(structure_payload, ensure_ascii=False),
        )


def _chapter_outline_payload(ch: Chapter) -> dict:
    content = ch.content or ""
    return {
        "id": str(ch.id),
        "chapter_number": ch.chapter_number,
        "title": ch.title or "",
        "arc_name": ch.arc_name or "",
        "summary": _clip_text(ch.summary or "", 800),
        "connects_from": _clip_text(ch.connects_from or "", 500),
        "connects_to": _clip_text(ch.connects_to or "", 500),
        "hook": _clip_text(ch.hook or "", 500),
        "has_content": bool(content),
        "word_count": ch.word_count or len(content),
        "content_head": _clip_text(content[:700], 700) if content else "",
        "content_tail": _clip_text(content[-900:], 900) if content else "",
        "blueprint": ch.blueprint or {},
        "key_events": ch.key_events or [],
        "minor_events": ch.minor_events or [],
        "story_state_snapshot": _clip_text(ch.story_state_snapshot or "", 1000),
    }


def _merge_arc_patch(existing_arc: dict, patch: dict) -> dict:
    arc = dict(existing_arc or {})
    for key in [
        "name", "description", "tension_curve", "key_milestones", "narrative_function",
        "emotional_color", "dependence_on_previous", "payoff_for_next",
    ]:
        if key in patch and patch.get(key) not in (None, "", [], {}):
            arc[key] = patch.get(key)
    return arc


async def _do_adjust_outline(project_id: str, volume_id: str, body: AdjustOutlineRequest, task_id: str = "") -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not project or not volume:
            raise RuntimeError("卷不存在")
        chapters = (await db.execute(
            select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id).order_by(Chapter.chapter_number)
        )).scalars().all()

        arcs = volume.narrative_arcs or []
        scoped_chapters = chapters
        scoped_arc = None
        if body.arc_index is not None and 0 <= body.arc_index < len(arcs):
            scoped_arc = arcs[body.arc_index]
            scoped_chapters = [ch for ch in chapters if ch.arc_name == scoped_arc.get("name", "")]

        payload = {
            "volume": {
                "id": str(volume.id),
                "volume_number": volume.volume_number,
                "title": volume.title,
                "summary": volume.summary,
                "outline": volume.outline,
                "theme": volume.theme,
                "emotional_arc_description": volume.emotional_arc_description,
                "narrative_arcs": arcs if scoped_arc is None else [scoped_arc],
            },
            "scope": "arc" if scoped_arc is not None else "volume",
            "adjust_scope": body.adjust_scope,
            "arc_index": body.arc_index,
            "chapters": [_chapter_outline_payload(ch) for ch in scoped_chapters],
            "written_chapter_numbers": [ch.chapter_number for ch in scoped_chapters if ch.content],
            "unwritten_chapter_numbers": [ch.chapter_number for ch in scoped_chapters if not ch.content],
        }

    if task_id:
        update_progress(task_id, 0.1, "正在分析已写正文与当前大纲", {
            "stage": "analyzing",
            "volume_id": volume_id,
            "arc_index": body.arc_index,
        })

    ai = AIService()
    result = await ai.adjust_outline(
        project.title,
        project.genre,
        _wizard_story_brief(project),
        project.core_theme or "",
        body.instruction,
        payload,
    )

    if task_id:
        update_progress(task_id, 0.75, "AI 已生成大纲调整方案，正在写入", {
            "stage": "applying" if body.apply else "preview",
            "warnings": result.get("warnings", []),
        })

    applied = {"volume": False, "arcs": 0, "chapters": 0}
    if body.apply:
        async with async_session() as db:
            volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
            if not volume:
                raise RuntimeError("卷不存在")
            volume_patch = result.get("volume_patch") or {}
            volume_keys = ["summary"] if body.adjust_scope == "summary_only" else ["title", "summary", "outline", "theme", "emotional_arc_description"]
            for key in volume_keys:
                value = volume_patch.get(key)
                if value not in (None, "", [], {}):
                    setattr(volume, key, value)
                    applied["volume"] = True

            if body.adjust_scope == "summary_only":
                await db.commit()
                if task_id:
                    update_progress(task_id, 1, "卷故事大概调整完成", {
                        "stage": "completed",
                        "applied": applied,
                        "warnings": result.get("warnings", []),
                    })
                return {**result, "applied": applied}

            current_arcs = [dict(a) for a in (volume.narrative_arcs or [])]
            for arc_patch in result.get("arcs") or []:
                if not isinstance(arc_patch, dict):
                    continue
                idx = arc_patch.get("index")
                if not isinstance(idx, int) and isinstance(idx, str) and idx.isdigit():
                    idx = int(idx)
                if isinstance(idx, int) and 0 <= idx < len(current_arcs):
                    current_arcs[idx] = _merge_arc_patch(current_arcs[idx], arc_patch)
                    applied["arcs"] += 1
            if applied["arcs"]:
                volume.narrative_arcs = current_arcs

            chapter_by_number = {
                ch.chapter_number: ch for ch in (await db.execute(
                    select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id)
                )).scalars().all()
            }
            for chapter_patch in result.get("chapters") or []:
                if not isinstance(chapter_patch, dict):
                    continue
                chapter_number = chapter_patch.get("chapter_number")
                if not isinstance(chapter_number, int) and isinstance(chapter_number, str) and chapter_number.isdigit():
                    chapter_number = int(chapter_number)
                chapter = chapter_by_number.get(chapter_number)
                if not chapter:
                    continue
                for key in ["title", "summary", "connects_from", "connects_to"]:
                    value = chapter_patch.get(key)
                    if value not in (None, "", [], {}):
                        setattr(chapter, key, value)
                for key in ["key_events", "minor_events"]:
                    value = chapter_patch.get(key)
                    if isinstance(value, list):
                        setattr(chapter, key, value)
                blueprint = chapter_patch.get("blueprint")
                if isinstance(blueprint, dict) and blueprint:
                    chapter.blueprint = blueprint
                    chapter.rhythm_profile = blueprint.get("rhythm_profile", chapter.rhythm_profile or {})
                    chapter.foreshadowing_tasks = blueprint.get("foreshadowing_tasks", chapter.foreshadowing_tasks or [])
                    chapter.scene_count = len(blueprint.get("scene_beats", [])) if isinstance(blueprint.get("scene_beats"), list) else chapter.scene_count
                applied["chapters"] += 1
            await db.commit()

    if task_id:
        update_progress(task_id, 1, "大纲调整完成", {
            "stage": "completed",
            "applied": applied,
            "warnings": result.get("warnings", []),
        })
    return {**result, "applied": applied}


async def _do_adjust_outline_chat(project_id: str, volume_id: str, body: AdjustOutlineChatRequest, task_id: str = "") -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not project or not volume:
            raise RuntimeError("卷不存在")
        chapters = (await db.execute(
            select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id).order_by(Chapter.chapter_number)
        )).scalars().all()

        arcs = volume.narrative_arcs or []
        scoped_chapters = chapters
        scoped_arc = None
        if body.arc_index is not None and 0 <= body.arc_index < len(arcs):
            scoped_arc = arcs[body.arc_index]
            scoped_chapters = [ch for ch in chapters if ch.arc_name == scoped_arc.get("name", "")]

        payload = {
            "volume": {
                "id": str(volume.id),
                "volume_number": volume.volume_number,
                "title": volume.title,
                "summary": volume.summary,
                "outline": volume.outline,
                "theme": volume.theme,
                "emotional_arc_description": volume.emotional_arc_description,
                "narrative_arcs": arcs if scoped_arc is None else [scoped_arc],
            },
            "scope": "arc" if scoped_arc is not None else "volume",
            "adjust_scope": body.adjust_scope,
            "arc_index": body.arc_index,
            "chapters": [_chapter_outline_payload(ch) for ch in scoped_chapters],
            "written_chapter_numbers": [ch.chapter_number for ch in scoped_chapters if ch.content],
            "unwritten_chapter_numbers": [ch.chapter_number for ch in scoped_chapters if not ch.content],
        }

    if task_id:
        update_progress(task_id, 0.3, "AI 正在理解你的调整意见", {
            "stage": "chatting",
            "volume_id": volume_id,
            "adjust_scope": body.adjust_scope,
        })

    ai = AIService()
    result = await ai.chat_adjust_outline(
        project.title,
        project.genre,
        _wizard_story_brief(project),
        project.core_theme or "",
        body.messages,
        body.adjust_scope,
        payload,
    )
    if task_id:
        update_progress(task_id, 1, "调整意见已整理", {"stage": "completed"})
    return result


async def _do_generate_outline_draft(project_id: str) -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = ", ".join([f"{c.name}({c.role_type})" for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = ", ".join([f"{f.name}({f.faction_type})" for f in facs_result.scalars().all()])
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "story_brief": _wizard_story_brief(project),
            "core_theme": project.core_theme,
            "target_total_words": project.target_total_words,
        }
    ai = AIService()
    return await ai.generate_outline_plan(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], snapshot["target_total_words"], chars_summary, facs_summary)


async def _do_generate_story_bible(project_id: str) -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        ws = (await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))).scalar_one_or_none()
        if not ws:
            ws = WorldSetting(project_id=project_id)
            db.add(ws)
            await db.flush()
        defaults = _world_rule_defaults_from_project(project)
        changed = False
        for key in ["hard_rules", "tone_rules", "constraints"]:
            if not getattr(ws, key, None) and defaults.get(key):
                setattr(ws, key, defaults[key])
                changed = True
        if changed:
            await db.commit()
        return await build_story_bible(db, project_id)


class ExpandVolumeArcsRequest(BaseModel):
    arc_strategy: str = "标准长篇策划"
    arc_density: str = "标准弧线"
    style_focus: str = "主线清晰，角色自然成长"
    length_control: str = "按全书体量和本卷复杂度自主判断"
    clear_existing_chapters: bool = False


@router.post("/expand-volume-arcs/{volume_id}")
async def expand_volume_arcs(project_id: str, volume_id: str, body: ExpandVolumeArcsRequest | None = None, user: User = Depends(get_current_user)):
    body = body or ExpandVolumeArcsRequest()
    task_id = start_task(
        _do_expand_volume_arcs(project_id, volume_id, body.arc_strategy, body.arc_density, body.style_focus, body.length_control, body.clear_existing_chapters),
        "expand_volume_arcs",
        project_id,
        {
            "volume_id": volume_id,
            "arc_strategy": body.arc_strategy,
            "arc_density": body.arc_density,
            "style_focus": body.style_focus,
            "length_control": body.length_control,
            "clear_existing_chapters": body.clear_existing_chapters,
        },
    )
    return {"task_id": task_id}


class ExpandArcRequest(BaseModel):
    arc_index: int = 0
    pacing: str = "medium"
    event_density: str = "medium"
    expansion_scale: str = "standard"
    chapter_ids: list[str] | None = None
    readability_mode: str = "easy"


class ReviseVolumeArcRequest(BaseModel):
    arc_index: int = 0
    action: str = "重写"
    instruction: str = ""
    regenerate_chapters: bool = False


@router.post("/expand-arc-chapters/{volume_id}")
async def expand_arc_chapters(project_id: str, volume_id: str, body: ExpandArcRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_expand_arc_chapters(project_id, volume_id, body.arc_index, body.pacing, body.event_density, body.expansion_scale),
        "expand_arc_chapters",
        project_id,
        {
            "volume_id": volume_id,
            "arc_index": body.arc_index,
            "pacing": body.pacing,
            "event_density": body.event_density,
            "expansion_scale": body.expansion_scale,
        },
    )
    return {"task_id": task_id}


@router.post("/revise-volume-arc/{volume_id}")
async def revise_volume_arc(project_id: str, volume_id: str, body: ReviseVolumeArcRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_revise_volume_arc(project_id, volume_id, body.arc_index, body.action, body.instruction, body.regenerate_chapters),
        "revise_volume_arc",
        project_id,
        {
            "volume_id": volume_id,
            "arc_index": body.arc_index,
            "action": body.action,
            "instruction": body.instruction,
            "regenerate_chapters": body.regenerate_chapters,
        },
        timeout=2 * 60 * 60,
    )
    return {"task_id": task_id}


@router.post("/batch-write-arc/{volume_id}")
async def batch_write_arc(project_id: str, volume_id: str, body: ExpandArcRequest, user: User = Depends(get_current_user)):
    import uuid as _uuid
    task_id = str(_uuid.uuid4())
    controls = {"readability_mode": body.readability_mode}
    start_task(
        _do_batch_write_arc(project_id, volume_id, body.arc_index, task_id, body.chapter_ids, body.readability_mode, controls),
        "batch_write_arc",
        project_id,
        {"volume_id": volume_id, "arc_index": body.arc_index, "chapter_ids": body.chapter_ids or [], "readability_mode": body.readability_mode, "controls": controls},
        task_id=task_id,
        timeout=BATCH_WRITE_ARC_TIMEOUT_SECONDS,
    )
    return {"task_id": task_id}


@router.post("/write-chapter/{chapter_id}")
async def write_chapter(project_id: str, chapter_id: str, body: WriteChapterRequest | None = None, user: User = Depends(get_current_user)):
    body = body or WriteChapterRequest()
    task_id = start_task(
        _do_write_chapter(project_id, chapter_id, body.mode, body.instruction, body.controls, body.preview),
        "write_chapter",
        project_id,
        {"chapter_id": chapter_id, "mode": body.mode, "instruction": body.instruction, "controls": body.controls, "preview": body.preview},
    )
    return {"task_id": task_id}


@router.post("/split-chapter/{chapter_id}")
async def split_chapter(project_id: str, chapter_id: str, body: SplitChapterRequest | None = None, user: User = Depends(get_current_user)):
    body = body or SplitChapterRequest()
    task_id = start_task(
        _do_split_chapter(project_id, chapter_id, body),
        "split_chapter",
        project_id,
        {"chapter_id": chapter_id, "target_words": body.target_words, "apply": body.apply},
        timeout=60 * 60,
    )
    return {"task_id": task_id}


@router.post("/generate-outline")
async def generate_outline(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_volumes(project_id), "generate_outline", project_id)
    return {"task_id": task_id}


@router.post("/generate-outline-draft")
async def generate_outline_draft(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_outline_draft(project_id), "generate_outline_draft", project_id)
    return {"task_id": task_id}


@router.post("/generate-story-bible")
async def generate_story_bible(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_story_bible(project_id), "generate_story_bible", project_id)
    return {"task_id": task_id}


class AuditChapterRequest(BaseModel):
    chapter_id: str


@router.post("/audit-chapter/{chapter_id}")
async def audit_chapter(project_id: str, chapter_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_audit_chapter(project_id, chapter_id), "audit_chapter", project_id, {"chapter_id": chapter_id})
    return {"task_id": task_id}


@router.get("/narrative-graph/{volume_id}")
async def narrative_graph(project_id: str, volume_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
    if not volume:
        raise HTTPException(404, "卷不存在")

    chapters = (await db.execute(
        select(Chapter).where(Chapter.volume_id == volume_id).order_by(Chapter.chapter_number)
    )).scalars().all()

    arcs = volume.narrative_arcs or []

    nodes = []
    for ch in chapters:
        arc = next((a for a in arcs if a.get("name") == ch.arc_name), None)
        nodes.append({
            "id": str(ch.id),
            "chapter_number": ch.chapter_number,
            "title": ch.title or f"第{ch.chapter_number}章",
            "summary": ch.summary,
            "arc_name": ch.arc_name,
            "narrative_function": arc.get("narrative_function", "") if arc else "",
            "emotional_color": arc.get("emotional_color", "") if arc else "",
            "key_events": ch.key_events or [],
            "minor_events": ch.minor_events or [],
            "characters_in_chapter": ch.characters_in_chapter or [],
            "connects_from": ch.connects_from,
            "connects_to": ch.connects_to,
            "hook": ch.hook,
            "tension_level": ch.tension_actual or 5,
            "scene_count": ch.scene_count or 0,
            "has_content": bool(ch.content),
            "word_count": ch.word_count or 0,
            "is_key_chapter": ch.narrative_line == "main" and (ch.tension_actual or 5) >= 7,
        })

    arc_list = []
    for a in arcs:
        arc_chapters = [n for n in nodes if n["arc_name"] == a.get("name")]
        arc_list.append({
            "name": a.get("name", ""),
            "narrative_function": a.get("narrative_function", ""),
            "emotional_color": a.get("emotional_color", ""),
            "tension_curve": a.get("tension_curve", ""),
            "chapters": arc_chapters,
        })

    return {
        "volume_title": volume.title,
        "arcs": arc_list,
        "all_chapters": nodes,
    }


@router.post("/normalize-volume-chapters/{volume_id}")
async def normalize_volume_chapters(project_id: str, volume_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
    if not volume:
        raise HTTPException(404, "卷不存在")
    await _normalize_volume_arc_chapters(db, volume)
    await _refresh_volume_arc_bridges(db, volume)
    await db.commit()
    return {"ok": True}


@router.post("/review-arc/{volume_id}")
async def review_arc(project_id: str, volume_id: str, body: ExpandArcRequest, user: User = Depends(get_current_user)):
    task_id = start_task(_do_review_arc(project_id, volume_id, body.arc_index), "review_arc", project_id, {"volume_id": volume_id, "arc_index": body.arc_index})
    return {"task_id": task_id}


@router.post("/review-volume/{volume_id}")
async def review_volume(project_id: str, volume_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_review_volume(project_id, volume_id), "review_volume", project_id, {"volume_id": volume_id})
    return {"task_id": task_id}


@router.post("/repair-from-review/{volume_id}")
async def repair_from_review(project_id: str, volume_id: str, body: RepairFromReviewRequest, user: User = Depends(get_current_user)):
    task_id = str(uuid.uuid4())
    start_task(
        _do_repair_from_review(project_id, volume_id, body, task_id),
        "repair_from_review",
        project_id,
        {
            "volume_id": volume_id,
            "apply": body.apply,
            "reaudit": body.reaudit,
            "review_result": body.review_result,
            "review_scope": body.review_scope,
            "resume_chapters": body.resume_chapters,
        },
        task_id=task_id,
        timeout=BATCH_WRITE_ARC_TIMEOUT_SECONDS,
    )
    return {"task_id": task_id}


@router.post("/review-project-structure")
async def review_project_structure(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_review_project_structure(project_id), "review_project_structure", project_id)
    return {"task_id": task_id}


@router.post("/adjust-outline/{volume_id}")
async def adjust_outline(project_id: str, volume_id: str, body: AdjustOutlineRequest, user: User = Depends(get_current_user)):
    task_id = str(uuid.uuid4())
    task_id = start_task(
        _do_adjust_outline(project_id, volume_id, body, task_id),
        "adjust_outline",
        project_id,
        {"volume_id": volume_id, "arc_index": body.arc_index, "apply": body.apply, "instruction": body.instruction},
        task_id=task_id,
        timeout=60 * 60,
    )
    return {"task_id": task_id}


@router.post("/adjust-outline-chat/{volume_id}")
async def adjust_outline_chat(project_id: str, volume_id: str, body: AdjustOutlineChatRequest, user: User = Depends(get_current_user)):
    task_id = str(uuid.uuid4())
    task_id = start_task(
        _do_adjust_outline_chat(project_id, volume_id, body, task_id),
        "adjust_outline_chat",
        project_id,
        {"volume_id": volume_id, "arc_index": body.arc_index, "adjust_scope": body.adjust_scope, "messages": body.messages},
        task_id=task_id,
        timeout=30 * 60,
    )
    return {"task_id": task_id}


@router.post("/revise-chapter/{chapter_id}")
async def revise_chapter(project_id: str, chapter_id: str, body: ReviseChapterRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_revise_chapter(project_id, chapter_id, body),
        "revise_chapter",
        project_id,
        {"chapter_id": chapter_id, "mode": body.mode, "instruction": body.instruction, "selection": body.selection, "controls": body.controls, "apply": body.apply},
    )
    return {"task_id": task_id}


@router.post("/extract-state/{chapter_id}")
async def extract_state(project_id: str, chapter_id: str, apply: bool = False, user: User = Depends(get_current_user)):
    task_id = start_task(_do_extract_state(project_id, chapter_id, apply), "extract_state", project_id, {"chapter_id": chapter_id, "apply": apply})
    return {"task_id": task_id}


@router.post("/apply-draft")
async def apply_draft(project_id: str, body: ApplyDraftRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    if body.draft_type == "world":
        ws = (await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))).scalar_one_or_none()
        if not ws:
            ws = WorldSetting(project_id=project_id)
            db.add(ws)
        for key in ["geography", "social_structure", "power_system", "history", "culture", "special_rules", "world_logic"]:
            if key in body.payload:
                setattr(ws, key, body.payload[key])
        defaults = _world_rule_defaults_from_project(project)
        for key in ["hard_rules", "tone_rules", "constraints"]:
            if key in body.payload:
                setattr(ws, key, _as_string_list(body.payload.get(key), 12))
            elif not getattr(ws, key, None):
                setattr(ws, key, defaults.get(key, []))
        await db.flush()
        return {"success": True}

    if body.draft_type == "characters":
        existing_characters = (await db.execute(select(Character).where(Character.project_id == project_id))).scalars().all()
        existing_factions = (await db.execute(select(Faction).where(Faction.project_id == project_id))).scalars().all()
        character_by_name = {_normalize_entity_name(c.name): c for c in existing_characters if _normalize_entity_name(c.name)}
        faction_by_name = {_normalize_entity_name(f.name): f for f in existing_factions if _normalize_entity_name(f.name)}
        seen_char_names = set()
        for cdata in body.payload.get("characters", []):
            key = _normalize_entity_name(cdata.get("name") if isinstance(cdata, dict) else "")
            if not key or key in seen_char_names:
                continue
            seen_char_names.add(key)
            await _upsert_character(db, project_id, cdata, character_by_name)
        seen_faction_names = set()
        for fdata in body.payload.get("factions", []):
            key = _normalize_entity_name(fdata.get("name") if isinstance(fdata, dict) else "")
            if not key or key in seen_faction_names:
                continue
            seen_faction_names.add(key)
            await _upsert_faction(db, project_id, fdata, faction_by_name)
        await db.flush()
        return {"success": True}

    raise HTTPException(400, "不支持的草稿类型")


async def _do_audit_chapter(project_id: str, chapter_id: str) -> dict:
    async with async_session() as db:
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if not chapter or not chapter.content:
            raise RuntimeError("章节不存在或未写入")

        prev_chapter = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)

        previous_ending = "无"
        previous_hook = ""
        if prev_chapter and prev_chapter.content:
            ending = prev_chapter.content[-500:] if len(prev_chapter.content) > 500 else prev_chapter.content
            previous_ending = ending
            previous_hook = prev_chapter.hook or ""
        elif chapter.connects_from:
            previous_ending = chapter.connects_from

        snapshot = chapter.story_state_snapshot or _build_story_state_snapshot(chapter, "")

        ai = AIService()
        result = await ai.audit_chapter(previous_ending, previous_hook, snapshot, chapter.content)
        if isinstance(result, dict):
            chapter.quality_score = int(result.get("overall_score") or 0) or chapter.quality_score
            checks = chapter.continuity_checks or {}
            checks["quality_review"] = result
            chapter.continuity_checks = checks
            await db.commit()
        return result


async def _do_review_arc(project_id: str, volume_id: str, arc_index: int) -> dict:
    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("请先生成弧线和章节")
        arc = volume.narrative_arcs[arc_index]
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()

        chapters = (await db.execute(
            select(Chapter).where(Chapter.volume_id == volume_id, Chapter.arc_name == arc.get("name", "")).order_by(Chapter.chapter_number)
        )).scalars().all()

        if not chapters:
            raise RuntimeError("该弧线无章节")

        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = "\n".join([_build_character_profile(c) for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs_result.scalars().all()])

        chapters_content_parts = []
        for ch in chapters:
            if ch.content:
                chapters_content_parts.append(f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n摘要：{ch.summary or '无'}\n正文前300字：{(ch.content[:300] if ch.content else '无')}\n正文后500字：{(ch.content[-500:] if len(ch.content) > 500 else ch.content) if ch.content else '无'}")
            else:
                chapters_content_parts.append(f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n状态：未写入\n摘要：{ch.summary or '无'}")
        chapters_content = "\n\n".join(chapters_content_parts)

        review_scope = f"弧线「{arc.get('name', '')}」共{len(chapters)}章"
        ai = AIService()
        result = await ai.review_chapters(
            project.title, project.genre, _wizard_story_brief(project),
            chars_summary, facs_summary,
            review_scope, chapters_content,
        )
        return result


async def _do_review_volume(project_id: str, volume_id: str) -> dict:
    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume:
            raise RuntimeError("卷不存在")
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()

        chapters = (await db.execute(
            select(Chapter).where(Chapter.volume_id == volume_id).order_by(Chapter.chapter_number)
        )).scalars().all()

        if not chapters:
            raise RuntimeError("该卷无章节")

        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = "\n".join([_build_character_profile(c) for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs_result.scalars().all()])

        chapters_content_parts = []
        for ch in chapters:
            if ch.content:
                chapters_content_parts.append(f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n摘要：{ch.summary or '无'}\n正文前300字：{(ch.content[:300] if ch.content else '无')}\n正文后500字：{(ch.content[-500:] if len(ch.content) > 500 else ch.content) if ch.content else '无'}")
            else:
                chapters_content_parts.append(f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n状态：未写入\n摘要：{ch.summary or '无'}")
        chapters_content = "\n\n".join(chapters_content_parts)

        review_scope = f"卷「{volume.title}」共{len(chapters)}章"
        ai = AIService()
        result = await ai.review_chapters(
            project.title, project.genre, _wizard_story_brief(project),
            chars_summary, facs_summary,
            review_scope, chapters_content,
        )
        return result


def _review_chapter_number(item: dict) -> int | None:
    chapter = item.get("chapter")
    if isinstance(chapter, int):
        return chapter
    if isinstance(chapter, str):
        digits = re.findall(r"\d+", chapter)
        if digits:
            return int(digits[0])
    chapter = item.get("chapter_number")
    if isinstance(chapter, int):
        return chapter
    if isinstance(chapter, str):
        digits = re.findall(r"\d+", chapter)
        if digits:
            return int(digits[0])
    evidence = item.get("evidence", "")
    if isinstance(evidence, str):
        digits = re.findall(r"第\s*(\d+)\s*章", evidence)
        if digits:
            return int(digits[0])
    return None


def _normalize_review_issues(review_result: dict) -> list[dict]:
    issues = []
    for key in ("critical_issues", "high_issues", "low_issues"):
        items = review_result.get(key) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                issue = dict(item)
                issue["priority"] = "critical" if key == "critical_issues" else "high" if key == "high_issues" else "medium"
                issue["chapter_number"] = _review_chapter_number(issue)
                issues.append(issue)
    if not issues:
        for item in review_result.get("issues") or []:
            if isinstance(item, dict):
                issue = dict(item)
                severity = (issue.get("severity") or "").lower()
                issue["priority"] = "critical" if severity in {"critical", "致命"} else "high" if severity in {"high", "严重"} else "medium"
                issue["chapter_number"] = _review_chapter_number(issue)
                issues.append(issue)
    return issues


async def _build_review_chapter_index(db: AsyncSession, project_id: str, volume_id: str) -> list[dict]:
    chapters = (await db.execute(
        select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id).order_by(Chapter.chapter_number)
    )).scalars().all()
    return [
        {
            "chapter_number": ch.chapter_number,
            "chapter_id": str(ch.id),
            "title": ch.title or "",
            "arc_name": ch.arc_name or "",
            "summary": ch.summary or "",
            "has_content": bool(ch.content),
        }
        for ch in chapters
    ]


async def _do_repair_from_review(project_id: str, volume_id: str, body: RepairFromReviewRequest, task_id: str = "") -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not project or not volume:
            raise RuntimeError("卷不存在")

        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars = chars_result.scalars().all()
        chars_summary = "\n".join([_build_character_profile(c) for c in chars])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs = facs_result.scalars().all()
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs])
        chapter_index = await _build_review_chapter_index(db, project_id, volume_id)

    review_result = body.review_result or {}
    issues = _normalize_review_issues(review_result)
    review_scope = body.review_scope or f"卷「{volume.title}」"
    ai = AIService()
    repair_plan = await ai.plan_review_repair(
        project.title, project.genre, _wizard_story_brief(project),
        chars_summary, facs_summary,
        review_scope, review_result, chapter_index,
    )
    tasks = repair_plan.get("tasks") or []
    if not isinstance(tasks, list) or not tasks:
        tasks = [
            {
                "chapter": issue.get("chapter_number"),
                "priority": issue.get("priority", "medium"),
                "issue_type": issue.get("dimension", issue.get("severity", "其他")),
                "issue_summary": issue.get("description", ""),
                "canon_to_keep": [],
                "changes_required": [issue.get("fix_suggestion", "")],
                "bridge_to_previous": "",
                "bridge_to_next": "",
                "must_not_do": [],
                "verification_points": [],
            }
            for issue in issues
            if issue.get("chapter_number")
        ]

    tasks = [t for t in tasks if isinstance(t, dict)]

    def _task_chapter_number(task: dict) -> int:
        chapter = task.get("chapter")
        if isinstance(chapter, int):
            return chapter
        if isinstance(chapter, str):
            digits = re.findall(r"\d+", chapter)
            if digits:
                return int(digits[0])
        return 10**9

    if body.resume_chapters:
        resume_set = {
            int(ch)
            for ch in body.resume_chapters
            if isinstance(ch, int) or (isinstance(ch, str) and ch.isdigit())
        }
        if resume_set:
            tasks = [t for t in tasks if _task_chapter_number(t) in resume_set]

    tasks.sort(key=lambda t: (0 if (t.get("priority") == "critical") else 1 if (t.get("priority") == "high") else 2, _task_chapter_number(t)))

    chapter_map = {item["chapter_number"]: item for item in chapter_index}
    if task_id:
        update_progress(task_id, 0, f"已生成修复计划：{len(tasks)} 项", {
            "stage": "planned",
            "task_count": len(tasks),
            "diagnosis": repair_plan.get("diagnosis", ""),
            "global_constraints": repair_plan.get("global_constraints", []),
        })

    repaired_chapters: list[int] = []
    async with async_session() as db:
        for idx, task in enumerate(tasks, start=1):
            chapter_number = task.get("chapter")
            if isinstance(chapter_number, str):
                digits = re.findall(r"\d+", chapter_number)
                chapter_number = int(digits[0]) if digits else None
            if not isinstance(chapter_number, int):
                continue
            chapter_meta = chapter_map.get(chapter_number)
            if not chapter_meta:
                continue
            chapter = (await db.execute(
                select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id, Chapter.chapter_number == chapter_number)
            )).scalar_one_or_none()
            if not chapter:
                continue

            prev = await _get_previous_chapter(db, project_id, volume_id, chapter.chapter_number)
            previous_ending = prev.content[-500:] if prev and prev.content else chapter.connects_from or ""
            if prev and prev.hook:
                previous_ending = f"{previous_ending}\n\n【上章钩子】{prev.hook}"

            repair_context = {
                "diagnosis": repair_plan.get("diagnosis", ""),
                "global_constraints": repair_plan.get("global_constraints", []),
                "issue_type": task.get("issue_type", ""),
                "issue_summary": task.get("issue_summary", ""),
                "canon_to_keep": task.get("canon_to_keep", []),
                "changes_required": task.get("changes_required", []),
                "must_not_do": task.get("must_not_do", []),
                "verification_points": task.get("verification_points", []),
                "bridge_to_previous": task.get("bridge_to_previous", ""),
                "bridge_to_next": task.get("bridge_to_next", ""),
            }

            if task_id:
                update_progress(task_id, idx / max(len(tasks), 1), f"正在修复第{chapter.chapter_number}章《{chapter.title or ''}》", {
                    "stage": "repairing",
                    "chapter_number": chapter.chapter_number,
                    "chapter_title": chapter.title or "",
                    "priority": task.get("priority", "medium"),
                    "issue_type": task.get("issue_type", ""),
                    "repair_context": repair_context,
                })

            result = await ai.revise_chapter(
                project.title, project.genre, chapter.chapter_number, chapter.title or "",
                chapter.summary or "", chapter.content or "", "repair",
                instruction=f"按修复计划处理：{task.get('issue_summary', '')}",
                selection="",
                previous_ending=previous_ending,
                controls={
                    "repair_task": task,
                    "global_constraints": repair_plan.get("global_constraints", []),
                    "review_scope": review_scope,
                },
                repair_context=json.dumps(repair_context, ensure_ascii=False),
            )
            new_content = result.get("content", "")
            if body.apply and new_content:
                await _save_chapter_version(db, chapter, "ai_repair", f"AI 评审修复：第{chapter.chapter_number}章", {
                    "repair_plan": repair_plan,
                    "repair_task": task,
                    "review_result": review_result,
                })
                chapter.content = new_content
                chapter.word_count = len(chapter.content or "")
                chapter.status = _status_after_content_change(chapter.status)
                chapter.version = (chapter.version or 1) + 1
                chapter.hook = result.get("hook", chapter.hook)
                with db.no_autoflush:
                    await _extract_and_apply_state(db, project_id, chapter, chapter.content)
                repaired_chapters.append(chapter.chapter_number)
                await db.commit()

        if body.reaudit and repaired_chapters:
            audited = []
            for chapter_number in repaired_chapters:
                chapter = (await db.execute(
                    select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id, Chapter.chapter_number == chapter_number)
                )).scalar_one_or_none()
                if chapter:
                    audited.append({
                        "chapter_number": chapter.chapter_number,
                        "audit": await ai.audit_chapter(
                            chapter.connects_from or "",
                            chapter.hook or "",
                            chapter.story_state_snapshot or "",
                            chapter.content or "",
                        ),
                    })
            return {
                "repair_plan": repair_plan,
                "repaired_chapters": repaired_chapters,
                "reaudit": audited,
            }

    return {
        "repair_plan": repair_plan,
        "repaired_chapters": repaired_chapters,
    }


async def _do_revise_chapter(project_id: str, chapter_id: str, body: ReviseChapterRequest) -> dict:
    async with async_session() as db:
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if not project or not chapter:
            raise RuntimeError("章节不存在")
        original_content = chapter.content or ""
        is_local_revise = body.mode in LOCAL_REVISE_MODES
        if is_local_revise:
            selection = (body.selection or "").strip()
            if not selection:
                raise RuntimeError("局部修复缺少原文定位，请先选择或定位要修复的句子/段落")
            if selection not in original_content:
                raise RuntimeError("未找到可精确替换的原文片段，请重新审计或手动选中原文后再修复")
        prev = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)
        previous_ending = prev.content[-500:] if prev and prev.content else chapter.connects_from or ""
        ai = AIService()
        controls = _merge_writing_controls(project, body.controls)
        result = await ai.revise_chapter(
            project.title, project.genre, chapter.chapter_number, chapter.title or "",
            chapter.summary or "", chapter.content or "", body.mode, body.instruction,
            body.selection, previous_ending, controls,
        )
        new_content = result.get("content", "")
        if body.apply and new_content:
            await _save_chapter_version(db, chapter, "ai_revise", f"AI 修订前备份：{body.mode}", body.model_dump())
            if body.selection and body.selection in original_content:
                chapter.content = original_content.replace(body.selection, new_content, 1)
            elif is_local_revise:
                raise RuntimeError("局部修复返回后原文定位失效，本次未写入正文")
            else:
                chapter.content = new_content
            chapter.word_count = len(chapter.content or "")
            chapter.status = _status_after_content_change(chapter.status)
            chapter.version = (chapter.version or 1) + 1
            review = await ai.audit_chapter(previous_ending, chapter.hook or "", chapter.story_state_snapshot or "", chapter.content or "")
            if isinstance(review, dict):
                chapter.quality_score = int(review.get("overall_score") or 0) or chapter.quality_score
                checks = chapter.continuity_checks or {}
                checks["quality_review"] = review
                chapter.continuity_checks = checks
                result["quality_review"] = review
            await db.commit()
        return result


async def _do_extract_state(project_id: str, chapter_id: str, apply_changes: bool = False) -> dict:
    async with async_session() as db:
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if not chapter or not chapter.content:
            raise RuntimeError("章节不存在或未写入")
        ai = AIService()
        result = await ai.extract_state_changes(chapter.chapter_number, chapter.title or "", chapter.summary or "", chapter.content)
        if apply_changes:
            chapter.story_state_snapshot = json.dumps(result, ensure_ascii=False)[:3000]
            for event in result.get("timeline_events", []):
                db.add(TimelineEvent(
                    project_id=project_id,
                    chapter_id=chapter.id,
                    time_point=event.get("time_point", f"第{chapter.chapter_number}章"),
                    description=event.get("description", ""),
                    event_type=event.get("event_type", "event"),
                    is_major_event=event.get("is_major", False),
                ))
            db.add(StoryStateTrail(
                project_id=project_id,
                chapter_id=chapter.id,
                chapter_number=chapter.chapter_number,
                state_snapshot=result,
                change_description="; ".join(result.get("next_must_follow", [])[:3]),
            ))
            await db.commit()
        return result


async def _apply_state_payload(db: AsyncSession, project_id: str, chapter: Chapter, result: dict):
    chapter.story_state_snapshot = json.dumps(result, ensure_ascii=False)[:3000]
    for event in result.get("timeline_events", []):
        db.add(TimelineEvent(
            project_id=project_id,
            chapter_id=chapter.id,
            time_point=event.get("time_point", f"第{chapter.chapter_number}章"),
            description=event.get("description", ""),
            event_type=event.get("event_type", "event"),
            is_major_event=event.get("is_major", False),
        ))
    db.add(StoryStateTrail(
        project_id=project_id,
        chapter_id=chapter.id,
        chapter_number=chapter.chapter_number,
        state_snapshot=result,
        change_description="; ".join(result.get("next_must_follow", [])[:3]),
    ))


@router.post("/apply-state/{chapter_id}")
async def apply_state(project_id: str, chapter_id: str, body: ApplyStateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    await _apply_state_payload(db, project_id, chapter, body.payload)
    await db.flush()
    return {"success": True, "state": body.payload}


@router.get("/task/{task_id}")
async def poll_task(project_id: str, task_id: str):
    t = await get_task_persisted(task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    return {
        "id": t.get("id"),
        "status": t["status"],
        "result": t.get("result"),
        "error": t.get("error"),
        "progress": t.get("progress", 0),
        "progress_label": t.get("progress_label", ""),
        "detail": t.get("detail", {}),
        "task_type": t.get("task_type"),
        "meta": t.get("meta", {}),
        "created_at": t.get("created_at"),
        "updated_at": t.get("updated_at"),
    }


@router.get("/tasks")
async def project_tasks(project_id: str, user: User = Depends(get_current_user)):
    return {"tasks": await list_tasks_persisted(project_id)}


@router.post("/cancel-task/{task_id}")
async def cancel_task_endpoint(project_id: str, task_id: str, user: User = Depends(get_current_user)):
    if cancel_task(task_id):
        return {"ok": True}
    raise HTTPException(400, "无法取消该任务")


def _task_retry_meta(task: GenerationTask) -> dict:
    config = task.precision_config or {}
    meta = dict(config.get("meta") or {})
    if task.result_summary and task.result_summary.get("result") is not None:
        meta.setdefault("task_result", task.result_summary.get("result"))
    return meta


@router.post("/retry-task/{task_id}")
async def retry_task(project_id: str, task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = (await db.execute(
        select(GenerationTask).where(GenerationTask.id == task_id, GenerationTask.project_id == project_id)
    )).scalar_one_or_none()
    if not task:
        raise HTTPException(404, "任务不存在")

    meta = _task_retry_meta(task)
    task_type = task.task_type or ""
    new_task_id = str(uuid.uuid4())

    if task_type == "batch_write_arc":
        volume_id = meta.get("volume_id")
        arc_index = meta.get("arc_index")
        if volume_id is None or arc_index is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        chapter_ids = meta.get("chapter_ids") or None
        controls = meta.get("controls") if isinstance(meta.get("controls"), dict) else {"readability_mode": meta.get("readability_mode", "easy")}
        start_task(
            _do_batch_write_arc(project_id, str(volume_id), int(arc_index), new_task_id, chapter_ids, str(meta.get("readability_mode", "easy")), controls),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
            timeout=BATCH_WRITE_ARC_TIMEOUT_SECONDS,
        )
        return {"task_id": new_task_id}

    if task_type == "repair_from_review":
        review_result = meta.get("review_result")
        volume_id = meta.get("volume_id")
        if not isinstance(review_result, dict) or not review_result:
            last_repair_version = (await db.execute(
                select(ChapterVersion)
                .where(ChapterVersion.project_id == project_id, ChapterVersion.source == "ai_repair")
                .order_by(ChapterVersion.created_at.desc())
                .limit(1)
            )).scalar_one_or_none()
            if last_repair_version and isinstance(last_repair_version.generation_config, dict):
                review_result = last_repair_version.generation_config.get("review_result")
                if not volume_id:
                    repaired_chapter = (await db.execute(
                        select(Chapter).where(Chapter.id == last_repair_version.chapter_id, Chapter.project_id == project_id)
                    )).scalar_one_or_none()
                    if repaired_chapter:
                        volume_id = str(repaired_chapter.volume_id)
        if not isinstance(review_result, dict) or not review_result:
            raise HTTPException(400, "该修复任务缺少评审结果，无法继续")
        resume_chapters = [
            int(ch)
            for ch in (meta.get("resume_chapters") or [])
            if isinstance(ch, int) or (isinstance(ch, str) and str(ch).isdigit())
        ]
        if not resume_chapters:
            detail = (task.precision_config or {}).get("detail") or {}
            current_chapter = detail.get("chapter_number")
            all_issues = [issue for issue in _normalize_review_issues(review_result) if issue.get("chapter_number")]
            if isinstance(current_chapter, int):
                resume_chapters = sorted({issue["chapter_number"] for issue in all_issues if issue["chapter_number"] >= current_chapter})
            else:
                resume_chapters = sorted({issue["chapter_number"] for issue in all_issues})
        body = RepairFromReviewRequest(
            review_result=review_result,
            review_scope=meta.get("review_scope", ""),
            apply=bool(meta.get("apply", True)),
            reaudit=bool(meta.get("reaudit", False)),
            resume_chapters=resume_chapters,
        )
        if volume_id is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_repair_from_review(project_id, str(volume_id), body, new_task_id),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
            timeout=BATCH_WRITE_ARC_TIMEOUT_SECONDS,
        )
        return {"task_id": new_task_id}

    if task_type == "expand_arc_chapters":
        volume_id = meta.get("volume_id")
        arc_index = meta.get("arc_index")
        if volume_id is None or arc_index is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_expand_arc_chapters(
                project_id,
                str(volume_id),
                int(arc_index),
                meta.get("pacing", "medium"),
                meta.get("event_density", "medium"),
                meta.get("expansion_scale", "standard"),
            ),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "expand_volume_arcs":
        volume_id = meta.get("volume_id")
        if volume_id is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_expand_volume_arcs(
                project_id,
                str(volume_id),
                meta.get("arc_strategy", "标准长篇策划"),
                meta.get("arc_density", "标准弧线"),
                meta.get("style_focus", "主线清晰，角色自然成长"),
                meta.get("length_control", "按全书体量和本卷复杂度自主判断"),
                bool(meta.get("clear_existing_chapters", False)),
            ),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "revise_volume_arc":
        volume_id = meta.get("volume_id")
        arc_index = meta.get("arc_index")
        if volume_id is None or arc_index is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_revise_volume_arc(
                project_id,
                str(volume_id),
                int(arc_index),
                meta.get("action", "重写"),
                meta.get("instruction", ""),
                bool(meta.get("regenerate_chapters", False)),
            ),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
            timeout=2 * 60 * 60,
        )
        return {"task_id": new_task_id}

    if task_type == "review_arc":
        volume_id = meta.get("volume_id")
        arc_index = meta.get("arc_index")
        if volume_id is None or arc_index is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_review_arc(project_id, str(volume_id), int(arc_index)),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "review_volume":
        volume_id = meta.get("volume_id")
        if volume_id is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_review_volume(project_id, str(volume_id)),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "review_project_structure":
        start_task(
            _do_review_project_structure(project_id),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "adjust_outline":
        volume_id = meta.get("volume_id")
        if volume_id is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        body = AdjustOutlineRequest(
            instruction=meta.get("instruction", "请根据已写内容校准后续大纲"),
            arc_index=meta.get("arc_index"),
            apply=bool(meta.get("apply", True)),
        )
        start_task(
            _do_adjust_outline(project_id, str(volume_id), body, new_task_id),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
            timeout=60 * 60,
        )
        return {"task_id": new_task_id}

    if task_type == "audit_chapter":
        chapter_id = meta.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_audit_chapter(project_id, str(chapter_id)),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "extract_state":
        chapter_id = meta.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_extract_state(project_id, str(chapter_id), bool(meta.get("apply", False))),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "revise_chapter":
        chapter_id = meta.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "该任务缺少可重试参数")
        body = ReviseChapterRequest(
            mode=meta.get("mode", "polish"),
            instruction=meta.get("instruction", ""),
            selection=meta.get("selection", ""),
            controls=meta.get("controls", {}) if isinstance(meta.get("controls", {}), dict) else {},
            apply=bool(meta.get("apply", False)),
        )
        start_task(
            _do_revise_chapter(project_id, str(chapter_id), body),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "split_chapter":
        chapter_id = meta.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "该任务缺少可重试参数")
        body = SplitChapterRequest(target_words=int(meta.get("target_words", 3500)), apply=bool(meta.get("apply", True)))
        start_task(
            _do_split_chapter(project_id, str(chapter_id), body),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "write_chapter":
        chapter_id = meta.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "该任务缺少可重试参数")
        body = WriteChapterRequest(
            mode=meta.get("mode", "append"),
            instruction=meta.get("instruction", ""),
            controls=meta.get("controls", {}) if isinstance(meta.get("controls", {}), dict) else {},
            preview=bool(meta.get("preview", False)),
        )
        start_task(
            _do_write_chapter(project_id, str(chapter_id), body.mode, body.instruction, body.controls, body.preview),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "generate_world":
        start_task(_do_generate_world(project_id), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "generate_world_draft":
        start_task(_do_generate_world_draft(project_id), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "generate_story_bible":
        start_task(_do_generate_story_bible(project_id), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "generate_outline":
        start_task(_do_generate_volumes(project_id), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "generate_outline_draft":
        start_task(_do_generate_outline_draft(project_id), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "generate_characters":
        start_task(
            _do_generate_characters(project_id, int(meta.get("char_count", 6)), int(meta.get("faction_count", 3))),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "generate_characters_draft":
        start_task(
            _do_generate_characters_draft(project_id, int(meta.get("char_count", 6)), int(meta.get("faction_count", 3))),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    raise HTTPException(400, "该任务类型暂不支持重新开始")
