"""
AI Fiction - 伏笔管理服务

提供伏笔计划的 CRUD、列表查询、完成度报告等服务。
"""

import uuid
from collections import defaultdict
from typing import Optional

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.foreshadowing_plan import ForeshadowingPlan
from app.models.chapter import Chapter
from app.schemas.foreshadowing import ForeshadowingCreate, ForeshadowingUpdate
from app.utils.exceptions import ValidationException


def _model_to_dict(fs: ForeshadowingPlan) -> dict:
    """将 ForeshadowingPlan 模型实例转换为字典，包含所有业务字段"""
    return {
        "id": fs.id,
        "project_id": fs.project_id,
        "name": fs.name,
        "description": fs.description,
        "type": fs.type,
        "importance": fs.importance,
        "status": fs.status,
        "plant_chapter_number": fs.plant_chapter_number,
        "plant_detail": fs.plant_detail,
        "reveal_chapter_number": fs.reveal_chapter_number,
        "reveal_type": fs.reveal_type,
        "reveal_detail": fs.reveal_detail,
        "actual_plant_chapter_id": fs.actual_plant_chapter_id,
        "actual_plant_content": fs.actual_plant_content,
        "actual_reveal_chapter_id": fs.actual_reveal_chapter_id,
        "actual_reveal_content": fs.actual_reveal_content,
        "parent_foreshadowing_id": fs.parent_foreshadowing_id,
        "is_verified": fs.is_verified,
        "verified_at": fs.verified_at,
        "notes": fs.notes,
        "created_at": fs.created_at,
        "updated_at": fs.updated_at,
        "child_foreshadowings": [],
    }


async def get_foreshadowings(
    db: AsyncSession,
    project_id: uuid.UUID,
    status_filter: Optional[list[str]] = None,
) -> dict:
    """查询项目下所有伏笔计划

    Args:
        db: 数据库会话
        project_id: 项目 ID
        status_filter: 可选的状态筛选列表

    Returns:
        {total, by_status: {status: count}, items: [dict, ...]}
    """
    # 一次性查询项目所有伏笔，按创建时间倒序
    stmt = select(ForeshadowingPlan).where(
        ForeshadowingPlan.project_id == project_id,
    )
    if status_filter:
        stmt = stmt.where(ForeshadowingPlan.status.in_(status_filter))

    stmt = stmt.order_by(desc(ForeshadowingPlan.created_at))
    result = await db.execute(stmt)
    all_plans = list(result.scalars().all())

    # 按状态分组计数
    by_status: dict[str, int] = defaultdict(int)
    for p in all_plans:
        by_status[p.status] += 1

    if not all_plans:
        return {
            "total": 0,
            "by_status": dict(by_status),
            "items": [],
        }

    # 批量查询子伏笔：收集所有父级ID，一次性查出所有子记录
    parent_ids = [p.id for p in all_plans]
    child_result = await db.execute(
        select(ForeshadowingPlan).where(
            ForeshadowingPlan.parent_foreshadowing_id.in_(parent_ids),
        )
    )
    children_by_parent: dict[uuid.UUID, list[dict]] = defaultdict(list)
    for child in child_result.scalars().all():
        if child.parent_foreshadowing_id:
            children_by_parent[child.parent_foreshadowing_id].append(
                _model_to_dict(child)
            )

    # 组装返回数据
    items: list[dict] = []
    for plan in all_plans:
        item = _model_to_dict(plan)
        item["child_foreshadowings"] = children_by_parent.get(plan.id, [])
        items.append(item)

    return {
        "total": len(all_plans),
        "by_status": dict(by_status),
        "items": items,
    }


