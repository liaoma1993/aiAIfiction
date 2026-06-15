from app.services.wizard.common import *
from app.services.wizard.outline_arcs import _do_review_project_structure
from app.services.wizard.repair_guards import (
    _effective_original_hook,
    _restore_missing_hook_marker,
    _revision_min_ratio,
)

async def audit_chapter(project_id: str, chapter_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_audit_chapter(project_id, chapter_id), "audit_chapter", project_id, {"chapter_id": chapter_id})
    return {"task_id": task_id}

async def diagnose_chapter(project_id: str, chapter_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_diagnose_chapter(project_id, chapter_id), "diagnose_chapter", project_id, {"chapter_id": chapter_id})
    return {"task_id": task_id}

async def review_arc(project_id: str, volume_id: str, body: ExpandArcRequest, user: User = Depends(get_current_user)):
    task_id = start_task(_do_review_arc(project_id, volume_id, body.arc_index), "review_arc", project_id, {"volume_id": volume_id, "arc_index": body.arc_index})
    return {"task_id": task_id}

async def review_arc_structure(project_id: str, volume_id: str, body: ExpandArcRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_review_arc_structure(project_id, volume_id, body.arc_index),
        "review_arc_structure",
        project_id,
        {"volume_id": volume_id, "arc_index": body.arc_index},
    )
    return {"task_id": task_id}

async def review_chapter_blueprints(project_id: str, volume_id: str, body: ExpandArcRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_review_chapter_blueprints(project_id, volume_id, body.arc_index),
        "review_chapter_blueprints",
        project_id,
        {"volume_id": volume_id, "arc_index": body.arc_index},
    )
    return {"task_id": task_id}

async def review_volume(project_id: str, volume_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_review_volume(project_id, volume_id), "review_volume", project_id, {"volume_id": volume_id})
    return {"task_id": task_id}

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

async def review_project_structure(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_review_project_structure(project_id), "review_project_structure", project_id)
    return {"task_id": task_id}

async def revise_chapter(project_id: str, chapter_id: str, body: ReviseChapterRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_revise_chapter(project_id, chapter_id, body),
        "revise_chapter",
        project_id,
        {
            "chapter_id": chapter_id,
            "mode": body.mode,
            "instruction": body.instruction,
            "selection": body.selection,
            "controls": body.controls,
            "apply": body.apply,
            "resolved_issue_index": body.resolved_issue_index,
            "resolved_issue": body.resolved_issue,
        },
    )
    return {"task_id": task_id}

def _review_dimension_scores(review: dict) -> dict:
    scores: dict[str, int] = {}
    for dim in review.get("dimensions") or []:
        if not isinstance(dim, dict):
            continue
        name = str(dim.get("name") or dim.get("key") or "").strip()
        score = dim.get("score")
        if not name or score is None:
            continue
        key = re.sub(r"^\d+[\.\、]\s*", "", name).strip()
        key_map = {
            "情节逻辑": "plot_logic",
            "角色一致性": "character_consistency",
            "节奏与结构": "pacing",
            "对话质量": "dialogue",
            "描写密度": "scene_clarity",
            "情感线": "emotion",
            "伏笔与回收": "information_reveal",
            "设定一致性": "world_consistency",
            "叙事视角": "pov",
            "阅读体验": "readability",
            "上下章节连贯": "continuity",
            "上下弧线连贯": "arc_continuity",
        }
        try:
            scores[key_map.get(key, key)] = int(round(float(score)))
        except (TypeError, ValueError):
            continue
    if review.get("continuity_score") is not None:
        scores.setdefault("continuity", int(round(float(review.get("continuity_score") or 0))))
    if review.get("readability_score") is not None:
        scores.setdefault("readability", int(round(float(review.get("readability_score") or 0))))
    return scores

def _issue_severity_from_priority(priority: str, fallback: str = "") -> str:
    value = str(fallback or priority or "").strip()
    if value in {"致命", "严重", "轻微"}:
        return value
    lowered = value.lower()
    if lowered == "critical":
        return "致命"
    if lowered == "high":
        return "严重"
    if lowered == "low":
        return "轻微"
    # 收紧：未明确分级的问题不再默认降级为"中等"，而是标记为"未分级"
    # 归一化时按 high 处理（宁严勿松），避免掩盖真实严重度
    return "未分级"

_SEVERITY_RANK = {"致命": 0, "critical": 0, "严重": 1, "high": 1, "未分级": 1, "中等": 2, "medium": 2, "轻微": 3, "low": 3}

