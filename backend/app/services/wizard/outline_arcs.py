from app.services.wizard.common import *
from app.services.wizard.state_tools import _serialize_snapshot, _serialize_summary

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

async def _format_volume_continuity_context(db: AsyncSession, project_id: str, volume: Volume) -> str:
    prev_volume = (await db.execute(
        select(Volume)
        .where(Volume.project_id == project_id, Volume.volume_number < volume.volume_number)
        .order_by(Volume.volume_number.desc())
        .limit(1)
    )).scalar_one_or_none()
    next_volume = (await db.execute(
        select(Volume)
        .where(Volume.project_id == project_id, Volume.volume_number > volume.volume_number)
        .order_by(Volume.volume_number.asc())
        .limit(1)
    )).scalar_one_or_none()

    parts: list[str] = []
    if prev_volume:
        parts.append(f"【上一卷】第{prev_volume.volume_number}卷《{prev_volume.title}》")
        if prev_volume.summary:
            parts.append(f"上一卷摘要：{_clip_text(prev_volume.summary, 500)}")
        if prev_volume.outline:
            parts.append(f"上一卷大纲要点：{_clip_text(prev_volume.outline, 700)}")
        prev_arcs = prev_volume.narrative_arcs or []
        if prev_arcs:
            last_arc = prev_arcs[-1]
            parts.append(f"上一卷最后弧线：{last_arc.get('name', '')}")
            parts.append(f"终点状态：{_clip_text(last_arc.get('ending_state', ''), 400)}")
            parts.append(f"交给后文：{_clip_text(last_arc.get('handoff_to_next') or last_arc.get('payoff_for_next') or '', 500)}")
            open_threads = last_arc.get("must_remain_open") or []
            if open_threads:
                parts.append(f"上一卷未闭合问题：{_list_preview(open_threads, 8)}")
        last_chapter = (await db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id, Chapter.volume_id == prev_volume.id)
            .order_by(Chapter.chapter_number.desc(), Chapter.updated_at.desc())
            .limit(1)
        )).scalar_one_or_none()
        if last_chapter:
            parts.append(f"上一卷最后章节：第{last_chapter.chapter_number}章《{last_chapter.title or ''}》")
            if last_chapter.connects_to:
                parts.append(f"上一卷章末状态：{_clip_text(last_chapter.connects_to, 500)}")
            if last_chapter.hook:
                parts.append(f"上一卷最后钩子：{_clip_text(last_chapter.hook, 300)}")
            state = _parse_state_snapshot(last_chapter.story_state_snapshot or "")
            for label, key in [
                ("人物/事实变化", "facts"),
                ("下卷必须承接", "next_must_follow"),
                ("物件状态", "object_states"),
                ("外部压力", "external_pressures"),
            ]:
                value = state.get(key)
                if value:
                    parts.append(f"{label}：{_list_preview(value, 8)}")
    else:
        parts.append("【上一卷】无（本卷是第一卷或缺少上一卷）")

    parts.append(f"【当前卷】第{volume.volume_number}卷《{volume.title}》")
    if volume.summary:
        parts.append(f"当前卷摘要：{_clip_text(volume.summary, 500)}")

    if next_volume:
        parts.append(f"【下一卷预告】第{next_volume.volume_number}卷《{next_volume.title}》")
        if next_volume.summary:
            parts.append(f"下一卷摘要：{_clip_text(next_volume.summary, 500)}")
        if next_volume.outline:
            parts.append(f"下一卷大纲要点：{_clip_text(next_volume.outline, 500)}")
    else:
        parts.append("【下一卷预告】无（本卷可能是当前最后一卷）")

    return _clip_text("\n".join(p for p in parts if p), 3200)

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
    if prev_arc.get("continuity_chain"):
        parts.append(f"【上一弧线因果链】{_clip_text(prev_arc.get('continuity_chain', ''), 500)}")
    if prev_arc.get("handoff_to_next") or prev_arc.get("payoff_for_next"):
        parts.append(f"【上一弧线交给下一弧线】{_clip_text(prev_arc.get('handoff_to_next') or prev_arc.get('payoff_for_next') or '', 500)}")
    if next_arc and (next_arc.get("handoff_from_previous") or next_arc.get("dependence_on_previous")):
        parts.append(f"【当前弧线必须接住】{_clip_text(next_arc.get('handoff_from_previous') or next_arc.get('dependence_on_previous') or '', 500)}")
    if prev_arc.get("arc_steps"):
        steps = prev_arc.get("arc_steps") or []
        if isinstance(steps, list) and steps:
            tail_steps = steps[-2:]
            parts.append("【上一弧线最后变化台阶】")
            for step in tail_steps:
                if isinstance(step, dict):
                    parts.append(
                        f"- {step.get('step_name', '')}：后果={_clip_text(step.get('consequence', ''), 180)}；必须带入={_clip_text(step.get('carry_forward', ''), 180)}"
                    )
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
            f"下一弧线接收物：{_clip_text(next_arc.get('handoff_from_previous', ''), 400)}",
            f"下一弧线起点：{_clip_text(next_arc.get('description', ''), 400)}",
        ])
    return "\n".join(p for p in parts if p)

