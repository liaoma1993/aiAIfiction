from app.services.wizard.common import *
from app.services.wizard.outline_arcs import (
    _arc_index,
    _build_arc_bridge_context,
    _generate_chapter_blueprint,
    _normalize_volume_arc_chapters,
    _refresh_volume_arc_bridges,
)
from app.services.wizard.world_entities import _normalize_role_type

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
    previous_hook: str,
    story_state_snapshot: str,
    controls: dict,
) -> tuple[str, dict | None]:
    if not controls.get("auto_quality_check", False):
        return content, None
    review = await ai.audit_chapter(previous_ending, previous_hook or "", story_state_snapshot, content)
    if controls.get("auto_light_fix", False) and _quality_needs_fix(review):
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
            second_review = await ai.audit_chapter(previous_ending, previous_hook or "", story_state_snapshot, content)
            if isinstance(second_review, dict):
                second_review["light_fix_applied"] = True
                second_review["before_fix"] = review
            review = second_review
    return content, review

async def _run_prewrite_diagnosis(
    ai: AIService,
    project: Project,
    chapter: Chapter,
    vol: Volume | None,
    previous_ending: str,
    story_state_snapshot: str,
    chars_summary: str,
    facs_summary: str,
) -> dict:
    return await ai.diagnose_chapter_before_write(
        project.title,
        project.genre,
        chapter.chapter_number,
        chapter.title or "",
        vol.outline if vol else "",
        {
            "summary": chapter.summary or "",
            "blueprint": chapter.blueprint or {},
            "continuity": json.loads(_format_chapter_continuity_payload(chapter)),
        },
        previous_ending,
        story_state_snapshot,
        chars_summary,
        facs_summary,
    )

def _format_prewrite_diagnosis_guidance(diagnosis: dict | None) -> str:
    if not isinstance(diagnosis, dict):
        return ""
    blocking = diagnosis.get("blocking_issues") if isinstance(diagnosis.get("blocking_issues"), list) else []
    warnings = diagnosis.get("soft_warnings") if isinstance(diagnosis.get("soft_warnings"), list) else []
    must_fix = diagnosis.get("must_fix_before_write") if isinstance(diagnosis.get("must_fix_before_write"), list) else []
    safe_start = diagnosis.get("safe_starting_point") or ""
    if not blocking and not warnings and not must_fix and not safe_start:
        return ""
    parts = ["【写作前置诊断修复要求】"]
    if blocking:
        parts.append("系统发现以下连续性缺口，本次写正文必须先修复，不能忽略：")
        for idx, item in enumerate(blocking[:5], start=1):
            if isinstance(item, dict):
                parts.append(f"{idx}. 类型：{item.get('type', 'blocking')}；问题：{item.get('problem', '')}；修复：{item.get('fix', '')}")
            else:
                parts.append(f"{idx}. {item}")
    if must_fix:
        parts.append("写正文前必须落实：")
        parts.extend([f"- {x}" for x in must_fix[:6]])
    if safe_start:
        parts.append(f"建议开场落点：{safe_start}")
    if warnings:
        parts.append("软提醒：")
        for idx, item in enumerate(warnings[:4], start=1):
            if isinstance(item, dict):
                parts.append(f"{idx}. {item.get('problem', '')}；建议：{item.get('fix', '')}")
            else:
                parts.append(f"{idx}. {item}")
    parts.append("执行规则：正文开场必须接住上述缺口，再推进原章节蓝图；不得把诊断内容写成旁白说明或列表。")
    return "\n".join(p for p in parts if p)

def _prewrite_should_block(controls: dict | None) -> bool:
    if not isinstance(controls, dict):
        return False
    return bool(controls.get("strict_prewrite_check") or controls.get("block_on_prewrite_failure"))

def _prewrite_ai_enabled(controls: dict | None) -> bool:
    if not isinstance(controls, dict):
        return False
    value = controls.get("auto_prewrite_check")
    if value is True:
        return bool(controls.get("strict_prewrite_check") or controls.get("deep_prewrite_check"))
    return str(value or "").lower() in {"ai", "deep", "strict", "精修", "深度"}

