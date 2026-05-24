"""
AI Fiction - 角色 CRUD API 路由

路由前缀: /projects/{project_id}/characters
所有接口需要认证。
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.character import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
    ReorderRequest,
)
from app.schemas.common import ApiResponse
from app.services import character_service
from app.utils.exceptions import NotFoundException

router = APIRouter(
    prefix="/projects/{project_id}/characters",
    tags=["characters"],
)


# ============================================================
# POST /projects/{project_id}/characters - 创建角色
# ============================================================


@router.post("", response_model=ApiResponse[CharacterResponse], status_code=201)
async def create_character(
    project_id: uuid.UUID,
    data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建角色

    在指定项目下创建一个新角色。
    """
    character = await character_service.create_character(db, project_id, data)

    return ApiResponse(
        code=201,
        message="角色创建成功",
        data=CharacterResponse.model_validate(character),
    )


# ============================================================
# GET /projects/{project_id}/characters - 获取角色列表
# ============================================================


@router.get("", response_model=ApiResponse[list[CharacterResponse]])
async def list_characters(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目下的所有角色

    按 sort_order 排序返回。
    """
    characters = await character_service.get_characters_by_project(db, project_id)

    return ApiResponse(
        data=[CharacterResponse.model_validate(c) for c in characters],
    )


# ============================================================
# PUT /projects/{project_id}/characters/reorder - 批量排序
# ============================================================


@router.put("/reorder", response_model=ApiResponse)
async def reorder_characters(
    project_id: uuid.UUID,
    data: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量更新角色排序

    传入按目标顺序排列的角色 ID 列表，系统将按索引位置更新 sort_order。
    """
    await character_service.reorder_characters(db, project_id, data.character_ids)

    return ApiResponse(
        message="角色排序更新成功",
    )


# ============================================================
# GET /projects/{project_id}/characters/{character_id} - 获取角色详情
# ============================================================


@router.get("/{character_id}", response_model=ApiResponse[CharacterResponse])
async def get_character(
    project_id: uuid.UUID,
    character_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取角色详情

    需要角色归属校验，只能访问属于指定项目的角色。
    """
    character = await character_service.get_character(
        db, character_id, project_id
    )

    if character is None:
        raise NotFoundException("角色不存在或不属于该项目")

    return ApiResponse(
        data=CharacterResponse.model_validate(character),
    )


# ============================================================
# PUT /projects/{project_id}/characters/{character_id} - 更新角色
# ============================================================


@router.put("/{character_id}", response_model=ApiResponse[CharacterResponse])
async def update_character(
    project_id: uuid.UUID,
    character_id: uuid.UUID,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新角色信息

    可以部分更新，只传需要修改的字段。
    需要角色归属校验，只能更新属于指定项目的角色。
    """
    character = await character_service.update_character(
        db, character_id, project_id, data
    )

    if character is None:
        raise NotFoundException("角色不存在或不属于该项目")

    return ApiResponse(
        message="角色更新成功",
        data=CharacterResponse.model_validate(character),
    )


# ============================================================
# DELETE /projects/{project_id}/characters/{character_id} - 删除角色
# ============================================================


@router.delete("/{character_id}", response_model=ApiResponse)
async def delete_character(
    project_id: uuid.UUID,
    character_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除角色

    需要角色归属校验，只能删除属于指定项目的角色。
    """
    success = await character_service.delete_character(
        db, character_id, project_id
    )

    if not success:
        raise NotFoundException("角色不存在或不属于该项目")

    return ApiResponse(
        message="角色已删除",
    )
