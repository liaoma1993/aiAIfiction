"""
AI Fiction - 模板业务逻辑

提供模板的创建、查询、删除、应用等服务。
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.models.project import Project
from app.models.template import Template
from app.models.world_setting import WorldSetting
from app.schemas.common import PaginationParams, SortParams
from app.schemas.template import TemplateCreate


async def create_template(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: TemplateCreate,
) -> Template:
    """创建模板

    支持两种方式：
    1. 从已有项目快照（传入 source_project_id）
    2. 手动输入参数

    Args:
        db: 数据库会话
        user_id: 当前用户 ID
        data: 模板创建数据

    Returns:
        创建成功的 Template 实例
    """
    world_setting_snapshot: dict = {}
    characters_snapshot: list = []

    if data.source_project_id is not None:
        # 从源项目获取快照数据
        ws_result = await db.execute(
            select(WorldSetting).where(
                WorldSetting.project_id == data.source_project_id
            )
        )
        source_ws = ws_result.scalar_one_or_none()

        char_result = await db.execute(
            select(Character).where(
                Character.project_id == data.source_project_id
            ).order_by(Character.sort_order)
        )
        source_chars = list(char_result.scalars().all())

        if source_ws is not None:
            world_setting_snapshot = {
                "original_content": source_ws.original_content,
                "expanded_content": source_ws.expanded_content,
                "structured_data": source_ws.structured_data,
            }

        characters_snapshot = [
            {
                "name": c.name,
                "gender": c.gender,
                "age": c.age,
                "appearance": c.appearance,
                "personality": c.personality,
                "background": c.background,
                "role_type": c.role_type,
                "genre_specific_fields": c.genre_specific_fields,
                "deepened_profile": c.deepened_profile,
                "relationships": c.relationships,
                "growth_arc": c.growth_arc,
                "notes": c.notes,
                "sort_order": c.sort_order,
            }
            for c in source_chars
        ]
    else:
        # 手动输入模式：使用传入的世界观和角色数据
        if data.world_setting is not None:
            world_setting_snapshot = {"original_content": data.world_setting}
        if data.characters is not None:
            characters_snapshot = data.characters

    template = Template(
        user_id=user_id,
        name=data.name,
        description=data.description,
        source_project_id=data.source_project_id,
        genre=data.genre,
        target_length=data.target_length,
        writing_style=data.writing_style,
        story_brief=data.story_brief,
        world_setting=world_setting_snapshot,
        characters=characters_snapshot,
    )
    db.add(template)
    await db.flush()
    return template


async def get_user_templates(
    db: AsyncSession,
    user_id: uuid.UUID,
    pagination: PaginationParams,
    sort: SortParams,
) -> tuple[list[Template], int]:
    """分页查询用户的模板列表

    Args:
        db: 数据库会话
        user_id: 当前用户 ID
        pagination: 分页参数
        sort: 排序参数

    Returns:
        (模板列表, 总记录数) 元组
    """
    count_query = (
        select(func.count())
        .select_from(Template)
        .where(Template.user_id == user_id)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = select(Template).where(Template.user_id == user_id)

    sort_by = sort.sort_by
    sort_order = sort.sort_order
    if sort_by and hasattr(Template, sort_by):
        order_col = getattr(Template, sort_by)
        query = query.order_by(
            order_col.desc() if sort_order == "desc" else order_col.asc()
        )
    else:
        query = query.order_by(Template.updated_at.desc())

    offset = (pagination.page - 1) * pagination.page_size
    query = query.offset(offset).limit(pagination.page_size)

    result = await db.execute(query)
    templates = list(result.scalars().all())

    return templates, total


async def get_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> Template | None:
    """查询模板详情，可选所有权校验

    Args:
        db: 数据库会话
        template_id: 模板 ID
        user_id: 当前用户 ID，None 时不校验所有权

    Returns:
        Template 实例，若无权限或不存在则返回 None
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        return None

    if user_id is not None and template.user_id != user_id:
        return None

    return template


async def delete_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """删除模板（物理删除）

    Args:
        db: 数据库会话
        template_id: 模板 ID
        user_id: 当前用户 ID

    Returns:
        是否删除成功
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None or template.user_id != user_id:
        return False

    await db.delete(template)
    await db.flush()
    return True


async def apply_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
) -> Project | None:
    """从模板创建新项目

    使用模板中的配置创建新项目，并复制世界观设定和角色。

    Args:
        db: 数据库会话
        template_id: 模板 ID
        user_id: 当前用户 ID
        title: 新项目标题

    Returns:
        创建成功的 Project 实例，若模板不存在则返回 None
    """
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if template is None:
        return None

    # 创建新项目
    project = Project(
        user_id=user_id,
        title=title,
        genre=template.genre,
        target_length=template.target_length,
        writing_style=template.writing_style,
        story_brief=template.story_brief,
    )
    db.add(project)
    await db.flush()

    # 复制世界观设定
    ws_data = template.world_setting or {}
    world_setting = WorldSetting(
        project_id=project.id,
        original_content=ws_data.get("original_content"),
        expanded_content=ws_data.get("expanded_content"),
        structured_data=ws_data.get("structured_data", {}),
    )
    db.add(world_setting)

    # 复制角色
    for char_data in template.characters or []:
        character = Character(
            project_id=project.id,
            name=char_data.get("name", ""),
            gender=char_data.get("gender"),
            age=char_data.get("age"),
            appearance=char_data.get("appearance"),
            personality=char_data.get("personality"),
            background=char_data.get("background"),
            role_type=char_data.get("role_type", "supporting"),
            genre_specific_fields=char_data.get("genre_specific_fields", {}),
            deepened_profile=char_data.get("deepened_profile"),
            relationships=char_data.get("relationships", []),
            growth_arc=char_data.get("growth_arc"),
            notes=char_data.get("notes"),
            sort_order=char_data.get("sort_order", 0),
        )
        db.add(character)

    # 增加模板使用次数
    template.usage_count = Template.usage_count + 1

    await db.flush()
    return project