def _run_rule_prewrite_diagnosis(chapter: Chapter, previous_ending: str, story_state_snapshot: str) -> dict:
    blocking = []
    warnings = []
    if not (chapter.summary or "").strip() and not chapter.blueprint:
        blocking.append({
            "type": "missing_blueprint",
            "problem": "章节缺少概要或蓝图，模型只能凭空续写。",
            "fix": "先生成章节蓝图，或补充本章目标、开场承接、关键事件和章末钩子。",
        })
    if chapter.chapter_number and chapter.chapter_number > 1 and not (previous_ending or "").strip():
        blocking.append({
            "type": "missing_previous_state",
            "problem": "缺少上一章结尾或上承状态。",
            "fix": "补充上一章结尾、上一章钩子或本章 connects_from。",
        })
    continuity = {}
    try:
        continuity = json.loads(_format_chapter_continuity_payload(chapter))
    except Exception:
        continuity = {}
    if chapter.chapter_number and chapter.chapter_number > 1 and not (
        continuity.get("connects_from") or continuity.get("opening_requirements") or continuity.get("entry_gate_checks")
    ):
        warnings.append({
            "type": "weak_opening_contract",
            "problem": "本章缺少明确开场承接要求，可能写成跳场。",
            "fix": "正文开头直接回应上一章结尾、上章钩子或当前压力。",
        })
    if not (chapter.hook or continuity.get("hook_design") or continuity.get("connects_to")):
        warnings.append({
            "type": "weak_hook_contract",
            "problem": "本章章末钩子约束较弱。",
            "fix": "写作时必须落到具体消息、动作、物件、来人或一句话。",
        })
    can_write = len(blocking) == 0
    return {
        "can_write": can_write,
        "mode": "rule",
        "blocking_issues": blocking,
        "soft_warnings": warnings,
        "must_fix_before_write": [],
        "safe_starting_point": continuity.get("connects_from") or (previous_ending[-240:] if previous_ending else ""),
        "context_ready": {
            "has_previous": bool(previous_ending),
            "has_state_snapshot": bool(story_state_snapshot),
            "has_blueprint": bool(chapter.blueprint),
            "has_summary": bool(chapter.summary),
        },
    }

