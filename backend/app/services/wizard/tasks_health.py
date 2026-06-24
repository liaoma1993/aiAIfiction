from app.services.wizard.common import *
from app.services.wizard.chapters import _do_write_chapter, _do_batch_write_arc, _do_split_chapter, _do_extract_state, _do_extract_style_fingerprint
from app.services.wizard.outline_arcs import (
    _do_adjust_outline,
    _do_adjust_outline_chat,
    _do_expand_arc_chapters,
    _do_expand_volume_arcs,
    _do_generate_master_outline,
    _do_generate_outline_draft,
    _do_generate_story_bible,
    _do_review_project_structure,
    _do_revise_outline_chat,
    _do_revise_volume_arc,
    _do_split_volumes,
    _format_volume_continuity_context,
)
from app.services.wizard.reviews_repairs import (
    _do_audit_chapter,
    _do_diagnose_chapter,
    _do_repair_from_review,
    _do_review_arc,
    _do_review_arc_structure,
    _do_review_chapter_blueprints,
    _do_review_volume,
    _do_revise_chapter,
    _normalize_review_issues,
)
from app.services.wizard.world_entities import (
    _do_generate_characters,
    _do_generate_characters_draft,
    _do_generate_world,
    _do_generate_world_draft,
)

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

async def project_tasks(project_id: str, user: User = Depends(get_current_user)):
    return {"tasks": await list_tasks_persisted(project_id)}

async def project_state_ledger(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chapters = (await db.execute(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_number)
    )).scalars().all()
    trails = (await db.execute(
        select(StoryStateTrail).where(StoryStateTrail.project_id == project_id).order_by(StoryStateTrail.chapter_number)
    )).scalars().all()

    ledger = {
        "characters": [],
        "relationships": [],
        "objects": [],
        "external_pressures": [],
        "open_threads": [],
        "hooks": [],
        "recent_state_deltas": [],
    }
    for ch in chapters:
        if ch.characters_in_chapter:
            ledger["characters"].extend([_safe_str(x) for x in ch.characters_in_chapter[:8]])
        if ch.relationship_changes:
            ledger["relationships"].extend(ch.relationship_changes[:8])
        if ch.object_states:
            ledger["objects"].extend(ch.object_states[:8])
        if ch.external_pressures:
            ledger["external_pressures"].extend(ch.external_pressures[:8])
        if ch.connects_to:
            ledger["open_threads"].append({"chapter_number": ch.chapter_number, "title": ch.title, "state": _clip_text(ch.connects_to, 220)})
        if ch.hook:
            ledger["hooks"].append({"chapter_number": ch.chapter_number, "title": ch.title, "hook": _clip_text(ch.hook, 220), "status": "待追踪"})
        if ch.state_delta:
            ledger["recent_state_deltas"].append({"chapter_number": ch.chapter_number, "delta": ch.state_delta})
        state = _parse_state_snapshot(ch.story_state_snapshot or "")
        for key, target in [
            ("relationship_changes", "relationships"),
            ("object_states", "objects"),
            ("external_pressures", "external_pressures"),
            ("next_must_follow", "open_threads"),
        ]:
            value = state.get(key)
            if value:
                if target == "open_threads":
                    ledger[target].extend({"chapter_number": ch.chapter_number, "state": _safe_str(x)} for x in value[:8])
                else:
                    ledger[target].extend(value[:8] if isinstance(value, list) else [value])
    for trail in trails[-20:]:
        snap = trail.state_snapshot or {}
        if isinstance(snap, dict) and snap.get("next_must_follow"):
            ledger["open_threads"].extend({"chapter_number": trail.chapter_number, "state": _safe_str(x)} for x in snap.get("next_must_follow", [])[:5])

    ledger["characters"] = sorted(set(x for x in ledger["characters"] if x))[:80]
    for key in ["relationships", "objects", "external_pressures", "open_threads", "hooks", "recent_state_deltas"]:
        ledger[key] = ledger[key][-80:]
    return {"prompt_version": PROMPT_VERSION, "ledger": ledger}

