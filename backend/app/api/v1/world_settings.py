from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.world_setting import WorldSetting
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/world-setting", tags=["world-setting"])


class UpdateWorldSettingRequest(BaseModel):
    geography: dict | None = None
    social_structure: dict | None = None
    power_system: dict | None = None
    history: dict | None = None
    culture: dict | None = None
    special_rules: dict | None = None
    world_logic: dict | None = None
    hard_rules: list[str] | None = None
    tone_rules: list[str] | None = None
    constraints: list[str] | None = None


@router.get("")
async def get_world_setting(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))
    ws = result.scalar_one_or_none()
    if not ws:
        ws = WorldSetting(project_id=project_id)
        db.add(ws)
        await db.flush()
    return {"world_setting": ws}


@router.put("")
async def update_world_setting(
    project_id: str, body: UpdateWorldSettingRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WorldSetting).where(WorldSetting.project_id == project_id))
    ws = result.scalar_one_or_none()
    if not ws:
        ws = WorldSetting(project_id=project_id)
        db.add(ws)
        await db.flush()
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(ws, field, value)
    await db.flush()
    return {"world_setting": ws}
