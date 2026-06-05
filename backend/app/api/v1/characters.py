from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import re
from app.database import get_db
from app.models.user import User
from app.models.character import Character
from app.models.character_state_snapshot import CharacterStateSnapshot
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/characters", tags=["characters"])


def _normalize_character_name(name: str | None) -> str:
    return re.sub(r"\s+", "", (name or "").strip()).lower()


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


def _normalize_role_type(role_type: str | None) -> str:
    role = (role_type or "配角").strip()
    return ROLE_TYPE_ALIASES.get(role.lower(), ROLE_TYPE_ALIASES.get(role, role))


def _character_completeness_score(char: Character) -> int:
    text_fields = [
        char.personality,
        char.background,
        char.motivation,
        char.behavior_pattern,
        char.language_style,
        char.emotional_expression,
        char.appearance,
        char.growth_arc,
        char.inner_conflict,
        char.language_fingerprint,
    ]
    list_fields = [char.relationship_dynamics, char.faction_history, char.growth_stages, char.relationships]
    return sum(len(x or "") for x in text_fields) + sum(len(x or []) * 20 for x in list_fields)


class CreateCharacterRequest(BaseModel):
    name: str
    role_type: str = "配角"
    personality: str = ""
    background: str = ""
    motivation: str = ""
    growth_stages: list[dict] = []
    primary_faction_id: str | None = None
    faction_rank: str | None = None


class UpdateCharacterRequest(BaseModel):
    name: str | None = None
    role_type: str | None = None
    personality: str | None = None
    background: str | None = None
    motivation: str | None = None
    behavior_pattern: str | None = None
    language_style: str | None = None
    emotional_expression: str | None = None
    appearance: str | None = None
    primary_faction_id: str | None = None
    faction_rank: str | None = None
    growth_arc: str | None = None
    growth_stages: list[dict] | None = None
    relationships: list[dict] | None = None
    current_state: dict | None = None


@router.get("")
async def list_characters(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Character).where(Character.project_id == project_id))
    characters = result.scalars().all()
    by_name: dict[str, Character] = {}
    unnamed: list[Character] = []
    for char in characters:
        key = _normalize_character_name(char.name)
        if not key:
            unnamed.append(char)
            continue
        current = by_name.get(key)
        if not current:
            by_name[key] = char
            continue
        current_score = _character_completeness_score(current)
        next_score = _character_completeness_score(char)
        current_updated = current.updated_at or current.created_at
        next_updated = char.updated_at or char.created_at
        if next_score > current_score or (next_score == current_score and next_updated and current_updated and next_updated > current_updated):
            by_name[key] = char
    deduped = [*by_name.values(), *unnamed]
    for char in deduped:
        normalized = _normalize_role_type(char.role_type)
        if normalized != char.role_type:
            char.role_type = normalized
    deduped.sort(key=lambda c: (str(c.created_at or ""), c.name or ""))
    return {"characters": deduped}


@router.post("")
async def create_character(
    project_id: str, body: CreateCharacterRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    data["role_type"] = _normalize_role_type(data.get("role_type"))
    char = Character(project_id=project_id, **data)
    db.add(char)
    await db.flush()
    return {"character": char}


@router.get("/{character_id}")
async def get_character(project_id: str, character_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Character).where(Character.id == character_id, Character.project_id == project_id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "角色不存在")
    return {"character": char}


@router.put("/{character_id}")
async def update_character(
    project_id: str, character_id: str, body: UpdateCharacterRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Character).where(Character.id == character_id, Character.project_id == project_id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "角色不存在")
    data = body.model_dump(exclude_none=True)
    if "role_type" in data:
        data["role_type"] = _normalize_role_type(data.get("role_type"))
    for field, value in data.items():
        setattr(char, field, value)
    await db.flush()
    return {"character": char}


@router.get("/{character_id}/snapshots")
async def get_snapshots(project_id: str, character_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CharacterStateSnapshot)
        .where(CharacterStateSnapshot.character_id == character_id)
        .order_by(CharacterStateSnapshot.chapter_number)
    )
    return {"snapshots": result.scalars().all()}


class CreateSnapshotRequest(BaseModel):
    chapter_id: str | None = None
    chapter_number: int = 0
    snapshot_label: str = ""
    ability_level: str = ""
    mental_state: str = ""
    faction_id: str | None = None
    faction_rank: str | None = None
    important_items: list[str] = []


@router.post("/{character_id}/snapshots")
async def create_snapshot(
    project_id: str, character_id: str, body: CreateSnapshotRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    snap = CharacterStateSnapshot(character_id=character_id, project_id=project_id, **body.model_dump())
    db.add(snap)
    await db.flush()
    return {"snapshot": snap}