async def create_foreshadowing(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: ForeshadowingCreate,
) -> ForeshadowingPlan:
    """创建新伏笔计划

    Args:
        db: 数据库会话
        project_id: 项目 ID
        data: 伏笔创建数据

    Returns:
        创建成功的 ForeshadowingPlan 实例

    Raises:
        ValidationException: plant_chapter_number > reveal_chapter_number 时抛出
    """
    # 校验：埋设章节号不能大于揭晓章节号
    plant_ch = data.plant_chapter_number
    reveal_ch = data.reveal_chapter_number
    if plant_ch is not None and reveal_ch is not None and plant_ch > reveal_ch:
        raise ValidationException(
            f"plant_chapter_number ({plant_ch}) must not be greater "
            f"than reveal_chapter_number ({reveal_ch})"
        )

    plan = ForeshadowingPlan(
        project_id=project_id,
        name=data.name,
        description=data.description,
        type=data.type,
        importance=data.importance,
        status="planned",
        plant_chapter_number=data.plant_chapter_number,
        plant_detail=data.plant_detail,
        reveal_chapter_number=data.reveal_chapter_number,
        reveal_type=data.reveal_type,
        reveal_detail=data.reveal_detail,
        parent_foreshadowing_id=data.parent_foreshadowing_id,
        notes=data.notes,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def update_foreshadowing(
    db: AsyncSession,
    project_id: uuid.UUID,
    foreshadowing_id: uuid.UUID,
    data: ForeshadowingUpdate,
) -> Optional[ForeshadowingPlan]:
    """更新伏笔计划

    Args:
        db: 数据库会话
        project_id: 项目 ID
        foreshadowing_id: 伏笔 ID
        data: 更新数据（所有字段可选）

    Returns:
        更新后的 ForeshadowingPlan 实例，若不存在则返回 None
    """
    result = await db.execute(
        select(ForeshadowingPlan).where(
            ForeshadowingPlan.id == foreshadowing_id,
            ForeshadowingPlan.project_id == project_id,
        )
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        return None

    update_dict = data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(plan, field, value)

    await db.flush()
    await db.refresh(plan)
    return plan


async def delete_foreshadowing(
    db: AsyncSession,
    project_id: uuid.UUID,
    foreshadowing_id: uuid.UUID,
) -> bool:
    """删除伏笔计划

    如有子伏笔（parent_foreshadowing_id 指向当前ID），
    将其 parent_foreshadowing_id 置为 None 以避免外键依赖冲突。

    Args:
        db: 数据库会话
        project_id: 项目 ID
        foreshadowing_id: 伏笔 ID

    Returns:
        是否删除成功
    """
    result = await db.execute(
        select(ForeshadowingPlan).where(
            ForeshadowingPlan.id == foreshadowing_id,
            ForeshadowingPlan.project_id == project_id,
        )
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        return False

    # 批量将子伏笔的 parent_foreshadowing_id 置为 None
    child_result = await db.execute(
        select(ForeshadowingPlan).where(
            ForeshadowingPlan.parent_foreshadowing_id == foreshadowing_id,
        )
    )
    children = child_result.scalars().all()
    for child in children:
        child.parent_foreshadowing_id = None

    await db.delete(plan)
    await db.flush()
    return True


async def get_foreshadowing_report(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict:
    """获取伏笔完成度报告

    统计各状态数量、完成率，检测断链伏笔并生成建议。

    Args:
        db: 数据库会话
        project_id: 项目 ID

    Returns:
        {total, verified, revealed, developing, planted, planned,
         completion_rate, broken_chain, suggestions}
    """
    # 一次性查出所有伏笔
    result = await db.execute(
        select(ForeshadowingPlan).where(
            ForeshadowingPlan.project_id == project_id,
        )
    )
    all_plans = list(result.scalars().all())

    # 查询当前已生成的最大章节号
    max_chapter_result = await db.execute(
        select(func.max(Chapter.chapter_number)).where(
            Chapter.project_id == project_id,
        )
    )
    max_chapter: int | None = max_chapter_result.scalar_one()

    # 按状态计数
    status_counts: dict[str, int] = defaultdict(int)
    for p in all_plans:
        status_counts[p.status] += 1

    total = len(all_plans)
    verified = status_counts.get("verified", 0)
    revealed = status_counts.get("revealed", 0)
    developing = status_counts.get("developing", 0)
    planted = status_counts.get("planted", 0)
    planned = status_counts.get("planned", 0)

    # 完成率 = (verified + revealed) / total
    resolved = verified + revealed
    completion_rate = round(resolved / total * 100, 1) if total > 0 else 0.0

    # 检测断链伏笔：
    # reveal_chapter_number < 当前已生成最大章节数，但 status 仍为 planned/planted
    broken_chain: list[dict] = []
    if max_chapter is not None:
        for p in all_plans:
            reveal_ch = p.reveal_chapter_number
            if (
                reveal_ch is not None
                and reveal_ch < max_chapter
                and p.status in ("planned", "planted")
            ):
                broken_chain.append({
                    "id": str(p.id),
                    "name": p.name,
                    "detail": (
                        f"预定在第{reveal_ch}章揭晓，但当前已生成到第{max_chapter}章，"
                        f"状态仍为 {p.status}"
                    ),
                })

    # 生成建议
    suggestions: list[str] = []
    orphaned = status_counts.get("orphaned", 0)
    if orphaned > 0:
        suggestions.append(
            f"发现 {orphaned} 个孤儿伏笔，建议检查是否仍需要或标记为废弃"
        )
    if broken_chain:
        suggestions.append(
            f"发现 {len(broken_chain)} 个断链伏笔，"
            f"预定揭晓章节已过但状态未更新，建议标记或删除"
        )
    if completion_rate < 100 and total > 0:
        suggestions.append(
            f"当前伏笔完成率为 {completion_rate}%，"
            f"还有 {total - resolved} 个伏笔待揭晓或验证"
        )
    if not all_plans:
        suggestions.append("当前项目暂无伏笔计划，建议在关键剧情节点预先规划伏笔")

    return {
        "total": total,
        "verified": verified,
        "revealed": revealed,
        "developing": developing,
        "planted": planted,
        "planned": planned,
        "completion_rate": completion_rate,
        "broken_chain": broken_chain,
        "suggestions": suggestions,
    }
