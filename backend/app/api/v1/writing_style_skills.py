from datetime import datetime
import uuid
import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db, async_session
from app.models.project import Project
from app.models.user import User
from app.models.writing_style_skill import WritingStyleSkill
from app.utils.timezone import isoformat as tz_isoformat, now as tz_now
from app.services.ai_service import AIService
from app.services.task_manager import get_task_persisted, list_tasks, start_task, update_progress

router = APIRouter(tags=["writing-style-skills"])


class AnalyzeWritingStyleSkillRequest(BaseModel):
    sample_text: str
    name: str = ""
    source_note: str = ""
    save: bool = True


class UpdateWritingStyleSkillRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    style_profile: dict | None = None
    prompt_fragment: str | None = None
    is_active: bool | None = None


class ActiveWritingStyleSkillRequest(BaseModel):
    skill_id: str | None = None


def _representative_sample(text: str, limit: int = 50000) -> str:
    clean = (text or "").strip()
    if len(clean) <= limit:
        return clean
    chapter_pattern = re.compile(r"(?=第[零一二三四五六七八九十百千万\d]+[章章节回][^\n\r]{0,60})")
    pieces = [p.strip() for p in chapter_pattern.split(clean) if len(p.strip()) > 800]
    if len(pieces) >= 8:
        indexes = [0, 1, 2, len(pieces) // 5, len(pieces) // 3, len(pieces) // 2, len(pieces) * 2 // 3, len(pieces) * 4 // 5, len(pieces) - 3, len(pieces) - 2, len(pieces) - 1]
        selected = []
        seen = set()
        per_piece = max(1800, limit // max(1, len(indexes)) - 120)
        for idx in indexes:
            idx = max(0, min(len(pieces) - 1, idx))
            if idx in seen:
                continue
            seen.add(idx)
            selected.append(f"【章节样本 {idx + 1}/{len(pieces)}】\n{pieces[idx][:per_piece]}")
        return "\n\n".join(selected)[:limit]

    window_count = 10
    window_size = max(2200, limit // window_count - 100)
    selected = []
    for i in range(window_count):
        start = int((len(clean) - window_size) * i / max(1, window_count - 1))
        selected.append(f"【文本窗口 {i + 1}/{window_count}】\n{clean[start:start + window_size]}")
    return "\n\n".join(selected)[:limit]


def _decode_upload_content(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(400, "文件编码无法识别，请上传 UTF-8 或 GBK/GB18030 文本文件")


def _ensure_skill_section(profile: dict, key: str, default: dict | list | str) -> None:
    value = profile.get(key)
    if value:
        return
    profile[key] = default


def _normalize_writing_style_profile(profile: dict, name: str, sample_word_count: int) -> dict:
    profile = dict(profile or {})
    now_name = (name or profile.get("name") or "未命名写作风格").strip()[:120]
    profile["name"] = now_name
    profile.setdefault("description", "")
    profile.setdefault("core_style", profile.get("description") or "")
    profile.setdefault("avoid_rules", [])
    profile.setdefault("prompt_fragment", "")
    profile.setdefault("source_policy", {
        "abstract_only": True,
        "no_verbatim_copy": True,
        "no_plot_replication": True,
        "no_proper_nouns_from_sample": True,
    })
    profile.setdefault("sample_diagnosis", {})
    if isinstance(profile["sample_diagnosis"], dict):
        profile["sample_diagnosis"].setdefault("sample_word_count", sample_word_count)
        profile["sample_diagnosis"].setdefault("sample_strategy", "多点代表性采样：开篇 + 中段 + 后段 + 若干窗口")

    _ensure_skill_section(profile, "technique_taxonomy", {
        "summary": "待补充：人物、情绪、世界、场景、冲突、关系、细节、信息差、爽点和语言手感的技法谱系。",
        "character": [],
        "emotion": [],
        "world": [],
        "scene": [],
        "conflict": [],
        "relationship": [],
        "detail": [],
        "information_gap": [],
        "payoff": [],
        "language": [],
        "must_do": [],
        "must_not_do": [],
    })
    _ensure_skill_section(profile, "evidence_bank", [])
    _ensure_skill_section(profile, "early_retention_model", {
        "summary": "待补充：前20万字的主角立住、卖点兑现、阶段反馈和追读节奏。",
        "chapter_1": [],
        "first_3_chapters": [],
        "first_10_chapters": [],
        "first_30_chapters": [],
        "first_50_chapters": [],
        "retention_risks": [],
        "payoff_cadence": [],
    })
    _ensure_skill_section(profile, "character_voice_matrix", {
        "summary": "待补充：不同角色身份的声音边界。",
        "protagonist_inner_voice": [],
        "protagonist_spoken_voice": [],
        "close_relationship_voice": [],
        "authority_voice": [],
        "antagonist_voice": [],
        "side_character_voice": [],
        "voice_separation_rules": [],
    })
    _ensure_skill_section(profile, "scene_templates", [])
    _ensure_skill_section(profile, "length_adaptation", {
        "summary": "待补充：短篇、中篇、长篇、超长篇的适配方式。",
        "short": "",
        "medium": "",
        "long": "",
        "mega": "",
        "fatigue_control": [],
    })
    _ensure_skill_section(profile, "workflow_usage", {
        "creation": [],
        "worldbuilding": [],
        "characters": [],
        "outline": [],
        "arc": [],
        "blueprint": [],
        "writing": [],
        "audit": [],
        "repair": [],
    })
    _ensure_skill_section(profile, "deviation_checks", {
        "summary": "待补充：风格贴合、角色声音、情绪、场景、爽点和 AI 味偏离检测。",
        "style_fit": [],
        "voice_fit": [],
        "emotion_fit": [],
        "scene_fit": [],
        "payoff_fit": [],
        "ai_flavor_risks": [],
    })
    _ensure_skill_section(profile, "repair_strategies", {
        "sentence": [],
        "paragraph": [],
        "chapter_light": [],
        "chapter_rewrite": [],
        "continuity": [],
    })
    return profile


async def _build_skill_from_sample(
    *,
    user_id: str,
    sample: str,
    name: str = "",
    source_note: str = "",
    save: bool = True,
) -> dict:
    sample = (sample or "").strip()
    if len(sample) < 1000:
        raise HTTPException(400, "样本文本太短，建议至少 1000 字")
    clipped = _representative_sample(sample, 50000)
    ai = AIService()
    profile = await ai.analyze_writing_style_skill(clipped, name)
    if not isinstance(profile, dict):
        raise HTTPException(500, "AI 返回写作风格 Skill 格式异常")
    profile = _normalize_writing_style_profile(profile, name, len(sample))
    now_name = profile["name"]
    skill_payload = {
        "name": now_name,
        "description": profile.get("description") or "",
        "style_profile": profile,
        "prompt_fragment": profile.get("prompt_fragment") or "",
        "sample_word_count": len(sample),
    }
    if not save:
        return {**skill_payload, "id": None}

    async with async_session() as db:
        skill = WritingStyleSkill(
            user_id=user_id,
            name=skill_payload["name"],
            description=skill_payload["description"],
            source_type="sample",
            source_note=source_note[:500] if source_note else "",
            sample_word_count=skill_payload["sample_word_count"],
            style_profile=skill_payload["style_profile"],
            prompt_fragment=skill_payload["prompt_fragment"],
            is_active=True,
        )
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        return _skill_payload(skill)


async def _do_analyze_writing_style_skill_task(
    *,
    task_id: str,
    user_id: str,
    sample: str,
    name: str = "",
    source_note: str = "",
    save: bool = True,
) -> dict:
    update_progress(task_id, 0.08, "样本已上传，正在准备代表性采样", {
        "source_note": source_note,
        "sample_word_count": len(sample or ""),
    })
    update_progress(task_id, 0.18, "正在抽取开篇、中段、后段代表样本", {
        "sample_word_count": len(sample or ""),
        "sample_strategy": "开篇 + 中段 + 后段",
    })
    skill = await _build_skill_from_sample(
        user_id=user_id,
        sample=sample,
        name=name,
        source_note=source_note,
        save=save,
    )
    update_progress(task_id, 0.95, "写作风格 Skill 已生成，正在保存结果", {
        "skill_id": skill.get("id"),
        "skill_name": skill.get("name"),
    })
    return {"skill": skill}


def _skill_payload(skill: WritingStyleSkill) -> dict:
    return {
        "id": str(skill.id),
        "name": skill.name,
        "description": skill.description or "",
        "source_type": skill.source_type or "",
        "source_note": skill.source_note or "",
        "sample_word_count": skill.sample_word_count or 0,
        "style_profile": skill.style_profile or {},
        "prompt_fragment": skill.prompt_fragment or "",
        "is_public": bool(skill.is_public),
        "is_active": bool(skill.is_active),
        "created_at": tz_isoformat(skill.created_at) or None,
        "updated_at": tz_isoformat(skill.updated_at) or None,
    }


def _project_payload(project: Project) -> dict:
    return {
        "id": str(project.id),
        "user_id": str(project.user_id),
        "title": project.title,
        "genre": project.genre,
        "target_length": project.target_length,
        "target_total_words": project.target_total_words,
        "word_count_breakdown": project.word_count_breakdown or {},
        "story_brief": project.story_brief or "",
        "writing_style": project.writing_style or {},
        "core_theme": project.core_theme or "",
        "secondary_themes": project.secondary_themes or [],
        "motifs": project.motifs or [],
        "narrative_lines": project.narrative_lines or [],
        "wizard_step": project.wizard_step,
        "status": project.status,
        "planning_memory": project.planning_memory or {},
        "created_at": tz_isoformat(project.created_at) or None,
        "updated_at": tz_isoformat(project.updated_at) or None,
    }


@router.get("/writing-style-skills")
async def list_writing_style_skills(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WritingStyleSkill)
        .where(WritingStyleSkill.user_id == user.id, WritingStyleSkill.is_active == True)
        .order_by(WritingStyleSkill.updated_at.desc())
    )
    return {"skills": [_skill_payload(s) for s in result.scalars().all()]}


@router.post("/writing-style-skills/analyze")
async def analyze_writing_style_skill(body: AnalyzeWritingStyleSkillRequest, user: User = Depends(get_current_user)):
    skill = await _build_skill_from_sample(
        user_id=user.id,
        sample=body.sample_text,
        name=body.name,
        source_note=body.source_note,
        save=body.save,
    )
    return {"skill": skill}


@router.post("/writing-style-skills/analyze-upload")
async def analyze_writing_style_skill_upload(
    file: UploadFile = File(...),
    name: str = Form(""),
    source_note: str = Form(""),
    supplement_text: str = Form(""),
    save: bool = Form(True),
    user: User = Depends(get_current_user),
):
    allowed = (".txt", ".md", ".markdown", ".text", ".log")
    filename = file.filename or "sample.txt"
    if not filename.lower().endswith(allowed):
        raise HTTPException(400, "当前只支持纯文本文件：txt、md、markdown、text、log")
    raw = await file.read()
    max_size = 60 * 1024 * 1024
    if len(raw) > max_size:
        raise HTTPException(400, "单个样本文件不能超过 60MB，请分批上传代表章节")
    sample = _decode_upload_content(raw)
    if supplement_text.strip():
        sample = sample + "\n\n【用户补充样本】\n" + supplement_text.strip()
    task_id = str(uuid.uuid4())
    start_task(
        _do_analyze_writing_style_skill_task(
            task_id=task_id,
            user_id=user.id,
            sample=sample,
            name=name,
            source_note=source_note or filename,
            save=save,
        ),
        "writing_style_skill_extract",
        project_id=None,
        meta={
            "user_id": user.id,
            "filename": filename,
            "source_note": source_note or filename,
            "sample_word_count": len(sample),
            "save": save,
        },
        task_id=task_id,
        timeout=3600,
    )
    return {"task_id": task_id, "status": "running"}


@router.get("/writing-style-skills/task/{task_id}")
async def poll_writing_style_skill_task(task_id: str, user: User = Depends(get_current_user)):
    task = await get_task_persisted(task_id)
    if not task or task.get("task_type") != "writing_style_skill_extract":
        raise HTTPException(404, "任务不存在")
    if (task.get("meta") or {}).get("user_id") != user.id:
        raise HTTPException(404, "任务不存在")
    return {"task": task}


@router.get("/writing-style-skills/tasks")
async def list_writing_style_skill_tasks(user: User = Depends(get_current_user)):
    tasks = [
        task for task in list_tasks()
        if task.get("task_type") == "writing_style_skill_extract"
        and (task.get("meta") or {}).get("user_id") == user.id
    ]
    return {"tasks": tasks}


@router.put("/writing-style-skills/{skill_id}")
async def update_writing_style_skill(skill_id: str, body: UpdateWritingStyleSkillRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    skill = (await db.execute(
        select(WritingStyleSkill).where(WritingStyleSkill.id == skill_id, WritingStyleSkill.user_id == user.id)
    )).scalar_one_or_none()
    if not skill:
        raise HTTPException(404, "写作风格 Skill 不存在")
    data = body.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(skill, key, value)
    if "style_profile" in data and isinstance(data["style_profile"], dict):
        skill.description = data["style_profile"].get("description") or skill.description
        skill.prompt_fragment = data["style_profile"].get("prompt_fragment") or skill.prompt_fragment
    await db.flush()
    return {"skill": _skill_payload(skill)}


@router.delete("/writing-style-skills/{skill_id}")
async def delete_writing_style_skill(skill_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    skill = (await db.execute(
        select(WritingStyleSkill).where(WritingStyleSkill.id == skill_id, WritingStyleSkill.user_id == user.id)
    )).scalar_one_or_none()
    if not skill:
        raise HTTPException(404, "写作风格 Skill 不存在")
    skill.is_active = False
    return {"success": True}


@router.put("/projects/{project_id}/active-writing-style-skill")
async def set_project_active_writing_style_skill(project_id: str, body: ActiveWritingStyleSkillRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))).scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    if body.skill_id:
        skill = (await db.execute(
            select(WritingStyleSkill).where(WritingStyleSkill.id == body.skill_id, WritingStyleSkill.user_id == user.id, WritingStyleSkill.is_active == True)
        )).scalar_one_or_none()
        if not skill:
            raise HTTPException(404, "写作风格 Skill 不存在")
    style = project.writing_style or {}
    if not isinstance(style, dict):
        style = {}
    style["active_style_skill_id"] = body.skill_id or ""
    style["active_style_skill_updated_at"] = tz_now().isoformat()
    project.writing_style = style
    await db.flush()
    return {"project": _project_payload(project)}
