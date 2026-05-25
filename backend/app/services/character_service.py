"""
AI Fiction - 角色业务逻辑

提供角色的创建、列表查询、详情查询、更新、删除、排序等服务。
"""
import uuid

from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.story_state_trail import StoryStateTrail
from app.schemas.character import (
    CharacterConstraintsUpdate,
    CharacterCreate,
    CharacterUpdate,
)


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
    await db.refresh(character)
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
    await db.refresh(character)
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


# ============================================================
# 角色约束管理
# ============================================================


async def update_character_constraints(
    db: AsyncSession,
    project_id: uuid.UUID,
    character_id: uuid.UUID,
    data: CharacterConstraintsUpdate,
) -> Character | None:
    """部分更新角色约束字段（PATCH /constraints）

    只更新 data 中显式传入的字段（exclude_unset=True）。
    传入 null 值的字段将被清空，未传入的字段保持不变。

    Args:
        db: 数据库会话
        project_id: 项目 ID
        character_id: 角色 ID
        data: 约束更新数据

    Returns:
        更新后的 Character 实例，若角色不存在则返回 None
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

    # 顶层 merge：只处理显式传入的字段
    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(character, field, value)

    await db.flush()
    await db.refresh(character)
    return character


async def get_character_consistency(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict:
    """获取角色一致性仪表盘数据

    查询项目下所有角色，构建一致性信息：
    - consistency_score 初始值 -1（暂无数据），后续由 Stage 6 更新
    - constraint_card 从 behavior_patterns / linguistic_style / emotional_expression 提取
    - recent_behavior_summary 从 StoryStateTrail 最新快照中解析

    Args:
        db: 数据库会话
        project_id: 项目 ID

    Returns:
        {"characters": [...], "affected_chapters": []}
    """
    result = await db.execute(
        select(Character)
        .where(Character.project_id == project_id)
        .order_by(Character.sort_order, Character.created_at)
    )
    characters = list(result.scalars().all())

    # 查询最新一次状态快照
    trail_result = await db.execute(
        select(StoryStateTrail)
        .where(StoryStateTrail.project_id == project_id)
        .order_by(desc(StoryStateTrail.snapshot_at))
        .limit(1)
    )
    latest_trail = trail_result.scalar_one_or_none()

    character_list: list[dict] = []
    for char in characters:
        # 构建约束卡：从 JSONB 字段提取关键约束
        constraint_card: dict = {}
        if char.behavior_patterns:
            constraint_card["behavior_patterns"] = char.behavior_patterns
        if char.linguistic_style:
            constraint_card["linguistic_style"] = char.linguistic_style
        if char.emotional_expression:
            constraint_card["emotional_expression"] = char.emotional_expression

        # 从最新快照中解析该角色的行为摘要
        recent_behavior_summary: list[str] = []
        if latest_trail and char.id:
            char_id_str = str(char.id)
            char_data = latest_trail.character_matrix.get(char_id_str, {})
            if isinstance(char_data, dict):
                behavior = char_data.get("behavior_summary")
                if isinstance(behavior, list):
                    recent_behavior_summary = behavior

        character_list.append({
            "character_id": char.id,
            "character_name": char.name,
            "role_type": char.role_type,
            "consistency_score": -1,
            "consistency_trend": [],
            "recent_deviations": [],
            "constraint_card": constraint_card,
            "recent_behavior_summary": recent_behavior_summary,
        })

    return {
        "characters": character_list,
        "affected_chapters": [],
    }
