from app.services.wizard.common import *

ROLE_TYPE_ALIASES = {
    "protagonist": "主角",
    "hero": "主角",
    "main": "主角",
    "antagonist": "反派",
    "villain": "反派",
    "supporting": "配角",
    "side": "配角",
    "sidekick": "配角",
    "mentor": "导师",
    "master": "导师",
    "love_interest": "恋人",
    "love interest": "恋人",
    "comic_relief": "搞笑担当",
    "other": "其他",
}

FACTION_TYPE_ALIASES = {
    "organization": "组织",
    "org": "组织",
    "sect": "门派",
    "clan": "家族",
    "family": "家族",
    "company": "公司",
    "guild": "公会",
    "government": "官方",
    "official": "官方",
    "school": "学院",
    "other": "其他",
}

CHARACTER_FIELDS = {
    "name",
    "role_type",
    "personality",
    "background",
    "motivation",
    "behavior_pattern",
    "language_style",
    "emotional_expression",
    "appearance",
    "primary_faction_id",
    "faction_rank",
    "inner_conflict",
    "language_fingerprint",
    "relationship_dynamics",
    "faction_history",
    "growth_arc",
    "growth_arc_preset",
    "growth_stages",
    "relationships",
    "current_state",
    "first_appeared_chapter",
    "first_appeared_title",
    "character_class",
}

FACTION_FIELDS = {
    "name",
    "faction_type",
    "description",
    "headquarters",
    "territory",
    "core_creed",
    "hierarchy",
    "notable_members",
    "faction_timeline",
    "emblem_description",
    "color_scheme",
    "core_conflict_of_interest",
    "internal_faction_cracks",
    "reputation_and_reality",
    "strength_trajectory",
    "sort_order",
}

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

async def generate_world(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_world(project_id), "generate_world", project_id)
    return {"task_id": task_id}

async def generate_world_draft(project_id: str, user: User = Depends(get_current_user)):
    task_id = start_task(_do_generate_world_draft(project_id), "generate_world_draft", project_id)
    return {"task_id": task_id}

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

async def _do_generate_characters(project_id: str, char_count: int, faction_count: int, task_id: str = "") -> dict:
    async with async_session() as db:
        if task_id:
            update_progress(task_id, 0.06, "正在读取项目与既有角色", {"stage": "loading_context"})
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
    if task_id:
        update_progress(task_id, 0.20, "AI 正在生成角色档案", {"stage": "generating_characters", "char_count": char_count})
    chars_data = await ai.generate_characters(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], char_count, existing_characters_summary)
    if task_id:
        update_progress(task_id, 0.52, "AI 正在生成势力与关系矩阵", {"stage": "generating_factions", "faction_count": faction_count})
    facs_result = await ai.generate_factions(snapshot["title"], snapshot["genre"], snapshot["story_brief"], snapshot["core_theme"], faction_count)

    async with async_session() as db:
        if task_id:
            update_progress(task_id, 0.74, "正在写入角色、势力和关系", {"stage": "saving_entities"})
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
        saved_characters = 0
        for cdata in chars_data:
            name = cdata.get("name", "")
            key = _normalize_entity_name(name)
            if not key or key in seen_char_names:
                continue
            seen_char_names.add(key)
            await _upsert_character(db, project_id, cdata, character_by_name)
            saved_characters += 1

        project.wizard_step = max(project.wizard_step, 3)
        await db.commit()
        result = {"success": True, "character_count": saved_characters, "faction_count": len(faction_map), "relation_count": len(cross_matrix), "generation_mode": "segmented"}
        if task_id:
            update_progress(task_id, 1, "角色势力生成完成", {"stage": "completed", **result})
        return result

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

async def generate_characters(project_id: str, body: GenerateRequest, user: User = Depends(get_current_user)):
    task_id = str(uuid.uuid4())
    start_task(
        _do_generate_characters(project_id, body.char_count, body.faction_count, task_id),
        "generate_characters",
        project_id,
        {"char_count": body.char_count, "faction_count": body.faction_count, "generation_mode": "segmented"},
        task_id=task_id,
    )
    return {"task_id": task_id}

async def generate_characters_draft(project_id: str, body: GenerateRequest, user: User = Depends(get_current_user)):
    task_id = start_task(
        _do_generate_characters_draft(project_id, body.char_count, body.faction_count),
        "generate_characters_draft",
        project_id,
        {"char_count": body.char_count, "faction_count": body.faction_count},
    )
    return {"task_id": task_id}