async def project_health(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    world = (await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))).scalar_one_or_none()
    volumes = (await db.execute(select(Volume).where(Volume.project_id == project_id).order_by(Volume.volume_number))).scalars().all()
    chapters = (await db.execute(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_number))).scalars().all()
    foreshadowing = (await db.execute(select(ForeshadowingPlan).where(ForeshadowingPlan.project_id == project_id))).scalars().all()
    world_rule_audit = _world_rule_audit_payload(world, project)

    arc_issues = []
    for v in volumes:
        for check in v.arc_bridge_checks or []:
            if check.get("needs_repair") or (check.get("quality_gate") and not check["quality_gate"].get("passed", True)):
                arc_issues.append({"volume": v.title, **check})

    blueprint_issues = []
    hook_count = 0
    no_event_count = 0
    repeated_titles: dict[str, int] = {}
    for ch in chapters:
        repeated_titles[ch.title or ""] = repeated_titles.get(ch.title or "", 0) + 1
        if ch.hook or ch.connects_to:
            hook_count += 1
        if not ch.key_events:
            no_event_count += 1
        gate = (ch.blueprint or {}).get("blueprint_quality_gate") or (ch.continuity_checks or {}).get("blueprint_quality_gate")
        if gate and not gate.get("passed", True):
            blueprint_issues.append({"chapter_number": ch.chapter_number, "title": ch.title, "gate": gate})

    fatigue = []
    if len(chapters) >= 8:
        recent = chapters[-8:]
        if sum(1 for ch in recent if not ch.key_events) >= 4:
            fatigue.append("最近8章中至少4章缺少 key_events，可能出现事件推进疲劳")
        if sum(1 for ch in recent if not (ch.hook or ch.connects_to)) >= 4:
            fatigue.append("最近8章中至少4章缺少章末钩子或交接状态")
    repeated = [title for title, count in repeated_titles.items() if title and count > 1]
    if repeated:
        fatigue.append("存在重复章节标题，可能有生成重复或结构混乱：" + "、".join(repeated[:8]))

    scores = {
        "arc_continuity": max(0, 100 - len(arc_issues) * 10),
        "chapter_blueprint": max(0, 100 - len(blueprint_issues) * 8),
        "hook_density": round((hook_count / len(chapters)) * 100) if chapters else 0,
        "event_density": round(((len(chapters) - no_event_count) / len(chapters)) * 100) if chapters else 0,
        "foreshadowing_tracking": max(0, 100 - sum(1 for f in foreshadowing if f.status not in {"已回收", "完成", "done"}) * 5),
        "world_rules": world_rule_audit["score"],
    }
    overall = round(sum(scores.values()) / len(scores)) if scores else 0
    return {
        "prompt_version": PROMPT_VERSION,
        "overall_score": overall,
        "scores": scores,
        "arc_issues": arc_issues[:30],
        "blueprint_issues": blueprint_issues[:30],
        "fatigue_warnings": fatigue,
        "world_rule_audit": world_rule_audit,
        "foreshadowing": [{"name": f.name, "status": f.status, "plant_stage": f.plant_stage, "reveal_stage": f.reveal_stage} for f in foreshadowing[:80]],
    }

async def world_rule_audit(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    world = (await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))).scalar_one_or_none()
    return {"prompt_version": PROMPT_VERSION, "audit": _world_rule_audit_payload(world, project)}

async def prompt_modules(project_id: str, user: User = Depends(get_current_user)):
    return {
        "prompt_version": PROMPT_VERSION,
        "modules": PROMPT_MODULES,
        "coverage": {
            "active": len([m for m in PROMPT_MODULES if m.get("status") == "active"]),
            "total": len(PROMPT_MODULES),
            "generation_surfaces": sorted({surface for m in PROMPT_MODULES for surface in m.get("used_in", [])}),
        },
    }