def _format_previous_arc_last_hook(chapter: Chapter | None) -> str:
    if not chapter:
        return ""
    parts = [f"第{chapter.chapter_number}章《{chapter.title or ''}》"]
    if chapter.hook:
        parts.append(f"正文[HOOK]：{_clip_text(chapter.hook, 300)}")
    if chapter.connects_to:
        parts.append(f"章末交接：{_clip_text(chapter.connects_to, 300)}")
    hook_design = {}
    if isinstance(chapter.blueprint, dict):
        hook_design = chapter.blueprint.get("hook_design") or {}
    if not hook_design and isinstance(chapter.continuity_checks, dict):
        hook_design = chapter.continuity_checks.get("hook_design") or {}
    if hook_design:
        parts.append(f"钩子设计：{_clip_text(json.dumps(hook_design, ensure_ascii=False), 300)}")
    continuity_to_next = chapter.continuity_to_next or []
    if continuity_to_next:
        parts.append(f"下章必须承接：{_list_preview(continuity_to_next, 5)}")
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
    volume.arc_continuity_index = _build_arc_continuity_index(arcs)
    volume.arc_bridge_checks = _build_arc_bridge_checks(arcs)

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
    chapter.connects_from = (
        blueprint.get("connects_from")
        or (prev_chapter.connects_to if prev_chapter and prev_chapter.connects_to else chapter.connects_from)
    )
    if bridge_context and (not chapter.connects_from or chapter.connects_from.startswith("无")):
        chapter.connects_from = bridge_context
    chapter.connects_to = blueprint.get("connects_to") or blueprint.get("ending_hook", chapter.connects_to or "")
    chapter.key_events = blueprint.get("must_include", chapter.key_events or [])
    chapter.minor_events = blueprint.get("foreshadowing_tasks", chapter.minor_events or [])
    continuity_checks = blueprint.get("continuity_checks", {}) or {}
    continuity_checks.update({
        "chapter_function": blueprint.get("chapter_function", ""),
        "arc_step_refs": blueprint.get("arc_step_refs", []),
        "continuity_from_previous": blueprint.get("continuity_from_previous", []),
        "state_delta": blueprint.get("state_delta", {}),
        "continuity_to_next": blueprint.get("continuity_to_next", []),
        "opening_requirements": blueprint.get("opening_requirements", []),
        "prewrite_diagnosis_seed": blueprint.get("prewrite_diagnosis_seed", {}),
        "indispensability_check": blueprint.get("indispensability_check", {}),
        "hook_design": blueprint.get("hook_design", {}),
        "character_voice_constraints": blueprint.get("character_voice_constraints", {}),
        "information_reveal_plan": blueprint.get("information_reveal_plan", {}),
        "repair_priority_hint": blueprint.get("repair_priority_hint", ""),
    })
    chapter.continuity_checks = continuity_checks
    chapter.arc_step_refs = blueprint.get("arc_step_refs", chapter.arc_step_refs or [])
    chapter.continuity_from_previous = blueprint.get("continuity_from_previous", chapter.continuity_from_previous or [])
    chapter.state_delta = blueprint.get("state_delta", chapter.state_delta or {})
    chapter.continuity_to_next = blueprint.get("continuity_to_next", chapter.continuity_to_next or [])
    chapter.causality_links = blueprint.get("causality_links", [])
    chapter.foreshadowing_tasks = blueprint.get("foreshadowing_tasks", [])
    chapter.rhythm_profile = blueprint.get("rhythm_profile", {})
    chapter.scene_count = len(blueprint.get("scene_beats", []))
    chapter.narrative_line = chapter.narrative_line or "main"
    return blueprint

