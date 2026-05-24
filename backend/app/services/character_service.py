"""
AI Fiction - 角色业务逻辑

提供角色的创建、列表查询、详情查询、更新、删除、排序等服务。
"""
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.schemas.character import CharacterCreate, CharacterUpdate


async def create_character(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: CharacterCreate,
) -> Character:
    """创建角色

    Args:
        db: 数据库会话
        project_id: 所属项目 ID
        data: 角色创建数据

    Returns:
        创建成功的 Character 实例
    """
    character = Character(
        project_id=project_id,
        name=data.name,
        gender=data.gender,
        age=data.age,
        appearance=data.appearance,
        personality=data.personality,
        background=data.background,
        role_type=data.role_type,
        genre_specific_fields=data.genre_specific_fields,
        notes=data.notes,
        sort_order=data.sort_order,
    )
    db.add(character)
    await db.flush()
    return character


async def get_characters_by_project(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[Character]:
    """查询项目下的所有角色，按 sort_order 排序

    Args:
        db: 数据库会话
        project_id: 项目 ID

    Returns:
        角色列表
    """
    result = await db.execute(
        select(Character)
        .where(Character.project_id == project_id)
        .order_by(Character.sort_order, Character.created_at)
    )
    return list(result.scalars().all())


async def get_character(
    db: AsyncSession,
    character_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Character | None:
    """查询角色详情，校验归属项目

    Args:
        db: 数据库会话
        character_id: 角色 ID
        project_id: 所属项目 ID

    Returns:
        Character 实例，若不属于该项目或不存在则返回 None
    """
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.project_id == project_id,
        )
    )
    return result.scalar_one_or_none()


async def update_character(
    db: AsyncSession,
    character_id: uuid.UUID,
    project_id: uuid.UUID,
    data: CharacterUpdate,
) -> Character | None:
    """更新角色，校验归属项目

    Args:
        db: 数据库会话
        character_id: 角色 ID
        project_id: 所属项目 ID
        data: 更新数据

    Returns:
        更新后的 Character 实例，若不属于该项目则返回 None
    """
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.project_id == project_id,
        )
    )
    character = result.scalar_one_or_none()

    if character is None:
        return None

    # 只更新非 None 的字段
    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(character, field, value)

    await db.flush()
    return character


async def delete_character(
    db: AsyncSession,
    character_id: uuid.UUID,
    project_id: uuid.UUID,
) -> bool:
    """删除角色，校验归属项目

    Args:
        db: 数据库会话
        character_id: 角色 ID
        project_id: 所属项目 ID

    Returns:
        是否删除成功
    """
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.project_id == project_id,
        )
    )
    character = result.scalar_one_or_none()

    if character is None:
        return False

    await db.delete(character)
    await db.flush()
    return True


async def reorder_characters(
    db: AsyncSession,
    project_id: uuid.UUID,
    character_ids: list[uuid.UUID],
) -> None:
    """批量更新角色排序顺序

    根据 character_ids 列表的索引位置设置对应角色的 sort_order。
    不在列表中的角色不受影响。

    Args:
        db: 数据库会话
        project_id: 项目 ID
        character_ids: 按目标顺序排列的角色 ID 列表
    """
    for index, cid in enumerate(character_ids):
        await db.execute(
            update(Character)
            .where(
                Character.id == cid,
                Character.project_id == project_id,
            )
            .values(sort_order=index)
        )
    await db.flush()