async def _extract_and_apply_state(db: AsyncSession, project_id: str, chapter: Chapter, content: str) -> dict:
    project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    volume = (await db.execute(select(Volume).where(Volume.id == chapter.volume_id))).scalar_one_or_none() if chapter.volume_id else None
    prev = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)
    ai = AIService()
    result = await ai.summarize_state(
        story_context={
            "project": {
                "id": project_id,
                "title": project.title if project else "",
                "genre": project.genre if project else "",
                "story_brief": _clip_context(_wizard_story_brief(project), 900) if project else "",
                "core_theme": project.core_theme if project else "",
            },
            "previous_chapter_state": _clip_context(prev.story_state_snapshot or "", 1600) if prev else "",
        },
        chapter_context={
            "current_chapter": {
                "chapter_number": chapter.chapter_number,
                "title": chapter.title or "",
                "summary": _clip_context(chapter.summary or "", 1600),
                "arc_name": chapter.arc_name or "",
                "connects_from": _clip_context(chapter.connects_from or "", 700),
                "connects_to": _clip_context(chapter.connects_to or "", 700),
                "hook": chapter.hook or "",
                "blueprint": _compact_json(chapter.blueprint or {}, 2500),
            },
            "current_volume": {
                "volume_number": volume.volume_number if volume else None,
                "title": volume.title if volume else "",
                "summary": _clip_context((volume.summary or volume.outline or "") if volume else "", 1200),
            },
            "recent_chapters": [
                {
                    "chapter_number": prev.chapter_number,
                    "title": prev.title or "",
                    "hook": prev.hook or "",
                    "ending": _clip_context((prev.content or "")[-600:], 600),
                }
            ] if prev else [],
        },
        content=_clip_context(content, 18000),
    )
    chapter.story_state_snapshot = json.dumps(result, ensure_ascii=False)[:3000]
    chapter.relationship_changes = result.get("relationship_changes", []) if isinstance(result.get("relationship_changes", []), list) else []
    chapter.object_states = result.get("object_states", []) if isinstance(result.get("object_states", []), list) else []
    chapter.external_pressures = result.get("external_pressures", []) if isinstance(result.get("external_pressures", []), list) else []
    chapter.opening_requirements_for_next = result.get("opening_requirements_for_next", []) if isinstance(result.get("opening_requirements_for_next", []), list) else []
    if isinstance(result.get("causality_links"), list):
        chapter.causality_links = result.get("causality_links", [])

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

        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs = facs_result.scalars().all()

        prev_chapter = await _get_previous_chapter(db, project_id, str(chapter.volume_id) if chapter.volume_id else None, chapter.chapter_number)

        previous_ending = "无（这是第一章）"
        previous_hook = ""
        story_state_snapshot = "无（这是第一章）"
        if prev_chapter and prev_chapter.content:
            opening = prev_chapter.content[:300] if len(prev_chapter.content) > 300 else prev_chapter.content
            ending = prev_chapter.content[-500:] if len(prev_chapter.content) > 500 else prev_chapter.content
            previous_ending = f"【开头】{opening}\n\n……\n\n【结尾】{ending}"
            if prev_chapter.hook:
                previous_hook = prev_chapter.hook
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
        chars_summary = _build_budgeted_character_summary(chars, chapter, controls)
        facs_summary = _build_budgeted_faction_summary(facs, chapter, controls)
        target_words = controls.get("target_words") or chapter.target_words or 3000
        if not chapter.blueprint:
            await _generate_chapter_blueprint(db, project_id, chapter, prev_chapter, vol)
        ai = AIService()
        prewrite_guidance = ""
        if controls.get("auto_prewrite_check", "rule"):
            diagnosis = _run_rule_prewrite_diagnosis(chapter, previous_ending, story_state_snapshot)
            if _prewrite_ai_enabled(controls):
                diagnosis = await _run_prewrite_diagnosis(
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
            checks["prewrite_diagnosis"] = diagnosis
            chapter.continuity_checks = checks
            if diagnosis.get("can_write") is False and diagnosis.get("blocking_issues"):
                prewrite_guidance = _format_prewrite_diagnosis_guidance(diagnosis)
                checks["prewrite_diagnosis_action"] = "injected_into_writing_prompt"
                chapter.continuity_checks = checks
                if _prewrite_should_block(controls):
                    await db.commit()
                    raise RuntimeError(f"写作前置诊断未通过：{json.dumps(diagnosis.get('blocking_issues'), ensure_ascii=False)[:500]}")
        if controls:
            extra = "；".join([f"{k}:{v}" for k, v in controls.items() if v not in [None, ""]])
            chapter_summary = f"{chapter.summary or ''}\n\n【本次写作控制】{extra}\n{_writing_controls_guidance(controls)}\n【用户要求】{instruction or '无'}"
        else:
            chapter_summary = chapter.summary or instruction or ""
        if prewrite_guidance:
            chapter_summary = f"{chapter_summary}\n\n{prewrite_guidance}"
        chapter_summary = f"{chapter_summary}\n\n【章节连贯性硬约束】\n{_format_chapter_continuity_payload(chapter)}"
        if bridge_context and arc_idx > 0:
            chapter_summary = f"{chapter_summary}\n\n【跨弧线桥接要求】\n{bridge_context}"
        writing_style_guidance = _format_project_writing_guidance(project, await _active_writing_style_skill(db, project), "writing")

        text, hook, new_characters = await ai.write_chapter(
            project.title, project.genre, _wizard_story_brief(project),
            chapter.chapter_number, chapter.title or "", chapter_summary,
            _clip_context(vol.outline if vol else "", _writing_context_limits(controls)["volume"]), chars_summary, facs_summary,
            min_words=target_words, written_so_far=len(chapter.content or ""),
            previous_ending=previous_ending,
            story_state_snapshot=_clip_context(f"{story_state_snapshot}\n\n{bridge_context}", _writing_context_limits(controls)["state"]),
            pov_character=pov_char,
            readability_guidance=_readability_guidance(controls),
            early_grip_guidance=_early_grip_guidance(project, chapter, vol, controls),
            writing_style_guidance=writing_style_guidance,
        )
        quality_review = {}
        if controls.get("auto_quality_check", False):
            text, quality_review = await _review_and_light_fix_chapter(
                ai,
                project,
                chapter,
                text,
                previous_ending,
                previous_hook,
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
        if isinstance(quality_review, dict) and quality_review:
            _save_quality_review_to_chapter(chapter, quality_review)
        chapter.status = _status_after_content_change(chapter.status)
        chapter.version = (chapter.version or 1) + 1
        background_task_types = []
        checks = chapter.continuity_checks or {}
        if controls.get("async_state_extract", True):
            checks["state_extract_status"] = "queued"
            background_task_types.append("extract_state")
        else:
            with db.no_autoflush:
                state_result = await _extract_and_apply_state(db, project_id, chapter, chapter.content)
            checks["state_extract"] = state_result
            checks["state_extract_validation"] = _validate_state_extract_payload(state_result)
        if controls.get("async_quality_check", True) and not controls.get("auto_quality_check", False):
            checks["quality_review_status"] = "queued"
            background_task_types.append("audit_chapter")
        chapter.continuity_checks = checks
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
        background_tasks = {}
        if "extract_state" in background_task_types:
            background_tasks["extract_state"] = start_task(
                _do_extract_state(project_id, str(chapter.id), True),
                "extract_state",
                project_id,
                {"chapter_id": str(chapter.id), "apply": True, "source": "post_write_async"},
            )
        if "audit_chapter" in background_task_types:
            from app.services.wizard.reviews_repairs import _do_audit_chapter

            background_tasks["audit_chapter"] = start_task(
                _do_audit_chapter(project_id, str(chapter.id)),
                "audit_chapter",
                project_id,
                {"chapter_id": str(chapter.id), "source": "post_write_async"},
            )
        return {
            "content": text,
            "hook": hook,
            "new_characters": new_characters,
            "mode": mode,
            "blueprint": chapter.blueprint,
            "write_flow": controls.get("write_flow_mode", "fast"),
            "background_tasks": background_tasks,
            "quality_review": quality_review,
        }

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
        else:
            lines.extend([chapter_head, ""])
        if ch.get("content"):
            lines.append(ch["content"])
        if fmt == "md":
            lines.append("")
        else:
            lines.extend(["", ""])

    data = "\n".join(lines).strip().encode("utf-8")
    media_type = "text/markdown; charset=utf-8" if fmt == "md" else "text/plain; charset=utf-8"
    return data, media_type, fmt

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
                "content": ch.content or "",
                "word_count": ch.word_count or len(ch.content or ""),
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

        facs_result = await db.execute(select(Faction).where(Faction.project_id == project_id))
        facs = facs_result.scalars().all()

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
        writing_style_guidance = _format_project_writing_guidance(project, await _active_writing_style_skill(db, project), "writing")
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
            chars_summary = _build_budgeted_character_summary(chars, ch, write_controls)
            facs_summary = _build_budgeted_faction_summary(facs, ch, write_controls)
            prewrite_guidance = ""
            if write_controls.get("auto_prewrite_check", "rule"):
                diagnosis = _run_rule_prewrite_diagnosis(ch, final_ending, story_state_snapshot)
                if _prewrite_ai_enabled(write_controls):
                    diagnosis = await _run_prewrite_diagnosis(
                        ai,
                        project,
                        ch,
                        volume,
                        final_ending,
                        story_state_snapshot,
                        chars_summary,
                        facs_summary,
                    )
                checks = ch.continuity_checks or {}
                checks["prewrite_diagnosis"] = diagnosis
                ch.continuity_checks = checks
                if diagnosis.get("can_write") is False and diagnosis.get("blocking_issues"):
                    prewrite_guidance = _format_prewrite_diagnosis_guidance(diagnosis)
                    checks["prewrite_diagnosis_action"] = "injected_into_writing_prompt"
                    ch.continuity_checks = checks
                    if _prewrite_should_block(write_controls):
                        raise RuntimeError(f"第{ch.chapter_number}章写作前置诊断未通过：{json.dumps(diagnosis.get('blocking_issues'), ensure_ascii=False)[:500]}")

            pov_char = "主角"
            if ch.characters_in_chapter:
                pov_char = ch.characters_in_chapter[0] if ch.characters_in_chapter else "主角"

            text, hook, new_characters = await ai.write_chapter(
                project.title, project.genre, _wizard_story_brief(project),
                ch.chapter_number, ch.title or "", f"{ch.summary or ''}\n\n{prewrite_guidance}\n\n【本次写作控制】\n{_writing_controls_guidance(write_controls)}\n\n【章节连贯性硬约束】\n{_format_chapter_continuity_payload(ch)}",
                _clip_context(volume.outline or "", _writing_context_limits(write_controls)["volume"]), chars_summary, facs_summary,
                min_words=ch.target_words or 3000, written_so_far=0,
                previous_ending=final_ending,
                story_state_snapshot=_clip_context(story_state_snapshot, _writing_context_limits(write_controls)["state"]),
                pov_character=pov_char,
                readability_guidance=_readability_guidance(write_controls),
                early_grip_guidance=_early_grip_guidance(project, ch, volume, write_controls),
                writing_style_guidance=writing_style_guidance,
            )
            quality_review = {}
            if write_controls.get("auto_quality_check", False):
                text, quality_review = await _review_and_light_fix_chapter(
                    ai,
                    project,
                    ch,
                    text,
                    final_ending,
                    previous_hook,
                    story_state_snapshot,
                    write_controls,
                )
            ch.content = text
            ch.hook = hook
            ch.word_count = len(text)
            if isinstance(quality_review, dict) and quality_review:
                _save_quality_review_to_chapter(ch, quality_review)
            ch.status = "completed"
            total_words += len(text)
            checks = ch.continuity_checks or {}
            if write_controls.get("async_state_extract", True):
                checks["state_extract_status"] = "queued"
            else:
                with db.no_autoflush:
                    state_result = await _extract_and_apply_state(db, project_id, ch, ch.content)
                checks["state_extract"] = state_result
                checks["state_extract_validation"] = _validate_state_extract_payload(state_result)
            if write_controls.get("async_quality_check", True) and not write_controls.get("auto_quality_check", False):
                checks["quality_review_status"] = "queued"
            ch.continuity_checks = checks
            await _refresh_volume_arc_bridges(db, volume)

            # propagate ending to next chapter
            previous_hook = hook or ""
            story_state_snapshot = _build_story_state_snapshot(ch, story_state_snapshot)

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
            await db.commit()
            if write_controls.get("async_state_extract", True):
                start_task(
                    _do_extract_state(project_id, str(ch.id), True),
                    "extract_state",
                    project_id,
                    {"chapter_id": str(ch.id), "apply": True, "source": "batch_write_async"},
                )
            if write_controls.get("async_quality_check", True) and not write_controls.get("auto_quality_check", False):
                from app.services.wizard.reviews_repairs import _do_audit_chapter

                start_task(
                    _do_audit_chapter(project_id, str(ch.id)),
                    "audit_chapter",
                    project_id,
                    {"chapter_id": str(ch.id), "source": "batch_write_async"},
                )

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

async def batch_write_arc(project_id: str, volume_id: str, body: ExpandArcRequest, user: User = Depends(get_current_user)):
    import uuid as _uuid
    task_id = str(_uuid.uuid4())
    body_controls = body.controls or {}
    controls = {
        **body_controls,
        "readability_mode": body.readability_mode,
        "write_flow_mode": body_controls.get("write_flow_mode") or "stable_draft",
        "auto_quality_check": bool(body_controls.get("auto_quality_check", False)),
        "auto_light_fix": bool(body_controls.get("auto_light_fix", False)),
        "async_quality_check": bool(body_controls.get("async_quality_check", False)),
    }
    start_task(
        _do_batch_write_arc(project_id, volume_id, body.arc_index, task_id, body.chapter_ids, body.readability_mode, controls),
        "batch_write_arc",
        project_id,
        {"volume_id": volume_id, "arc_index": body.arc_index, "chapter_ids": body.chapter_ids or [], "readability_mode": body.readability_mode, "controls": controls},
        task_id=task_id,
        timeout=BATCH_WRITE_ARC_TIMEOUT_SECONDS,
    )
    return {"task_id": task_id}

async def write_chapter(project_id: str, chapter_id: str, body: WriteChapterRequest | None = None, user: User = Depends(get_current_user)):
    body = body or WriteChapterRequest()
    task_id = start_task(
        _do_write_chapter(project_id, chapter_id, body.mode, body.instruction, body.controls, body.preview),
        "write_chapter",
        project_id,
        {"chapter_id": chapter_id, "mode": body.mode, "instruction": body.instruction, "controls": body.controls, "preview": body.preview},
    )
    return {"task_id": task_id}

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

async def normalize_volume_chapters(project_id: str, volume_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    volume = (await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))).scalar_one_or_none()
    if not volume:
        raise HTTPException(404, "卷不存在")
    await _normalize_volume_arc_chapters(db, volume)
    await _refresh_volume_arc_bridges(db, volume)
    await db.commit()
    return {"ok": True}

async def extract_state(project_id: str, chapter_id: str, apply: bool = False, user: User = Depends(get_current_user)):
    task_id = start_task(_do_extract_state(project_id, chapter_id, apply), "extract_state", project_id, {"chapter_id": chapter_id, "apply": apply})
    return {"task_id": task_id}

async def _do_extract_state(project_id: str, chapter_id: str, apply_changes: bool = False) -> dict:
    async with async_session() as db:
        chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
        if not chapter or not chapter.content:
            raise RuntimeError("章节不存在或未写入")
        ai = AIService()
        result = await ai.extract_state_changes(chapter.chapter_number, chapter.title or "", chapter.summary or "", chapter.content)
        if apply_changes:
            chapter.story_state_snapshot = json.dumps(result, ensure_ascii=False)[:3000]
            checks = dict(chapter.continuity_checks or {})
            checks["state_extract"] = result
            checks["state_extract_validation"] = _validate_state_extract_payload(result)
            checks["state_extract_status"] = "completed"
            chapter.continuity_checks = checks
            flag_modified(chapter, "continuity_checks")
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

async def apply_state(project_id: str, chapter_id: str, body: ApplyStateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    await _apply_state_payload(db, project_id, chapter, body.payload)
    await db.flush()
    return {"success": True, "state": body.payload}
