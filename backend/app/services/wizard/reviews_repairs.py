from app.services.wizard.common import *
from app.services.wizard.outline_arcs import _do_review_project_structure
from app.services.wizard.repair_guards import _revision_min_ratio

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
            if ch.content:
                chapters_content_parts.append(f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n摘要：{ch.summary or '无'}\n正文前300字：{(ch.content[:300] if ch.content else '无')}\n正文后500字：{(ch.content[-500:] if len(ch.content) > 500 else ch.content) if ch.content else '无'}")
            else:
                chapters_content_parts.append(f"=== 第{ch.chapter_number}章 {ch.title or ''} ===\n状态：未写入\n摘要：{ch.summary or '无'}")
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
        return {
            **chapter_review,
            "volume_structure_review": structure_review,
            "chapter_review": chapter_review,
            "review_mode": "volume_structure_and_chapters",
            "overall_score": round(((float(structure_review.get("overall_score") or 0) + float(chapter_review.get("overall_score") or 0)) / 2), 1),
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
                issue["priority"] = "critical" if severity in {"critical", "致命"} else "high" if severity in {"high", "严重"} else "medium"
                issue["chapter_number"] = _review_chapter_number(issue)
                issues.append(issue)
    return issues

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
                _validate_full_chapter_revision(chapter.content or "", new_content, chapter.hook or "", "repair")
                cleaned_content, revised_hook = _split_hook_marker(new_content)
                await _save_chapter_version(db, chapter, "ai_repair", f"AI 评审修复：第{chapter.chapter_number}章", {
                    "repair_plan": repair_plan,
                    "repair_task": task,
                    "review_result": review_result,
                })
                chapter.content = cleaned_content or new_content
                chapter.word_count = len(chapter.content or "")
                chapter.status = _status_after_content_change(chapter.status)
                chapter.version = (chapter.version or 1) + 1
                chapter.hook = revised_hook or result.get("hook") or chapter.hook
                with db.no_autoflush:
                    await _extract_and_apply_state(db, project_id, chapter, chapter.content)
                repaired_chapters.append(chapter.chapter_number)
                repaired_chapter_ids.append(str(chapter.id))
                await db.commit()

        if body.reaudit and repaired_chapter_ids:
            audited = []
            for chapter_id in repaired_chapter_ids:
                chapter = (await db.execute(
                    select(Chapter).where(
                        Chapter.id == chapter_id,
                        Chapter.project_id == project_id,
                        Chapter.volume_id == volume_id,
                    )
                )).scalar_one_or_none()
                if chapter:
                    prev_for_audit = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)
                    prev_ending = chapter.connects_from or ""
                    prev_hook = ""
                    prev_snapshot = "无"
                    if prev_for_audit and prev_for_audit.content:
                        prev_ending = prev_for_audit.content[-500:] if len(prev_for_audit.content) > 500 else prev_for_audit.content
                        prev_hook = prev_for_audit.hook or ""
                        prev_snapshot = _build_story_state_snapshot(prev_for_audit, prev_for_audit.story_state_snapshot or "")
                    audited.append({
                        "chapter_number": chapter.chapter_number,
                        "chapter_id": str(chapter.id),
                        "audit": await ai.audit_chapter(
                            prev_ending,
                            prev_hook,
                            prev_snapshot,
                            chapter.content or "",
                        ),
                    })
            return {
                "repair_plan": repair_plan,
                "repaired_chapters": repaired_chapters,
                "repaired_chapter_ids": repaired_chapter_ids,
                "duplicate_chapters": duplicate_chapters,
                "reaudit": audited,
            }

    return {
        "repair_plan": repair_plan,
        "repaired_chapters": repaired_chapters,
        "repaired_chapter_ids": repaired_chapter_ids,
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
        repair_context = {
            "original_word_count": len(original_content),
            "min_output_chars": min_output_chars,
            "min_output_rule": f"输出正文长度必须不少于 {min_output_chars} 字；低于该值会被系统拒绝写入。" if min_output_chars else "",
            "original_hook": chapter.hook or "",
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
                    _validate_full_chapter_revision(original_content, new_content, chapter.hook or "", body.mode, previous_content)
                cleaned_content, revised_hook = _split_hook_marker(new_content)
                next_content = cleaned_content or new_content
                next_hook = revised_hook or result.get("hook") or chapter.hook
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
