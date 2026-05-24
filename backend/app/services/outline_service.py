"""
AI Fiction - 大纲业务逻辑

提供大纲的创建、查询、确认以及大纲节点（OutlineNode）的增删改查和排序等服务。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.outline import Outline, OutlineNode
from app.schemas.outline import (
    BatchCreateNodesRequest,
    OutlineConfirmRequest,
    OutlineNodeUpdate,
)


async def get_or_create_outline(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> Outline:
    """获取或创建大纲（每个项目只有一个大纲）

    Args:
        db: 数据库会话
        project_id: 项目 ID

    Returns:
        已有或新建的 Outline 实例
    """
    result = await db.execute(
        select(Outline)
        .where(Outline.project_id == project_id)
        .options(selectinload(Outline.outline_nodes))
    )
    outline = result.scalars().first()

    if outline is None:
        outline = Outline(project_id=project_id)
        db.add(outline)
        await db.flush()

    return outline


async def get_outline_with_nodes(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> Outline | None:
    """获取大纲及其所有节点（按 sort_order 排序）

    Args:
        db: 数据库会话
        project_id: 项目 ID

    Returns:
        Outline 实例（含已排序的 nodes），不存在则返回 None
    """
    result = await db.execute(
        select(Outline)
        .where(Outline.project_id == project_id)
        .options(selectinload(Outline.outline_nodes))
    )
    return result.scalars().first()


async def confirm_outline(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: OutlineConfirmRequest,
) -> Outline:
    """确认大纲，版本号 +1

    Args:
        db: 数据库会话
        project_id: 项目 ID
        data: 确认请求（含 is_confirmed）

    Returns:
        更新后的 Outline 实例
    """
    outline = await get_or_create_outline(db, project_id)
    outline.is_confirmed = data.is_confirmed
    outline.version += 1
    await db.flush()
    return outline


async def batch_create_nodes(
    db: AsyncSession,
    outline_id: uuid.UUID,
    data: BatchCreateNodesRequest,
) -> list[OutlineNode]:
    """批量创建大纲节点

    Args:
        db: 数据库会话
        outline_id: 大纲 ID
        data: 批量创建请求

    Returns:
        新创建的 OutlineNode 列表
    """
    nodes = []
    for node_data in data.nodes:
        node = OutlineNode(
            outline_id=outline_id,
            chapter_number=node_data.chapter_number,
            title=node_data.title,
            summary=node_data.summary,
            key_events=node_data.key_events,
            emotional_arc=node_data.emotional_arc,
            writing_guide=node_data.writing_guide,
            foreshadowing_items=node_data.foreshadowing_items,
            foreshadowing_resolved=node_data.foreshadowing_resolved,
            sort_order=node_data.sort_order,
        )
        db.add(node)
        nodes.append(node)

    await db.flush()
    return nodes


async def update_node(
    db: AsyncSession,
    node_id: uuid.UUID,
    data: OutlineNodeUpdate,
) -> OutlineNode | None:
    """更新单个大纲节点

    Args:
        db: 数据库会话
        node_id: 节点 ID
        data: 更新数据（所有字段可选）

    Returns:
        更新后的 OutlineNode 实例，不存在则返回 None
    """
    result = await db.execute(
        select(OutlineNode).where(OutlineNode.id == node_id)
    )
    node = result.scalar_one_or_none()

    if node is None:
        return None

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(node, field, value)

    await db.flush()
    return node


async def delete_node(
    db: AsyncSession,
    node_id: uuid.UUID,
) -> bool:
    """删除单个大纲节点

    Args:
        db: 数据库会话
        node_id: 节点 ID

    Returns:
        是否成功删除
    """
    result = await db.execute(
        select(OutlineNode).where(OutlineNode.id == node_id)
    )
    node = result.scalar_one_or_none()

    if node is None:
        return False

    await db.delete(node)
    await db.flush()
    return True


async def reorder_nodes(
    db: AsyncSession,
    outline_id: uuid.UUID,
    node_ids: list[uuid.UUID],
) -> list[OutlineNode]:
    """批量更新大纲节点的排序序号

    按照 node_ids 的顺序依次分配 sort_order（从 0 开始递增）。

    Args:
        db: 数据库会话
        outline_id: 大纲 ID
        node_ids: 按新顺序排列的节点 ID 列表

    Returns:
        重新排序后的 OutlineNode 列表
    """
    # 批量查出所有涉及的节点
    result = await db.execute(
        select(OutlineNode).where(
            OutlineNode.outline_id == outline_id,
            OutlineNode.id.in_(node_ids),
        )
    )
    existing_nodes = {n.id: n for n in result.scalars().all()}

    # 按 node_ids 的顺序更新 sort_order
    updated_nodes = []
    for idx, node_id in enumerate(node_ids):
        node = existing_nodes.get(node_id)
        if node is not None:
            node.sort_order = idx
            updated_nodes.append(node)

    await db.flush()
    return updated_nodes
