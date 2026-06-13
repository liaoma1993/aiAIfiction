from app.services.wizard.common import *
from app.services.wizard.world_entities import _normalize_entity_name, _upsert_character, _upsert_faction

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
                style = project.writing_style or {}
                if not isinstance(style, dict):
                    style = {}
                if isinstance(tags, list):
                    style["tags"] = tags
                for key in ["tone_profile", "type_model", "readability_gate", "first_volume_engine", "early_event_chain"]:
                    if draft.get(key) is not None:
                        style[key] = draft.get(key)
                project.writing_style = style
                await db.commit()
    return data

async def project_plan_chat(project_id: str, body: ProjectPlanChatRequest, user: User = Depends(get_current_user)):
    task_id = start_task(_do_project_plan_chat(project_id, body.messages, body.genres, body.current_draft), "project_plan_chat", project_id)
    return {"task_id": task_id}

async def apply_story(project_id: str, body: ApplyStoryRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    project.title = body.title
    project.genre = body.genre
    project.story_brief = body.brief
    project.target_total_words = body.total_words
    existing_style = project.writing_style if isinstance(project.writing_style, dict) else {}
    selected_draft = body.selected_draft or {"title": body.title, "genre": body.genre, "brief": body.brief, "tags": body.tags, "total_words": body.total_words}
    project_meta = {
        key: selected_draft.get(key)
        for key in ["tone_profile", "type_model", "readability_gate", "first_volume_engine", "early_event_chain"]
        if isinstance(selected_draft, dict) and selected_draft.get(key) is not None
    }
    project.writing_style = {
        **existing_style,
        "tags": body.tags,
        **project_meta,
        "wizard_planning_memory": _build_wizard_planning_memory(
            body.planning_messages,
            selected_draft,
            body.planning_suggestions,
        ),
    }
    project.wizard_step = 1
    await db.flush()
    return {"project": project}

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