async def _do_expand_volume_arcs(
    project_id: str,
    volume_id: str,
    arc_strategy: str = "标准长篇策划",
    arc_density: str = "标准弧线",
    style_focus: str = "主线清晰，角色自然成长",
    length_control: str = "按全书体量和本卷复杂度自主判断",
    clear_existing_chapters: bool = False,
    task_id: str = "",
) -> dict:
    async with async_session() as db:
        if task_id:
            update_progress(task_id, 0.08, "正在读取卷、角色和势力上下文", {"stage": "loading_context", "volume_id": volume_id})
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
        volume_continuity_context = await _format_volume_continuity_context(db, project_id, volume)
        snapshot = {
            "title": project.title,
            "genre": project.genre,
            "volume_title": volume.title,
            "volume_outline": volume.outline or "",
            "chapter_count": volume.chapter_count,
            "chars_summary": chars_summary,
            "facs_summary": facs_summary,
            "volume_continuity_context": volume_continuity_context,
            "arc_strategy": arc_strategy,
            "arc_density": arc_density,
            "style_focus": style_focus,
            "length_control": length_control,
            "writing_style_guidance": _format_project_writing_guidance(project, await _active_writing_style_skill(db, project), "outline"),
        }

    ai = AIService()
    if task_id:
        update_progress(task_id, 0.22, "AI 正在拆分本卷弧线并处理跨卷承接", {"stage": "generating_arcs", "volume_id": volume_id})
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
        writing_style_guidance=snapshot["writing_style_guidance"],
        volume_continuity_context=snapshot["volume_continuity_context"],
    )
    if task_id:
        update_progress(task_id, 0.72, "正在校验弧线连续性和交接物", {"stage": "validating_arcs", "volume_id": volume_id})
    arcs = _normalize_narrative_arc_payload(arcs)
    arc_quality = _score_arc_quality(arcs)

    async with async_session() as db:
        if task_id:
            update_progress(task_id, 0.86, "正在写入弧线规划和质量检查结果", {"stage": "saving_arcs", "volume_id": volume_id, "arc_quality": arc_quality})
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume:
            raise RuntimeError("卷已被重新生成或删除，请刷新页面后重新展开弧线")
        cleared_chapters = 0
        if clear_existing_chapters:
            cleared_chapters = await _clear_volume_chapters(db, project_id, volume_id)
        volume.narrative_arcs = arcs
        volume.arc_continuity_index = _build_arc_continuity_index(arcs)
        bridge_checks = _build_arc_bridge_checks(arcs)
        for check in bridge_checks:
            check["quality_gate"] = _arc_quality_gate(arc_quality, check.get("arc_index", 0))
        volume.arc_bridge_checks = bridge_checks
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        if project:
            project.project_schema_mode = "continuity_v1"
            project.arc_generation_version = "continuity_v1"
            notes = project.continuity_upgrade_notes or {}
            notes["arc_generation"] = "用户主动重新生成弧线后启用 continuity_v1；旧正文和旧章节摘要未自动重写。"
            notes["last_arc_quality"] = arc_quality
            notes["last_volume_continuity_context"] = snapshot["volume_continuity_context"]
            notes["prompt_version"] = PROMPT_VERSION
            project.continuity_upgrade_notes = notes
        await db.commit()
        if task_id:
            update_progress(task_id, 1, "卷弧线展开完成", {
                "stage": "completed",
                "volume_id": volume_id,
                "arc_count": len(arcs),
                "cleared_chapters": cleared_chapters,
                "arc_quality": arc_quality,
            })
        return {"arcs": arcs, "cleared_chapters": cleared_chapters, "arc_quality": arc_quality}

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
        arcs = _normalize_narrative_arc_payload(arcs)
        revised = arcs[arc_index]
        volume.narrative_arcs = arcs
        volume.arc_continuity_index = _build_arc_continuity_index(arcs)
        arc_quality = _score_arc_quality(arcs)
        bridge_checks = _build_arc_bridge_checks(arcs)
        for check in bridge_checks:
            check["quality_gate"] = _arc_quality_gate(arc_quality, check.get("arc_index", 0))
        volume.arc_bridge_checks = bridge_checks
        if project:
            notes = project.continuity_upgrade_notes or {}
            notes["last_arc_quality"] = arc_quality
            notes["last_arc_revise"] = {
                "volume_id": volume_id,
                "arc_index": arc_index,
                "action": action,
            }
            project.continuity_upgrade_notes = notes
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
        "arc_quality": arc_quality,
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
        previous_arc_last_hook = ""
        start_chapter_number = volume.chapter_range_start or 1
        if arc_index > 0:
            bridge_context = await _build_arc_bridge_context(db, volume, arc_index)
            prev_arc = volume.narrative_arcs[arc_index - 1]
            prev_last_chapter = (await db.execute(
                select(Chapter).where(Chapter.volume_id == volume_id, Chapter.arc_name == prev_arc.get("name", ""))
                .order_by(Chapter.chapter_number.desc()).limit(1)
            )).scalar_one_or_none()
            previous_arc_last_hook = _format_previous_arc_last_hook(prev_last_chapter)
            if bridge_context:
                previous_arc_ending = bridge_context
            elif prev_last_chapter and prev_last_chapter.connects_to:
                previous_arc_ending = prev_last_chapter.connects_to
            elif prev_last_chapter and prev_last_chapter.summary:
                previous_arc_ending = prev_last_chapter.summary
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
            "previous_arc_last_hook": previous_arc_last_hook,
            "start_chapter_number": start_chapter_number,
            "chars_summary": chars_summary,
            "facs_summary": facs_summary,
            "writing_style_guidance": _format_project_writing_guidance(project, await _active_writing_style_skill(db, project), "outline"),
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
        writing_style_guidance=snapshot["writing_style_guidance"],
        arc_steps=snapshot["arc"].get("arc_steps", []),
        continuity_chain=snapshot["arc"].get("continuity_chain", ""),
        handoff_from_previous=snapshot["arc"].get("handoff_from_previous", ""),
        handoff_to_next=snapshot["arc"].get("handoff_to_next", ""),
        arc_type=snapshot["arc"].get("arc_type", ""),
        closure_level=snapshot["arc"].get("closure_level", ""),
        must_remain_open=snapshot["arc"].get("must_remain_open", []),
        bridge_chapter_plan=snapshot["arc"].get("bridge_chapter_plan", {}),
        protagonist_continuity_state=snapshot["arc"].get("protagonist_continuity_state", {}),
        character_lifecycle_updates=snapshot["arc"].get("character_lifecycle_updates", []),
        faction_lifecycle_updates=snapshot["arc"].get("faction_lifecycle_updates", []),
        blueprint_repair_targets=snapshot["arc"].get("blueprint_repair_targets", []),
        previous_arc_last_hook=snapshot["previous_arc_last_hook"],
    )

    async with async_session() as db:
        volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
        if not volume or not volume.narrative_arcs:
            raise RuntimeError("卷已被重新生成或删除，请刷新页面后重新展开章节")
        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
        current_arcs = volume.narrative_arcs or []
        if arc_index >= len(current_arcs) or current_arcs[arc_index].get("name", "") != snapshot["arc_name"]:
            raise RuntimeError("弧线已变化，请刷新页面后重新展开章节")
        old_chapters = (await db.execute(select(Chapter).where(Chapter.project_id == project_id, Chapter.volume_id == volume_id, Chapter.arc_name == snapshot["arc_name"]))).scalars().all()
        await _delete_chapters_with_related(db, project_id, old_chapters)
        for idx, node_data in enumerate(nodes):
            connects_from = _safe_str(node_data.get("connects_from", ""))
            if idx == 0 and arc_index > 0 and (not connects_from or connects_from.startswith("无")):
                connects_from = snapshot["previous_arc_ending"]
                node_data["connects_from"] = connects_from
            blueprint_quality_gate = _chapter_blueprint_gate(node_data, idx, arc_index, snapshot["previous_arc_ending"])
            continuity_from_previous = node_data.get("continuity_from_previous", [])
            continuity_to_next = node_data.get("continuity_to_next", [])
            state_delta = node_data.get("state_delta", {})
            arc_step_refs = node_data.get("arc_step_refs", [])
            entry_gate_checks = node_data.get("entry_gate_checks", {})
            chapter_function = node_data.get("chapter_function", "")
            opening_requirements = node_data.get("opening_requirements", [])
            indispensability_check = node_data.get("indispensability_check", {})
            hook_design = node_data.get("hook_design", {})
            character_voice_constraints = node_data.get("character_voice_constraints", {})
            information_reveal_plan = node_data.get("information_reveal_plan", {})
            repair_priority_hint = node_data.get("repair_priority_hint", "")
            causality_links = node_data.get("causality_links") or [
                {
                    "cause": _safe_str(connects_from),
                    "effect": _safe_str(node_data.get("connects_to", "")),
                    "source": "connects_from",
                    "target": "connects_to",
                }
            ]
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
                    "prompt_version": PROMPT_VERSION,
                    "chapter_function": chapter_function,
                    "opening_state": node_data.get("connects_from", ""),
                    "summary": node_data.get("summary", ""),
                    "scene_beats": node_data.get("scene_beats", []),
                    "ending_hook": node_data.get("connects_to", ""),
                    "arc_step_refs": arc_step_refs,
                    "continuity_from_previous": continuity_from_previous,
                    "state_delta": state_delta,
                    "continuity_to_next": continuity_to_next,
                    "entry_gate_checks": entry_gate_checks,
                    "opening_requirements": opening_requirements,
                    "indispensability_check": indispensability_check,
                    "hook_design": hook_design,
                    "character_voice_constraints": character_voice_constraints,
                    "information_reveal_plan": information_reveal_plan,
                    "repair_priority_hint": repair_priority_hint,
                    "blueprint_quality_gate": blueprint_quality_gate,
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
                    "previous_arc_last_hook": snapshot["previous_arc_last_hook"] if idx == 0 and arc_index > 0 else "",
                },
                continuity_checks={
                    "chapter_function": chapter_function,
                    "arc_step_refs": arc_step_refs,
                    "continuity_from_previous": continuity_from_previous,
                    "state_delta": state_delta,
                    "continuity_to_next": continuity_to_next,
                    "entry_gate_checks": entry_gate_checks,
                    "opening_requirements": opening_requirements,
                    "indispensability_check": indispensability_check,
                    "hook_design": hook_design,
                    "character_voice_constraints": character_voice_constraints,
                    "information_reveal_plan": information_reveal_plan,
                    "repair_priority_hint": repair_priority_hint,
                    "blueprint_quality_gate": blueprint_quality_gate,
                },
                arc_step_refs=arc_step_refs,
                continuity_from_previous=continuity_from_previous,
                state_delta=state_delta,
                continuity_to_next=continuity_to_next,
                causality_links=causality_links,
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
        if project:
            project.project_schema_mode = "continuity_v1"
            project.chapter_blueprint_version = "continuity_v1"
            notes = project.continuity_upgrade_notes or {}
            notes["chapter_blueprint"] = "用户主动展开章节后启用 continuity_v1 蓝图；旧正文未自动重写。"
            project.continuity_upgrade_notes = notes
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
            "writing_style_guidance": _format_project_writing_guidance(project, await _active_writing_style_skill(db, project), "outline"),
        }

    ai = AIService()
    data = await ai.generate_outline_plan(
        snapshot["title"],
        snapshot["genre"],
        snapshot["story_brief"],
        snapshot["core_theme"],
        snapshot["target_total_words"],
        chars_summary,
        facs_summary,
        writing_style_guidance=snapshot["writing_style_guidance"],
    )
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
            "writing_style_guidance": _format_project_writing_guidance(project, await _active_writing_style_skill(db, project), "outline"),
        }
    ai = AIService()
    return await ai.generate_outline_plan(
        snapshot["title"],
        snapshot["genre"],
        snapshot["story_brief"],
        snapshot["core_theme"],
        snapshot["target_total_words"],
        chars_summary,
        facs_summary,
        writing_style_guidance=snapshot["writing_style_guidance"],
    )

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

async def expand_volume_arcs(project_id: str, volume_id: str, body: ExpandVolumeArcsRequest | None = None, user: User = Depends(get_current_user)):
    import uuid as _uuid
    body = body or ExpandVolumeArcsRequest()
    task_id = str(_uuid.uuid4())
    start_task(
        _do_expand_volume_arcs(project_id, volume_id, body.arc_strategy, body.arc_density, body.style_focus, body.length_control, body.clear_existing_chapters, task_id),
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
        task_id=task_id,
    )
    return {"task_id": task_id}

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

async def generate_outline(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_volumes(project_id), "generate_outline", project_id)
    return {"task_id": task_id}

async def generate_outline_draft(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_outline_draft(project_id), "generate_outline_draft", project_id)
    return {"task_id": task_id}

async def generate_story_bible(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_story_bible(project_id), "generate_story_bible", project_id)
    return {"task_id": task_id}

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
