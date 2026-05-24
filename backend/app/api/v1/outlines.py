"""
AI Fiction - 大纲管理 API 路由

路由前缀: /projects/{project_id}/outline
所有接口需要认证。
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.outline import (
    BatchCreateNodesRequest,
    OutlineConfirmRequest,
    OutlineNodeResponse,
    OutlineNodeUpdate,
    OutlineResponse,
    ReorderNodesRequest,
)
from app.services import outline_service, project_service
from app.utils.exceptions import NotFoundException

router = APIRouter(prefix="/projects", tags=["outlines"])

# ============================================================
# 工具函数
# ============================================================


async def _verify_project_ownership(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """验证项目存在且属于当前用户，否则抛出 404"""
    project = await project_service.get_project(db, project_id, user_id)
    if project is None:
        raise NotFoundException("项目不存在或无权访问")


# ============================================================
# GET /projects/{project_id}/outline - 获取大纲及其所有节点
# ============================================================


@router.get("/{project_id}/outline", response_model=ApiResponse[OutlineResponse])
async def get_outline(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取大纲（含所有节点）

    如果大纲不存在，自动创建一个空大纲并返回。
    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    outline = await outline_service.get_or_create_outline(db, project_id)

    return ApiResponse(
        message="获取大纲成功",
        data=OutlineResponse.model_validate(outline),
    )


# ============================================================
# POST /projects/{project_id}/outline/confirm - 确认大纲
# ============================================================


@router.post(
    "/{project_id}/outline/confirm",
    response_model=ApiResponse[OutlineResponse],
)
async def confirm_outline(
    project_id: uuid.UUID,
    data: OutlineConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认大纲

    确认后版本号 +1。
    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    outline = await outline_service.confirm_outline(db, project_id, data)

    return ApiResponse(
        message="大纲已确认" if data.is_confirmed else "大纲已取消确认",
        data=OutlineResponse.model_validate(outline),
    )


# ============================================================
# POST /projects/{project_id}/outline/nodes - 批量创建大纲节点
# ============================================================


@router.post(
    "/{project_id}/outline/nodes",
    response_model=ApiResponse[list[OutlineNodeResponse]],
    status_code=201,
)
async def batch_create_nodes(
    project_id: uuid.UUID,
    data: BatchCreateNodesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量创建大纲节点

    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    outline = await outline_service.get_or_create_outline(db, project_id)
    nodes = await outline_service.batch_create_nodes(db, outline.id, data)

    return ApiResponse(
        code=201,
        message=f"成功创建 {len(nodes)} 个节点",
        data=[OutlineNodeResponse.model_validate(n) for n in nodes],
    )


# ============================================================
# PUT /projects/{project_id}/outline/nodes/{node_id} - 更新单个节点
# ============================================================


@router.put(
    "/{project_id}/outline/nodes/{node_id}",
    response_model=ApiResponse[OutlineNodeResponse],
)
async def update_node(
    project_id: uuid.UUID,
    node_id: uuid.UUID,
    data: OutlineNodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新单个大纲节点

    所有字段可选，只需传需要更新的字段。
    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    node = await outline_service.update_node(db, node_id, data)

    if node is None:
        raise NotFoundException("大纲节点不存在")

    return ApiResponse(
        message="节点更新成功",
        data=OutlineNodeResponse.model_validate(node),
    )


# ============================================================
# DELETE /projects/{project_id}/outline/nodes/{node_id} - 删除单个节点
# ============================================================


@router.delete(
    "/{project_id}/outline/nodes/{node_id}",
    response_model=ApiResponse,
)
async def delete_node(
    project_id: uuid.UUID,
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除单个大纲节点

    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    success = await outline_service.delete_node(db, node_id)

    if not success:
        raise NotFoundException("大纲节点不存在")

    return ApiResponse(
        message="节点已删除",
    )


# ============================================================
# PUT /projects/{project_id}/outline/nodes/reorder - 节点排序
# ============================================================


@router.put(
    "/{project_id}/outline/nodes/reorder",
    response_model=ApiResponse[list[OutlineNodeResponse]],
)
async def reorder_nodes(
    project_id: uuid.UUID,
    data: ReorderNodesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重新排序大纲节点

    按 node_ids 的顺序依次分配 sort_order（从 0 开始递增）。
    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    outline = await outline_service.get_or_create_outline(db, project_id)
    nodes = await outline_service.reorder_nodes(db, outline.id, data.node_ids)

    return ApiResponse(
        message="节点排序成功",
        data=[OutlineNodeResponse.model_validate(n) for n in nodes],
    )