async def generation_context_preview(project_id: str, chapter_id: str | None = None, volume_id: str | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if chapter_id:
        context = await build_generation_context(db, project_id, chapter_id)
        return {"prompt_version": PROMPT_VERSION, "scope": "chapter", "context": context}
    if volume_id:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume:
            raise HTTPException(404, "卷不存在")
        return {
            "prompt_version": PROMPT_VERSION,
            "scope": "volume",
            "volume_continuity_context": await _format_volume_continuity_context(db, project_id, volume),
            "arc_continuity_index": volume.arc_continuity_index or [],
            "arc_bridge_checks": volume.arc_bridge_checks or [],
        }
    bible = await build_story_bible(db, project_id)
    return {"prompt_version": PROMPT_VERSION, "scope": "project", "context": bible}

async def chapter_change_impact(project_id: str, chapter_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    later = (await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id, Chapter.chapter_number > chapter.chapter_number)
        .order_by(Chapter.chapter_number)
        .limit(12)
    )).scalars().all()
    impacted = []
    for ch in later:
        reasons = []
        if ch.connects_from and chapter.connects_to and chapter.connects_to[:30] in ch.connects_from:
            reasons.append("connects_from 直接引用本章结尾状态")
        if ch.arc_name == chapter.arc_name:
            reasons.append("同一弧线章节，可能共享 arc_steps 和状态链")
        if set(_safe_str(x) for x in (chapter.characters_in_chapter or [])) & set(_safe_str(x) for x in (ch.characters_in_chapter or [])):
            reasons.append("共享出场角色，人物状态可能受影响")
        if reasons:
            impacted.append({"chapter_number": ch.chapter_number, "title": ch.title, "reasons": reasons})
    return {
        "chapter": {"chapter_number": chapter.chapter_number, "title": chapter.title, "arc_name": chapter.arc_name},
        "impact_level": "high" if len(impacted) >= 5 else "medium" if impacted else "low",
        "impacted_chapters": impacted,
        "recommended_actions": [
            "只改本章正文时，至少同步检查下一章 connects_from",
            "改动章末钩子时，建议重跑本章之后的章节蓝图审查",
            "改动人物重大选择/伤势/秘密时，建议重新抽取状态账本",
        ],
    }

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
                new_task_id,
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

    if task_type == "review_arc_structure":
        volume_id = meta.get("volume_id")
        arc_index = meta.get("arc_index")
        if volume_id is None or arc_index is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_review_arc_structure(project_id, str(volume_id), int(arc_index)),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "review_chapter_blueprints":
        volume_id = meta.get("volume_id")
        arc_index = meta.get("arc_index")
        if volume_id is None or arc_index is None:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_review_chapter_blueprints(project_id, str(volume_id), int(arc_index)),
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

    if task_type == "diagnose_chapter":
        chapter_id = meta.get("chapter_id")
        if not chapter_id:
            raise HTTPException(400, "该任务缺少可重试参数")
        start_task(
            _do_diagnose_chapter(project_id, str(chapter_id)),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "extract_style_fingerprint":
        start_task(
            _do_extract_style_fingerprint(project_id),
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
        force = bool(meta.get("force"))
        start_task(_do_generate_master_outline(project_id, force=force), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "split_volumes":
        start_task(_do_split_volumes(project_id), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "revise_outline_chat":
        start_task(
            _do_revise_outline_chat(project_id, meta.get("messages", []), meta.get("latest_input", "")),
            task_type,
            project_id,
            {**meta, "retry_of": task_id},
            task_id=new_task_id,
        )
        return {"task_id": new_task_id}

    if task_type == "generate_outline_draft":
        start_task(_do_generate_outline_draft(project_id), task_type, project_id, {**meta, "retry_of": task_id}, task_id=new_task_id)
        return {"task_id": new_task_id}

    if task_type == "generate_characters":
        start_task(
            _do_generate_characters(project_id, int(meta.get("char_count", 6)), int(meta.get("faction_count", 3)), new_task_id),
            task_type,
            project_id,
            {**meta, "retry_of": task_id, "generation_mode": "segmented"},
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