def _build_review_chapter_excerpt(ch: Chapter, full_text: bool = True) -> str:
    """构造评审用的章节正文。
    full_text=True：送全章正文（中段不丢失），超长时按"前段+中段关键句抽样+后段"保留中段信息。
    """
    content = ch.content or ""
    if not content:
        return f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n状态：未写入\n摘要：{ch.summary or '无'}"
    header = f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n摘要：{ch.summary or '无'}\n正文："
    if not full_text or len(content) <= 2400:
        return f"{header}{content}"
    # 超长章节：前 800 + 中段抽样（每段取一句关键句）+ 后 800，保证中段逻辑链可见
    head = content[:800]
    tail = content[-800:]
    mid = content[800:-800]
    samples: list[str] = []
    step = max(200, len(mid) // 4)
    for i in range(0, len(mid), step):
        seg = mid[i:i + step]
        for sep in ("。", "！", "？", "……”", "’”"):
            pos = seg.find(sep)
            if pos != -1:
                samples.append(seg[:pos + len(sep)].strip())
                break
        if len(samples) >= 4:
            break
    mid_text = " ……（中段关键句抽样）".join(s for s in samples if s)
    return f"{header}{head}\n{mid_text}\n……\n{tail}"

# 已死角色的状态识别键（current_state JSON 里多种可能的键）
_DEATH_STATE_KEYS = ("alive", "is_alive", "death_state", "life_status", "status", "state")
_DEATH_POSITIVE_TOKENS = ("已死", "死亡", "已亡", "身亡", "阵亡", "dead", "deceased", "false", "已殁", "毙命", "丧命")

def _character_is_dead(c: Character) -> bool:
    """从 current_state JSON 多键识别角色是否已死亡。"""
    state = c.current_state
    if not isinstance(state, dict) or not state:
        return False
    for key in _DEATH_STATE_KEYS:
        value = state.get(key)
        if value is None:
            continue
        text = str(value).strip().lower()
        if key in ("alive", "is_alive"):
            # 显式 alive=False / "false" / "否" 视为死亡
            if text in {"false", "否", "0", "dead", "已死", "死亡"}:
                return True
            continue
        if any(tok in text for tok in _DEATH_POSITIVE_TOKENS):
            return True
    return False

def _detect_character_consistency_issues(content: str, characters: list[Character]) -> list[dict]:
    """确定性角色一致性校验：已死角色若在本章正文中出现"说话/行动"，记一条 critical 问题。
    补 LLM 审计"看懂了但没拦住"的盲区。
    """
    if not content or not characters:
        return []
    issues: list[dict] = []
    dead_chars = [c for c in characters if _character_is_dead(c)]
    if not dead_chars:
        return issues
    action_pattern = re.compile(r"(说道|说：|道：|喝道|喊道|笑道|怒道|问道|答道|低声道|大声说|问道|冲着|走上前|拔出|挥剑|举起|推开门|坐下|站起)")
    for c in dead_chars:
        name = (c.name or "").strip()
        if not name or name not in content:
            continue
        # 找到名字出现位置，检查其前后 30 字内是否有行动/说话动词
        for m in re.finditer(re.escape(name), content):
            window = content[m.start():m.start() + 30]
            if action_pattern.search(window):
                issues.append({
                    "severity": "critical",
                    "dimension": "2.角色一致性",
                    "source": "programmatic",
                    "target_text": content[m.start():m.start() + 24],
                    "fix_mode": "context",
                    "description": f"角色「{name}」当前状态为已死亡，但本章正文让其说话或行动，违反角色状态连续性。",
                    "fix_suggestion": f"删除「{name}」在本章的登场行动，改为他人转述、回忆或幻觉；或修正其 current_state 死亡标记。",
                    "repair_task": f"修正第N章：已死角色「{name}」不应直接行动，改为回忆/转述/幻觉呈现。",
                })
                break  # 同一角色只记一条
    return issues

def _dedup_review_issues(issues: list[dict]) -> list[dict]:
    """跨评审去重前置：同一 (chapter_number + dimension) 的问题按 severity 取最高保留。
    避免 review_volume 与 audit 同章产生重复问题污染看板。
    """
    if not issues:
        return issues
    bucket: dict[tuple, dict] = {}
    passthrough: list[dict] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        chapter_number = issue.get("chapter_number")
        dimension = str(issue.get("dimension") or issue.get("issue_type") or "").strip()
        # 用 description 前 40 字作为二级 key，避免不同 dimension 的同章问题被误并
        desc_key = str(issue.get("description") or issue.get("problem") or "")[:40]
        if chapter_number is None or not dimension:
            passthrough.append(issue)
            continue
        key = (chapter_number, dimension, desc_key)
        existing = bucket.get(key)
        if existing is None:
            bucket[key] = issue
            continue
        if _SEVERITY_RANK.get(str(issue.get("severity") or "").lower(), 2) < _SEVERITY_RANK.get(str(existing.get("severity") or "").lower(), 2):
            # 合并 evidence/fix_suggestion 后取更严重的
            for fld in ("evidence", "fix_suggestion", "target_text"):
                if not existing.get(fld) and issue.get(fld):
                    existing[fld] = issue.get(fld)
            bucket[key] = issue
    return list(bucket.values()) + passthrough

def _chapter_review_from_arc_review(review: dict, chapter: Chapter, chapter_issues: list[dict]) -> dict:
    issues = []
    for item in chapter_issues:
        issue = dict(item)
        issue.setdefault("severity", _issue_severity_from_priority(issue.get("priority", ""), issue.get("severity", "")))
        issue.setdefault("description", issue.get("problem") or issue.get("issue") or issue.get("repair_task") or "")
        issue.setdefault("fix_suggestion", issue.get("fix_suggestion") or issue.get("repair_task") or "")
        issue.setdefault("target_text", issue.get("evidence", ""))
        issue.setdefault("source", "review_arc")
        issues.append(issue)
    return {
        "overall_score": review.get("overall_score") or review.get("readability_score") or 0,
        "continuity_score": review.get("continuity_score"),
        "readability_score": review.get("readability_score"),
        "scores": _review_dimension_scores(review),
        "summary": f"来自弧线评审：{review.get('summary') or ''}",
        "issues": issues,
        "suggestions": [] if issues else [
            f"弧线评审未定位到第{chapter.chapter_number}章的阻断问题，可结合弧线总体评审继续观察。"
        ],
        "source": "review_arc",
        "review_scope": review.get("review_scope", ""),
        "passed": not issues and int(review.get("overall_score") or 0) >= 8,
    }

def _save_arc_review_to_chapters(chapters: list[Chapter], review: dict) -> list[int]:
    if not isinstance(review, dict) or not chapters:
        return []
    issues = _normalize_review_issues(review)
    continuity_repairs = []
    for item in review.get("continuity_repairs") or []:
        if isinstance(item, dict):
            repair = dict(item)
            repair["priority"] = repair.get("priority") or "high"
            repair["severity"] = repair.get("severity") or "严重"
            repair["chapter_number"] = _review_chapter_number(repair)
            repair["description"] = repair.get("problem") or repair.get("description") or ""
            repair["fix_suggestion"] = repair.get("repair_task") or repair.get("fix_suggestion") or ""
            continuity_repairs.append(repair)
    all_issues = issues + continuity_repairs
    saved_numbers: list[int] = []
    for chapter in chapters:
        chapter_issues = [
            issue for issue in all_issues
            if issue.get("chapter_number") == chapter.chapter_number
        ]
        chapter_review = _chapter_review_from_arc_review(review, chapter, chapter_issues)
        _save_quality_review_to_chapter(chapter, chapter_review)
        saved_numbers.append(chapter.chapter_number)
    return saved_numbers

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

        snapshot = "无"
        if prev_chapter:
            snapshot = _build_story_state_snapshot(prev_chapter, prev_chapter.story_state_snapshot or "")

        ai = AIService()
        result = await ai.audit_chapter(previous_ending, previous_hook, snapshot, chapter.content)
        # 程序化角色一致性校验：补 LLM 审计盲区（已死角色行动等硬性矛盾）
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        consistency_issues = _detect_character_consistency_issues(chapter.content or "", chars_result.scalars().all())
        if consistency_issues:
            existing_issues = list(result.get("issues") or [])
            result["issues"] = (consistency_issues + existing_issues)[:5]
            # 程序化 critical 问题强制拉低分数
            try:
                result["overall_score"] = min(int(result.get("overall_score") or 10), 5)
            except (TypeError, ValueError):
                result["overall_score"] = 5
            result["passed"] = False
            result.setdefault("audit_policy", "程序化校验发现角色状态硬性矛盾（如已死角色行动），综合分已强制下调。")
        _save_quality_review_to_chapter(chapter, result)
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
                chapters_content_parts.append(_build_review_chapter_excerpt(ch, full_text=True))
            else:
                chapters_content_parts.append(_build_review_chapter_excerpt(ch, full_text=True))
        chapters_content = "\n\n".join(chapters_content_parts)

        review_scope = f"弧线「{arc.get('name', '')}」共{len(chapters)}章"
        ai = AIService()
        result = await ai.review_chapters(
            project.title, project.genre, _wizard_story_brief(project),
            chars_summary, facs_summary,
            review_scope, chapters_content,
        )
        result["review_scope"] = review_scope
        saved_quality_chapters = _save_arc_review_to_chapters(chapters, result)
        result["saved_quality_chapters"] = saved_quality_chapters
        result["quality_dashboard_updated"] = bool(saved_quality_chapters)
        await db.commit()
        return result

async def _do_diagnose_chapter(project_id: str, chapter_id: str) -> dict:
    from app.services.wizard.chapters import _run_prewrite_diagnosis
    from app.services.wizard.outline_arcs import _generate_chapter_blueprint

    async with async_session() as db:
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project or not chapter:
            raise RuntimeError("章节不存在")
        vol = None
        if chapter.volume_id:
            vol = (await db.execute(select(Volume).where(Volume.id == chapter.volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        prev_chapter = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)
        if not chapter.blueprint:
            await _generate_chapter_blueprint(db, project_id, chapter, prev_chapter, vol)

        previous_ending = chapter.connects_from or "无"
        if prev_chapter and prev_chapter.content:
            previous_ending = prev_chapter.content[-500:] if len(prev_chapter.content) > 500 else prev_chapter.content
            if prev_chapter.hook:
                previous_ending += f"\n\n【上章钩子】{prev_chapter.hook}"
        story_state_snapshot = _build_story_state_snapshot(prev_chapter, prev_chapter.story_state_snapshot or "") if prev_chapter else "无"
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = "\n".join([_build_character_profile(c) for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs_result.scalars().all()])

        ai = AIService()
        result = await _run_prewrite_diagnosis(
            ai,
            project,
            chapter,
            vol,
            previous_ending,
            story_state_snapshot,
            chars_summary,
            facs_summary,
        )
        checks = chapter.continuity_checks or {}
        checks["prewrite_diagnosis"] = result
        chapter.continuity_checks = checks
        await db.commit()
        return result

async def _do_review_arc_structure(project_id: str, volume_id: str, arc_index: int) -> dict:
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
        chars_summary = "\n".join([_build_character_profile(c) for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs_result.scalars().all()])
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "volume_title": volume.title,
            "volume_outline": volume.outline or "",
            "previous_arc": arcs[arc_index - 1] if arc_index > 0 else {},
            "current_arc": arcs[arc_index],
            "next_arc": arcs[arc_index + 1] if arc_index + 1 < len(arcs) else {},
            "characters_summary": chars_summary,
            "factions_summary": facs_summary,
        }

    ai = AIService()
    result = await ai.review_arc_structure(**snapshot)

    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if volume and volume.narrative_arcs and arc_index < len(volume.narrative_arcs):
            arcs = list(volume.narrative_arcs or [])
            arc = dict(arcs[arc_index])
            arc["structure_review"] = result
            arcs[arc_index] = arc
            volume.narrative_arcs = arcs
            bridge_checks = _build_arc_bridge_checks(arcs)
            if arc_index < len(bridge_checks):
                bridge_checks[arc_index]["structure_review"] = result
            volume.arc_bridge_checks = bridge_checks
            await db.commit()
    return result

async def _do_review_chapter_blueprints(project_id: str, volume_id: str, arc_index: int) -> dict:
    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("请先生成弧线和章节")
        arcs = list(volume.narrative_arcs or [])
        if arc_index < 0 or arc_index >= len(arcs):
            raise RuntimeError("弧线索引无效")
        arc = arcs[arc_index]
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if not project:
            raise RuntimeError("项目不存在")
        chapters = (await db.execute(
            select(Chapter).where(Chapter.volume_id == volume_id, Chapter.arc_name == arc.get("name", "")).order_by(Chapter.chapter_number)
        )).scalars().all()
        if not chapters:
            raise RuntimeError("该弧线无章节蓝图")
        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = "\n".join([_build_character_profile(c) for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs_result.scalars().all()])
        chapter_payload = [
            {
                "chapter_number": ch.chapter_number,
                "title": ch.title or "",
                "summary": ch.summary or "",
                "connects_from": ch.connects_from or "",
                "connects_to": ch.connects_to or "",
                "blueprint": ch.blueprint or {},
                "continuity_checks": ch.continuity_checks or {},
            }
            for ch in chapters
        ]
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "volume_title": volume.title,
            "arc": arc,
            "chapters": chapter_payload,
            "characters_summary": chars_summary,
            "factions_summary": facs_summary,
        }

    ai = AIService()
    result = await ai.review_chapter_blueprints(**snapshot)

    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if volume and volume.narrative_arcs and arc_index < len(volume.narrative_arcs):
            arcs = list(volume.narrative_arcs or [])
            arc = dict(arcs[arc_index])
            arc["blueprint_review"] = result
            arcs[arc_index] = arc
            volume.narrative_arcs = arcs
            bridge_checks = _build_arc_bridge_checks(arcs)
            if arc_index < len(bridge_checks):
                bridge_checks[arc_index]["blueprint_review"] = result
            volume.arc_bridge_checks = bridge_checks
            await db.commit()
    return result

async def _do_review_volume(project_id: str, volume_id: str) -> dict:
    from app.services.wizard.outline_arcs import _chapter_outline_payload

    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume:
            raise RuntimeError("卷不存在")
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        volumes = (await db.execute(
            select(Volume).where(Volume.project_id == project_id).order_by(Volume.volume_number)
        )).scalars().all()

        chapters = (await db.execute(
            select(Chapter).where(Chapter.volume_id == volume_id).order_by(Chapter.chapter_number)
        )).scalars().all()

        chars_result = await db.execute(select(Character).where(Character.project_id == project_id))
        chars_summary = "\n".join([_build_character_profile(c) for c in chars_result.scalars().all()])
        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs_summary = "\n".join([_build_faction_profile(f) for f in facs_result.scalars().all()])

        chapters_content_parts = []
        for ch in chapters:
            chapters_content_parts.append(_build_review_chapter_excerpt(ch, full_text=True))
        chapters_content = "\n\n".join(chapters_content_parts)

        review_scope = f"卷「{volume.title}」共{len(chapters)}章"
        ai = AIService()
        project_outline = "\n".join([
            f"卷{v.volume_number}《{v.title or '未命名'}》：{v.summary or v.outline or '无概要'}"
            for v in volumes
        ])
        volume_payload = {
            "project": {
                "title": project.title if project else "",
                "genre": project.genre if project else "",
                "core_theme": project.core_theme if project else "",
                "reader_promise": getattr(project, "reader_promise", "") if project else "",
                "total_words": getattr(project, "target_total_words", 0) if project else 0,
            },
            "volume": {
                "id": str(volume.id),
                "volume_number": volume.volume_number,
                "title": volume.title,
                "summary": volume.summary,
                "outline": volume.outline,
                "theme": volume.theme,
                "chapter_range": [volume.chapter_range_start, volume.chapter_range_end],
                "emotional_arc_description": volume.emotional_arc_description,
                "narrative_line_distribution": volume.narrative_line_distribution,
                "tension_curve": volume.tension_curve,
                "narrative_arcs": volume.narrative_arcs or [],
                "arc_bridge_checks": volume.arc_bridge_checks or [],
            },
            "neighbor_volumes": {
                "previous": [
                    {"volume_number": v.volume_number, "title": v.title, "summary": v.summary}
                    for v in volumes if v.volume_number < volume.volume_number
                ][-2:],
                "next": [
                    {"volume_number": v.volume_number, "title": v.title, "summary": v.summary}
                    for v in volumes if v.volume_number > volume.volume_number
                ][:2],
            },
            "chapters": [_chapter_outline_payload(ch) for ch in chapters],
        }
        structure_review = await ai.review_volume_structure(
            project.title, project.genre, _wizard_story_brief(project),
            project_outline, chars_summary, facs_summary, volume_payload,
        )
        if not chapters:
            return {
                **structure_review,
                "summary": structure_review.get("summary") or "已完成卷轴合理性评审。",
                "volume_structure_review": structure_review,
                "chapter_review": None,
                "review_mode": "volume_structure_only",
            }
        chapter_review = await ai.review_chapters(
            project.title, project.genre, _wizard_story_brief(project),
            chars_summary, facs_summary,
            review_scope, chapters_content,
        )
        # 加权合并：章节正文分（含逻辑/角色/连续性维度）权重 0.6，结构分权重 0.4
        struct_score = float(structure_review.get("overall_score") or 0)
        chapter_score = float(chapter_review.get("overall_score") or 0)
        merged_overall = round(struct_score * 0.4 + chapter_score * 0.6, 1)
        return {
            **chapter_review,
            "volume_structure_review": structure_review,
            "chapter_review": chapter_review,
            "review_mode": "volume_structure_and_chapters",
            "overall_score": merged_overall,
            "summary": f"卷轴结构：{structure_review.get('summary', '')}\n章节正文：{chapter_review.get('summary', '')}".strip(),
            "dimensions": (structure_review.get("dimensions") or []) + (chapter_review.get("dimensions") or []),
            "critical_issues": (structure_review.get("critical_issues") or []) + (chapter_review.get("critical_issues") or []),
            "high_issues": (structure_review.get("high_issues") or []) + (chapter_review.get("high_issues") or []),
            "low_issues": (structure_review.get("low_issues") or []) + (chapter_review.get("low_issues") or []),
            "strengths": (structure_review.get("strengths") or []) + (chapter_review.get("strengths") or []),
            "writing_tips": (structure_review.get("writing_tips") or []) + (chapter_review.get("writing_tips") or []),
        }

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
                issue["priority"] = "critical" if severity in {"critical", "致命"} else "high" if severity in {"high", "严重", "未分级"} else "medium"
                issue["chapter_number"] = _review_chapter_number(issue)
                issues.append(issue)
    # 跨评审去重前置：同章同维度按 severity 合并，避免 review_volume + audit 重复污染
    return _dedup_review_issues(issues)

async def _build_review_chapter_index(db: AsyncSession, project_id: str, volume_id: str) -> list[dict]:
    chapters = (await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id, Chapter.volume_id == volume_id)
        .order_by(Chapter.chapter_number, Chapter.updated_at.desc(), Chapter.created_at.desc())
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
    from app.services.wizard.chapters import _extract_and_apply_state, _save_chapter_version

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
    if str(repair_plan.get("repair_level") or "").lower() == "outline":
        if task_id:
            update_progress(task_id, 1, "评审问题属于大纲/弧线结构层，已停止自动逐章覆盖", {
                "stage": "blocked_outline_repair",
                "task_count": 0,
                "diagnosis": repair_plan.get("diagnosis", ""),
                "one_pass_policy": repair_plan.get("one_pass_policy", ""),
                "arc_patch_strategy": repair_plan.get("arc_patch_strategy", {}),
            })
        return {
            "repair_plan": repair_plan,
            "repaired_chapters": [],
            "repaired_chapter_ids": [],
            "failed_chapters": [],
            "duplicate_chapters": [],
            "blocked": True,
            "blocked_reason": "评审问题属于大纲/弧线结构层，自动逐章修复容易越修越乱。请先调整弧线或章节蓝图，再重新写作。",
        }
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

    def _priority_rank(value: str) -> int:
        return 0 if value == "critical" else 1 if value == "high" else 2

    def _merge_chapter_tasks(task_list: list[dict]) -> list[dict]:
        """同一章只修一次，避免一章被多个问题连续覆盖后越修越漂。"""
        grouped: dict[int, list[dict]] = {}
        passthrough: list[dict] = []
        for task in task_list:
            chapter_number = _task_chapter_number(task)
            if chapter_number == 10**9:
                passthrough.append(task)
                continue
            grouped.setdefault(chapter_number, []).append(task)

        merged: list[dict] = []
        for chapter_number, items in grouped.items():
            if len(items) == 1:
                merged.append(items[0])
                continue
            items.sort(key=lambda item: _priority_rank(str(item.get("priority") or "medium")))
            primary = dict(items[0])
            primary["chapter"] = chapter_number
            primary["issue_type"] = "整章问题合并修复"
            primary["issue_summary"] = "；".join(
                str(item.get("issue_summary") or item.get("description") or item.get("issue_type") or "").strip()
                for item in items
                if str(item.get("issue_summary") or item.get("description") or item.get("issue_type") or "").strip()
            )[:4000]
            priority = min((str(item.get("priority") or "medium") for item in items), key=_priority_rank, default="medium")
            primary["priority"] = priority
            for key in ["canon_to_keep", "changes_required", "must_not_do", "verification_points"]:
                merged_values: list[str] = []
                for item in items:
                    value = item.get(key)
                    values = value if isinstance(value, list) else [value] if value else []
                    for entry in values:
                        text = str(entry or "").strip()
                        if text and text not in merged_values:
                            merged_values.append(text)
                primary[key] = merged_values[:20]
            primary["bridge_to_previous"] = "\n".join(
                str(item.get("bridge_to_previous") or "").strip()
                for item in items
                if str(item.get("bridge_to_previous") or "").strip()
            )[:2000]
            primary["bridge_to_next"] = "\n".join(
                str(item.get("bridge_to_next") or "").strip()
                for item in items
                if str(item.get("bridge_to_next") or "").strip()
            )[:2000]
            primary["merged_tasks"] = items
            primary["merged_issue_count"] = len(items)
            merged.append(primary)
        merged.extend(passthrough)
        return merged

    if body.resume_chapters:
        resume_set = {
            int(ch)
            for ch in body.resume_chapters
            if isinstance(ch, int) or (isinstance(ch, str) and ch.isdigit())
        }
        if resume_set:
            tasks = [t for t in tasks if _task_chapter_number(t) in resume_set]

    tasks = _merge_chapter_tasks(tasks)
    tasks.sort(key=lambda t: (_priority_rank(str(t.get("priority") or "medium")), _task_chapter_number(t)))

    chapter_items_by_number: dict[int, list[dict]] = {}
    for item in chapter_index:
        chapter_number = item.get("chapter_number")
        if isinstance(chapter_number, int):
            chapter_items_by_number.setdefault(chapter_number, []).append(item)
    duplicate_chapters = [
        {
            "chapter_number": chapter_number,
            "count": len(items),
            "chapter_ids": [item.get("chapter_id") for item in items if item.get("chapter_id")],
            "titles": [item.get("title", "") for item in items],
        }
        for chapter_number, items in chapter_items_by_number.items()
        if len(items) > 1
    ]
    chapter_map = {
        chapter_number: next((item for item in items if item.get("has_content")), items[0])
        for chapter_number, items in chapter_items_by_number.items()
    }
    if task_id:
        update_progress(task_id, 0, f"已生成修复计划：{len(tasks)} 项", {
            "stage": "planned",
            "task_count": len(tasks),
            "diagnosis": repair_plan.get("diagnosis", ""),
            "global_constraints": repair_plan.get("global_constraints", []),
            "duplicate_chapters": duplicate_chapters,
        })

    repaired_chapters: list[int] = []
    repaired_chapter_ids: list[str] = []
    failed_chapters: list[dict] = []
    chapter_audit_records: list[dict] = []
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
            chapter_id = chapter_meta.get("chapter_id")
            if not chapter_id:
                continue
            chapter = (await db.execute(
                select(Chapter).where(
                    Chapter.id == chapter_id,
                    Chapter.project_id == project_id,
                    Chapter.volume_id == volume_id,
                )
            )).scalar_one_or_none()
            if not chapter:
                continue

            prev = await _get_previous_chapter(db, project_id, volume_id, chapter.chapter_number)
            previous_ending = prev.content[-500:] if prev and prev.content else chapter.connects_from or ""
            if prev and prev.hook:
                previous_ending = f"{previous_ending}\n\n【上章钩子】{prev.hook}"
            next_chapter = (await db.execute(
                select(Chapter)
                .where(
                    Chapter.project_id == project_id,
                    Chapter.volume_id == volume_id,
                    Chapter.chapter_number > chapter.chapter_number,
                )
                .order_by(Chapter.chapter_number.asc(), Chapter.updated_at.desc(), Chapter.created_at.desc())
                .limit(1)
            )).scalars().first()
            chapter_review_issues = [
                issue for issue in issues
                if issue.get("chapter_number") == chapter.chapter_number
            ]

            repair_context = {
                "diagnosis": repair_plan.get("diagnosis", ""),
                "repair_level": repair_plan.get("repair_level", ""),
                "one_pass_policy": repair_plan.get("one_pass_policy", ""),
                "arc_patch_strategy": repair_plan.get("arc_patch_strategy", {}),
                "global_constraints": repair_plan.get("global_constraints", []),
                "issue_type": task.get("issue_type", ""),
                "issue_summary": task.get("issue_summary", ""),
                "structural_role": task.get("structural_role", ""),
                "coordinated_arc_patch": bool(task.get("coordinated_arc_patch")),
                "merged_issue_count": task.get("merged_issue_count", 1),
                "merged_tasks": task.get("merged_tasks", []),
                "chapter_review_issues": chapter_review_issues,
                "original_word_count": len(chapter.content or ""),
                "min_output_chars": int(len(chapter.content or "") * _revision_min_ratio("repair")) if chapter.content else 0,
                "min_output_rule": f"必须输出完整章节正文，最低不少于 {int(len(chapter.content or '') * _revision_min_ratio('repair'))} 字；严禁输出摘要或只输出修复说明。",
                "canon_to_keep": task.get("canon_to_keep", []),
                "changes_required": task.get("changes_required", []),
                "must_not_do": task.get("must_not_do", []),
                "verification_points": task.get("verification_points", []),
                "bridge_to_previous": task.get("bridge_to_previous", ""),
                "bridge_to_next": task.get("bridge_to_next", ""),
                "previous_chapter": {
                    "chapter_number": prev.chapter_number if prev else None,
                    "title": prev.title if prev else "",
                    "hook": prev.hook if prev else "",
                    "ending": previous_ending,
                },
                "next_chapter": {
                    "chapter_number": next_chapter.chapter_number if next_chapter else None,
                    "title": next_chapter.title if next_chapter else "",
                    "summary": next_chapter.summary if next_chapter else "",
                    "connects_from": next_chapter.connects_from if next_chapter else "",
                },
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

            async def _run_repair_attempt(attempt: int, extra_instruction: str = "") -> tuple[dict, str, str, str]:
                result = await ai.revise_chapter(
                    project.title, project.genre, chapter.chapter_number, chapter.title or "",
                    chapter.summary or "", chapter.content or "", "repair",
                    instruction="\n".join(x for x in [
                        f"按修复计划处理：{task.get('issue_summary', '')}",
                        "必须输出完整章节正文，不能输出摘要、提纲、改动说明或片段。",
                        extra_instruction,
                    ] if x),
                    selection="",
                    previous_ending=previous_ending,
                    controls={
                        "repair_task": task,
                        "global_constraints": repair_plan.get("global_constraints", []),
                        "review_scope": review_scope,
                        "min_output_chars": repair_context.get("min_output_chars", 0),
                        "full_chapter_required": True,
                        "single_pass_chapter_repair": True,
                    },
                    repair_context=json.dumps({**repair_context, "attempt": attempt}, ensure_ascii=False),
                )
                new_content = result.get("content", "")
                original_hook = _effective_original_hook(chapter.content or "", chapter.hook or "")
                new_content, restored_hook, hook_restored = _restore_missing_hook_marker(
                    chapter.content or "",
                    new_content,
                    original_hook,
                    result.get("hook", ""),
                )
                if hook_restored:
                    result.setdefault("change_notes", []).append("AI 修复稿缺少章末钩子，系统已自动恢复原章末钩子。")
                    result["hook_restored"] = True
                _validate_full_chapter_revision(chapter.content or "", new_content, original_hook, "repair", prev.content if prev else "")
                return result, new_content, restored_hook, original_hook

            if body.apply:
                try:
                    result, new_content, restored_hook, _original_hook = await _run_repair_attempt(1)
                except RuntimeError as exc:
                    error_text = str(exc)
                    if "输出过短" in error_text:
                        if task_id:
                            update_progress(task_id, idx / max(len(tasks), 1), f"第{chapter.chapter_number}章修复稿过短，正在保容量重试", {
                                "stage": "retrying_short_repair",
                                "chapter_number": chapter.chapter_number,
                                "chapter_title": chapter.title or "",
                                "error": error_text,
                                "min_output_chars": repair_context.get("min_output_chars", 0),
                            })
                        try:
                            result, new_content, restored_hook, _original_hook = await _run_repair_attempt(
                                2,
                                f"上次输出过短被系统拒绝：{error_text}。这次必须保留原章节主要场景、对白、动作和章末钩子，正文不少于 {repair_context.get('min_output_chars', 0)} 字。",
                            )
                        except RuntimeError as retry_exc:
                            failed_chapters.append({
                                "chapter_number": chapter.chapter_number,
                                "chapter_title": chapter.title or "",
                                "error": str(retry_exc),
                                "first_error": error_text,
                            })
                            if task_id:
                                update_progress(task_id, idx / max(len(tasks), 1), f"第{chapter.chapter_number}章修复失败，已跳过继续后续章节", {
                                    "stage": "chapter_repair_failed",
                                    "chapter_number": chapter.chapter_number,
                                    "chapter_title": chapter.title or "",
                                    "error": str(retry_exc),
                                })
                            continue
                    else:
                        failed_chapters.append({
                            "chapter_number": chapter.chapter_number,
                            "chapter_title": chapter.title or "",
                            "error": error_text,
                        })
                        if task_id:
                            update_progress(task_id, idx / max(len(tasks), 1), f"第{chapter.chapter_number}章修复失败，已跳过继续后续章节", {
                                "stage": "chapter_repair_failed",
                                "chapter_number": chapter.chapter_number,
                                "chapter_title": chapter.title or "",
                                "error": error_text,
                            })
                        continue
                # 写入 + 修复-验证循环：修复后立即 re-audit，若仍不达标或引入新 critical，再修一轮（最多 2 轮）
                def _apply_repair_content(content: str, hk: str, result_obj: dict) -> None:
                    nonlocal new_content, restored_hook
                    chapter.content = content
                    chapter.word_count = len(chapter.content or "")
                    chapter.status = _status_after_content_change(chapter.status)
                    chapter.version = (chapter.version or 1) + 1
                    chapter.hook = hk or restored_hook or result_obj.get("hook") or chapter.hook

                cleaned_content, revised_hook = _split_hook_marker(new_content)
                await _save_chapter_version(db, chapter, "ai_repair", f"AI 评审修复：第{chapter.chapter_number}章", {
                    "repair_plan": repair_plan,
                    "repair_task": task,
                    "review_result": review_result,
                })
                _apply_repair_content(cleaned_content or new_content, revised_hook, result)
                with db.no_autoflush:
                    await _extract_and_apply_state(db, project_id, chapter, chapter.content)
                await db.commit()

                # 立即 re-audit 验证；不达标则再修一轮（最多 2 轮闭环）
                verification_round = 0
                last_audit: dict | None = None
                audit_notes: list[str] = []
                while verification_round < 2:
                    verification_round += 1
                    prev_for_audit = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)
                    audit_prev_ending = chapter.connects_from or ""
                    audit_prev_hook = ""
                    audit_prev_snapshot = "无"
                    if prev_for_audit and prev_for_audit.content:
                        audit_prev_ending = prev_for_audit.content[-500:] if len(prev_for_audit.content) > 500 else prev_for_audit.content
                        audit_prev_hook = prev_for_audit.hook or ""
                        audit_prev_snapshot = _build_story_state_snapshot(prev_for_audit, prev_for_audit.story_state_snapshot or "")
                    last_audit = await ai.audit_chapter(
                        audit_prev_ending,
                        audit_prev_hook,
                        audit_prev_snapshot,
                        chapter.content or "",
                    )
                    _save_quality_review_to_chapter(chapter, last_audit)
                    await db.commit()

                    # 判定是否达标：overall_score>=8 且无 critical/high 问题则通过
                    audit_score = 0
                    try:
                        audit_score = int(last_audit.get("overall_score") or 0)
                    except (TypeError, ValueError):
                        audit_score = 0
                    blocking_after = [
                        i for i in (last_audit.get("issues") or [])
                        if isinstance(i, dict) and str(i.get("severity", "")).lower() in {"critical", "high", "致命", "严重"}
                    ]
                    if audit_score >= 8 and not blocking_after:
                        break
                    # 第 2 轮仍不达标：标记不强行再修，记录后退出
                    if verification_round >= 2:
                        audit_notes.append(
                            f"修复后复审第{verification_round}轮仍未达标（评分 {audit_score}，阻断问题 {len(blocking_after)} 条），"
                            "已保留当前稿件，建议人工复核。"
                        )
                        result.setdefault("change_notes", []).extend(audit_notes)
                        break
                    # 第 1 轮不达标：再修一轮，把复审问题注入指令
                    blocking_desc = "；".join(
                        str(i.get("description") or i.get("fix_suggestion") or "")[:80]
                        for i in blocking_after[:3]
                    )
                    audit_notes.append(f"修复后复审第{verification_round}轮评分为 {audit_score}，存在阻断问题，启动第{verification_round + 1}轮针对性修复。")
                    try:
                        result2, new_content2, restored_hook2, _oh = await _run_repair_attempt(
                            verification_round + 1,
                            f"上一稿修复后复审仍未通过（评分 {audit_score}）。必须针对以下阻断问题重修：{blocking_desc}。",
                        )
                    except RuntimeError as vexc:
                        audit_notes.append(f"第{verification_round + 1}轮修复失败：{vexc}。保留上一稿。")
                        result.setdefault("change_notes", []).extend(audit_notes)
                        break
                    cleaned2, revised_hook2 = _split_hook_marker(new_content2)
                    await _save_chapter_version(db, chapter, "ai_repair", f"AI 评审修复第{verification_round + 1}轮：第{chapter.chapter_number}章", {
                        "repair_plan": repair_plan,
                        "repair_task": task,
                        "previous_audit": last_audit,
                    })
                    new_content, restored_hook = new_content2, restored_hook2
                    _apply_repair_content(cleaned2 or new_content2, revised_hook2, result2)
                    with db.no_autoflush:
                        await _extract_and_apply_state(db, project_id, chapter, chapter.content)
                    await db.commit()

                repaired_chapters.append(chapter.chapter_number)
                repaired_chapter_ids.append(str(chapter.id))
                chapter_audit_records.append({
                    "chapter_number": chapter.chapter_number,
                    "chapter_id": str(chapter.id),
                    "audit": last_audit,
                    "verification_rounds": verification_round,
                })

        audited = chapter_audit_records
        if task_id:
            update_progress(task_id, 1, f"修复完成：写入 {len(repaired_chapters)} 章，跳过 {len(failed_chapters)} 章", {
                "stage": "completed",
                "task_count": len(tasks),
                "repaired_count": len(repaired_chapters),
                "failed_count": len(failed_chapters),
                "reaudit_count": len(audited),
                "quality_dashboard_updated": True,
            })
        return {
            "repair_plan": repair_plan,
            "repaired_chapters": repaired_chapters,
            "repaired_chapter_ids": repaired_chapter_ids,
            "failed_chapters": failed_chapters,
            "duplicate_chapters": duplicate_chapters,
            "reaudit": audited,
            "reaudit_auto": not body.reaudit,
            "quality_dashboard_updated": True,
        }

    if task_id:
        update_progress(task_id, 1, f"修复完成：写入 {len(repaired_chapters)} 章，跳过 {len(failed_chapters)} 章", {
            "stage": "completed",
            "task_count": len(tasks),
            "repaired_count": len(repaired_chapters),
            "failed_count": len(failed_chapters),
            "reaudit_count": 0,
            "quality_dashboard_updated": False,
        })
    return {
        "repair_plan": repair_plan,
        "repaired_chapters": repaired_chapters,
        "repaired_chapter_ids": repaired_chapter_ids,
        "failed_chapters": failed_chapters,
        "duplicate_chapters": duplicate_chapters,
    }

async def _do_revise_chapter(project_id: str, chapter_id: str, body: ReviseChapterRequest) -> dict:
    from app.services.wizard.chapters import _save_chapter_version

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
        previous_content = prev.content or "" if prev else ""
        previous_ending = prev.content[-500:] if prev and prev.content else chapter.connects_from or ""
        if prev and prev.hook:
            previous_ending = f"{previous_ending}\n\n【上章钩子】{prev.hook}"
        ai = AIService()
        controls = _merge_writing_controls(project, body.controls)
        min_output_chars = int(len(original_content) * _revision_min_ratio(body.mode)) if body.mode in FULL_CHAPTER_REPAIR_MODES else 0
        original_hook = _effective_original_hook(original_content, chapter.hook or "")
        repair_context = {
            "original_word_count": len(original_content),
            "min_output_chars": min_output_chars,
            "min_output_rule": f"输出正文长度必须不少于 {min_output_chars} 字；低于该值会被系统拒绝写入。" if min_output_chars else "",
            "original_hook": original_hook,
            "must_preserve": [
                "章节核心剧情、人物关系、关键线索、上承下启",
                "章末钩子 original_hook；如需强化，只能在原钩子基础上改得更具体，不能删除",
                "轻修模式不得明显缩短正文，不得把场景压缩成摘要",
                f"原文约 {len(original_content)} 字，修复后最低保留 {min_output_chars} 字；只能通过补足承接、过渡、反应和必要场景实写来修复，不能删减场景换取简洁。" if min_output_chars else "",
                "上一章内容只能作为承接上下文，禁止复制上一章已发生场景、对话或整段描写到本章；如需回应钩子，只能写本章人物对既有事实的反应和后果。",
            ],
            "anti_duplication_rule": "如果修复稿包含上一章长段落或重复上章已完成场景，系统会拒绝写入。",
            "write_back_guard": "若无法在不破坏章节容量和章末钩子的前提下修复，请在 change_notes 说明风险，不要输出缩水正文。",
        }
        result = await ai.revise_chapter(
            project.title, project.genre, chapter.chapter_number, chapter.title or "",
            chapter.summary or "", chapter.content or "", body.mode, body.instruction,
            body.selection, previous_ending, controls, json.dumps(repair_context, ensure_ascii=False),
        )
        new_content = result.get("content", "")
        if body.apply and new_content:
            next_content = new_content
            next_hook = chapter.hook
            if body.selection and body.selection in original_content:
                next_content = original_content.replace(body.selection, new_content, 1)
            elif is_local_revise:
                raise RuntimeError("局部修复返回后原文定位失效，本次未写入正文")
            else:
                if body.mode in FULL_CHAPTER_REPAIR_MODES:
                    new_content, restored_hook, hook_restored = _restore_missing_hook_marker(
                        original_content,
                        new_content,
                        original_hook,
                        result.get("hook", ""),
                    )
                    if hook_restored:
                        result.setdefault("change_notes", []).append("AI 修复稿缺少章末钩子，系统已自动恢复原章末钩子。")
                        result["hook_restored"] = True
                    _validate_full_chapter_revision(original_content, new_content, original_hook, body.mode, previous_content)
                else:
                    restored_hook = ""
                cleaned_content, revised_hook = _split_hook_marker(new_content)
                next_content = cleaned_content or new_content
                next_hook = revised_hook or restored_hook or result.get("hook") or chapter.hook
            await _save_chapter_version(db, chapter, "ai_revise", f"AI 修订前备份：{body.mode}", body.model_dump())
            chapter.content = next_content
            chapter.hook = next_hook
            chapter.word_count = len(chapter.content or "")
            chapter.status = _status_after_content_change(chapter.status)
            chapter.version = (chapter.version or 1) + 1
            previous_snapshot = _build_story_state_snapshot(prev, prev.story_state_snapshot or "") if prev else "无"
            review = await ai.audit_chapter(previous_ending, prev.hook if prev else "", previous_snapshot, chapter.content or "")
            _save_quality_review_to_chapter(chapter, review)
            _remember_resolved_quality_issue(chapter, body, review)
            if isinstance(review, dict):
                result["quality_review"] = review
            await db.commit()
        return result
