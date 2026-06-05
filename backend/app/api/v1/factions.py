from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.faction import Faction, FactionRelation
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/factions", tags=["factions"])

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


def _normalize_faction_type(faction_type: str | None) -> str:
    value = (faction_type or "组织").strip()
    return FACTION_TYPE_ALIASES.get(value.lower(), FACTION_TYPE_ALIASES.get(value, value))


class CreateFactionRequest(BaseModel):
    name: str
    faction_type: str = "组织"
    description: str = ""
    headquarters: str = ""
    territory: str = ""
    core_creed: str = ""
    hierarchy: list[dict] = []


class UpdateFactionRequest(BaseModel):
    name: str | None = None
    faction_type: str | None = None
    description: str | None = None
    headquarters: str | None = None
    territory: str | None = None
    core_creed: str | None = None
    hierarchy: list[dict] | None = None
    notable_members: list[str] | None = None


@router.get("")
async def list_factions(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Faction).where(Faction.project_id == project_id).order_by(Faction.sort_order))
    factions = result.scalars().all()
    for faction in factions:
        normalized = _normalize_faction_type(faction.faction_type)
        if normalized != faction.faction_type:
            faction.faction_type = normalized
    return {"factions": factions}


@router.post("")
async def create_faction(
    project_id: str, body: CreateFactionRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    data = body.model_dump()
    data["faction_type"] = _normalize_faction_type(data.get("faction_type"))
    faction = Faction(project_id=project_id, **data)
    db.add(faction)
    await db.flush()
    return {"faction": faction}


@router.put("/{faction_id}")
async def update_faction(
    project_id: str, faction_id: str, body: UpdateFactionRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Faction).where(Faction.id == faction_id, Faction.project_id == project_id))
    faction = result.scalar_one_or_none()
    if not faction:
        raise HTTPException(404, "势力不存在")
    data = body.model_dump(exclude_none=True)
    if "faction_type" in data:
        data["faction_type"] = _normalize_faction_type(data.get("faction_type"))
    for field, value in data.items():
        setattr(faction, field, value)
    await db.flush()
    return {"faction": faction}


@router.delete("/{faction_id}")
async def delete_faction(project_id: str, faction_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Faction).where(Faction.id == faction_id, Faction.project_id == project_id))
    faction = result.scalar_one_or_none()
    if not faction:
        raise HTTPException(404, "势力不存在")
    await db.delete(faction)
    return {"success": True}
