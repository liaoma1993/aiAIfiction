from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.volume import Volume
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/volumes", tags=["volumes"])


class CreateVolumeRequest(BaseModel):
    volume_number: int
    title: str
    summary: str = ""
    theme: str = ""
    target_words: int = 105000
    default_chapter_words: int = 3500
    chapter_count: int = 30
    chapter_range_start: int
    chapter_range_end: int


class UpdateVolumeRequest(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    summary: str | None = None
    outline: str | None = None
    theme: str | None = None
    target_words: int | None = None
    default_chapter_words: int | None = None
    chapter_count: int | None = None
    tension_curve: list[dict] | None = None
    emotional_arc_description: str | None = None
    narrative_line_distribution: dict | None = None


async def _get_project(project_id: str, user: User, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    return project


@router.get("")
async def list_volumes(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, user, db)
    result = await db.execute(
        select(Volume).where(Volume.project_id == project_id).order_by(Volume.sort_order)
    )
    return {"volumes": result.scalars().all()}


@router.post("")
async def create_volume(
    project_id: str,
    body: CreateVolumeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)
    volume = Volume(project_id=project_id, **body.model_dump())
    db.add(volume)
    await db.flush()
    return {"volume": volume}


@router.put("/{volume_id}")
async def update_volume(
    project_id: str,
    volume_id: str,
    body: UpdateVolumeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)
    result = await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))
    volume = result.scalar_one_or_none()
    if not volume:
        raise HTTPException(404, "卷不存在")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(volume, field, value)
    await db.flush()
    return {"volume": volume}


@router.delete("/{volume_id}")
async def delete_volume(project_id: str, volume_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, user, db)
    result = await db.execute(select(Volume).where(Volume.id == volume_id, Volume.project_id == project_id))
    volume = result.scalar_one_or_none()
    if not volume:
        raise HTTPException(404, "卷不存在")
    await db.delete(volume)
    return {"success": True}
