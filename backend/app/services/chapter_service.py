"""
AI Fiction - 章节业务逻辑

提供章节的创建、查询、更新、删除、重排和状态摘要服务。
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chapter import Chapter
from app.schemas.chapter import ChapterCreate, ChapterReorderRequest, ChapterUpdate


async def create_chapter(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: ChapterCreate,
) -> Chapter:
    """创建新章节

    检查同一项目下 chapter_number + branch_name 组合的唯一性。

    Args:
        db: 数据库会话
        project_id: 项目 ID
        data: 创建请求数据

    Returns:
        新创建的 Chapter 实例

    Raises:
        由 FastAPI 全局异常处理器捕获 IntegrityError (409)
    """
    chapter = Chapter(
        project_id=project_id,
        outline_node_id=data.outline_node_id,
        chapter_number=data.chapter_number,
        title=data.title,
        branch_name=data.branch_name,
        branch_parent_chapter_id=data.branch_parent_chapter_id,
    )
    db.add(chapter)
    await db.flush()
    return chapter


async def get_project_chapters(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[Chapter]:
    """获取项目下所有章节，按 chapter_number 升序排列

    Args:
        db: 数据库会话
        project_id: 项目 ID

    Returns:
        章节列表
    """
    result = await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id)
        .order_by(Chapter.chapter_number.asc())
    )
    return list(result.scalars().all())


async def get_chapter(
    db: AsyncSession,
    chapter_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Chapter | None:
    """获取单个章节详情

    Args:
        db: 数据库会话
        chapter_id: 章节 ID
        project_id: 项目 ID（用于权限校验）

    Returns:
        Chapter 实例，不存在则返回 None
    """
    result = await db.execute(
        select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.project_id == project_id,
        )
    )
    return result.scalar_one_or_none()


async def update_chapter(
    db: AsyncSession,
    chapter_id: uuid.UUID,
    data: ChapterUpdate,
) -> Chapter | None:
    """更新章节字段

    Args:
        db: 数据库会话
        chapter_id: 章节 ID
        data: 更新数据（所有字段可选，只更新传入的字段）

    Returns:
        更新后的 Chapter 实例，不存在则返回 None
    """
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()

    if chapter is None:
        return None

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(chapter, field, value)

    await db.flush()
    return chapter


async def delete_chapter(
    db: AsyncSession,
    chapter_id: uuid.UUID,
) -> bool:
    """删除章节

    Args:
        db: 数据库会话
        chapter_id: 章节 ID

    Returns:
        是否成功删除
    """
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()

    if chapter is None:
        return False

    await db.delete(chapter)
    await db.flush()
    return True


async def reorder_chapters(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: ChapterReorderRequest,
) -> list[Chapter]:
    """批量更新章节序号

    按 chapter_order 的顺序依次更新各章节的 chapter_number。

    Args:
        db: 数据库会话
        project_id: 项目 ID
        data: 重排请求（含章节 ID 与新序号列表）

    Returns:
        更新后的 Chapter 列表
    """
    chapter_ids = [item.chapter_id for item in data.chapter_order]

    # 批量查出所有涉及的章节
    result = await db.execute(
        select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.id.in_(chapter_ids),
        )
    )
    existing_map = {c.id: c for c in result.scalars().all()}

    updated_chapters = []
    for item in data.chapter_order:
        chapter = existing_map.get(item.chapter_id)
        if chapter is not None:
            chapter.chapter_number = item.chapter_number
            updated_chapters.append(chapter)

    await db.flush()
    return updated_chapters


async def get_chapter_status_summary(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict:
    """获取章节状态摘要

    统计各状态章节数量，并按 chapter_number 排序返回摘要列表。

    Args:
        db: 数据库会话
        project_id: 项目 ID

    Returns:
        状态摘要字典，包含 project_id、total、status_breakdown、chapters
    """
    result = await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id)
        .order_by(Chapter.chapter_number.asc())
    )
    chapters = list(result.scalars().all())

    # 统计各状态数量
    status_breakdown: dict[str, int] = {}
    for ch in chapters:
        status_breakdown[ch.status] = status_breakdown.get(ch.status, 0) + 1

    return {
        "project_id": project_id,
        "total": len(chapters),
        "status_breakdown": status_breakdown,
        "chapters": chapters,
    }
