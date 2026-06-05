from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.chapter import Chapter, ChapterVersion
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/chapters", tags=["chapters"])


@router.get("")
async def list_chapters(project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_number)
    )
    return {"chapters": result.scalars().all()}


@router.get("/{chapter_id}")
async def get_chapter(project_id: str, chapter_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    return {"chapter": chapter}


class UpdateChapterRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    word_count: int | None = None
    target_words: int | None = None
    status: str | None = None
    narrative_line: str | None = None
    tension_actual: int | None = None
    quality_score: int | None = None
    summary: str | None = None
    connects_from: str | None = None
    connects_to: str | None = None
    create_version: bool | None = False
    version_note: str | None = None


class CreateChapterRequest(BaseModel):
    volume_id: str | None = None
    chapter_number: int = 1
    title: str = ""
    summary: str = ""
    target_words: int = 3500


@router.post("")
async def create_chapter(
    project_id: str, body: CreateChapterRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    chapter = Chapter(project_id=project_id, **body.model_dump(), status="writing")
    db.add(chapter)
    await db.flush()
    return {"chapter": chapter}


@router.put("/{chapter_id}")
async def update_chapter(
    project_id: str, chapter_id: str, body: UpdateChapterRequest,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    data = body.model_dump(exclude_none=True)
    create_version = bool(data.pop("create_version", False))
    version_note = data.pop("version_note", None)
    if create_version and chapter.content:
        max_version = await db.scalar(
            select(func.max(ChapterVersion.version_number)).where(ChapterVersion.chapter_id == chapter.id)
        ) or 0
        db.add(ChapterVersion(
            project_id=project_id,
            chapter_id=chapter.id,
            version_number=max_version + 1,
            title=chapter.title or "",
            content=chapter.content or "",
            word_count=chapter.word_count or len(chapter.content or ""),
            source="manual",
            note=version_note or "手动保存前版本",
        ))
    for field, value in data.items():
        setattr(chapter, field, value)
    await db.flush()
    return {"chapter": chapter}


@router.get("/{chapter_id}/versions")
async def list_versions(project_id: str, chapter_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChapterVersion)
        .where(ChapterVersion.project_id == project_id, ChapterVersion.chapter_id == chapter_id)
        .order_by(ChapterVersion.version_number.desc())
    )
    return {"versions": result.scalars().all()}


@router.post("/{chapter_id}/versions")
async def create_version(project_id: str, chapter_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    max_version = await db.scalar(
        select(func.max(ChapterVersion.version_number)).where(ChapterVersion.chapter_id == chapter.id)
    ) or 0
    version = ChapterVersion(
        project_id=project_id,
        chapter_id=chapter.id,
        version_number=max_version + 1,
        title=chapter.title or "",
        content=chapter.content or "",
        word_count=chapter.word_count or len(chapter.content or ""),
        source="manual",
        note="手动快照",
    )
    db.add(version)
    await db.flush()
    return {"version": version}


@router.post("/{chapter_id}/versions/{version_id}/restore")
async def restore_version(project_id: str, chapter_id: str, version_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    chapter = (await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))).scalar_one_or_none()
    version = (await db.execute(select(ChapterVersion).where(ChapterVersion.id == version_id, ChapterVersion.chapter_id == chapter_id))).scalar_one_or_none()
    if not chapter or not version:
        raise HTTPException(404, "章节或版本不存在")
    max_version = await db.scalar(
        select(func.max(ChapterVersion.version_number)).where(ChapterVersion.chapter_id == chapter.id)
    ) or 0
    db.add(ChapterVersion(
        project_id=project_id,
        chapter_id=chapter.id,
        version_number=max_version + 1,
        title=chapter.title or "",
        content=chapter.content or "",
        word_count=chapter.word_count or len(chapter.content or ""),
        source="restore_backup",
        note="恢复前自动备份",
    ))
    chapter.title = version.title or chapter.title
    chapter.content = version.content or ""
    chapter.word_count = version.word_count or len(chapter.content or "")
    chapter.version = (chapter.version or 1) + 1
    await db.flush()
    return {"chapter": chapter}


@router.delete("/{chapter_id}")
async def delete_chapter(project_id: str, chapter_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(404, "章节不存在")
    await db.delete(chapter)
    return {"success": True}
