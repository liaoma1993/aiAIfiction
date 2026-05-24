"""
AI Fiction - 章节管理 API 路由

路由前缀: /projects/{project_id}/chapters
所有接口需要认证与项目所属权校验。
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chapter import (
    ChapterCreate,
    ChapterReorderRequest,
    ChapterResponse,
    ChapterStatusSummary,
    ChapterSummaryItem,
    ChapterUpdate,
)
from app.schemas.common import ApiResponse
from app.services import chapter_service, project_service
from app.utils.exceptions import NotFoundException

router = APIRouter(prefix="/projects", tags=["chapters"])


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
# POST /projects/{project_id}/chapters - 创建章节
# ============================================================


@router.post(
    "/{project_id}/chapters",
    response_model=ApiResponse[ChapterResponse],
    status_code=201,
)
async def create_chapter(
    project_id: uuid.UUID,
    data: ChapterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新章节

    需要项目所属权校验。
    同一项目下相同 chapter_number + branch_name 组合不可重复。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    chapter = await chapter_service.create_chapter(db, project_id, data)

    return ApiResponse(
        code=201,
        message="章节创建成功",
        data=ChapterResponse.model_validate(chapter),
    )


# ============================================================
# GET /projects/{project_id}/chapters - 获取章节列表
# ============================================================


@router.get(
    "/{project_id}/chapters",
    response_model=ApiResponse[list[ChapterResponse]],
)
async def list_chapters(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目下所有章节（按 chapter_number 升序）

    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    chapters = await chapter_service.get_project_chapters(db, project_id)

    return ApiResponse(
        message="获取章节列表成功",
        data=[ChapterResponse.model_validate(c) for c in chapters],
    )


# ============================================================
# GET /projects/{project_id}/chapters/summary - 章节状态摘要
# ============================================================


@router.get(
    "/{project_id}/chapters/summary",
    response_model=ApiResponse[ChapterStatusSummary],
)
async def get_chapter_status_summary(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取项目章节状态摘要

    返回各状态章节数量统计及章节摘要列表。
    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    summary = await chapter_service.get_chapter_status_summary(db, project_id)

    return ApiResponse(
        message="获取章节状态摘要成功",
        data=ChapterStatusSummary(
            **summary,
            chapters=[
                ChapterSummaryItem.model_validate(c) for c in summary["chapters"]
            ],
        ),
    )


# ============================================================
# GET /projects/{project_id}/chapters/{chapter_id} - 章节详情
# ============================================================


@router.get(
    "/{project_id}/chapters/{chapter_id}",
    response_model=ApiResponse[ChapterResponse],
)
async def get_chapter(
    project_id: uuid.UUID,
    chapter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个章节详情

    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    chapter = await chapter_service.get_chapter(db, chapter_id, project_id)

    if chapter is None:
        raise NotFoundException("章节不存在")

    return ApiResponse(
        message="获取章节详情成功",
        data=ChapterResponse.model_validate(chapter),
    )


# ============================================================
# PUT /projects/{project_id}/chapters/{chapter_id} - 更新章节
# ============================================================


@router.put(
    "/{project_id}/chapters/{chapter_id}",
    response_model=ApiResponse[ChapterResponse],
)
async def update_chapter(
    project_id: uuid.UUID,
    chapter_id: uuid.UUID,
    data: ChapterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新章节

    所有字段可选，只需传需要更新的字段。
    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    chapter = await chapter_service.update_chapter(db, chapter_id, data)

    if chapter is None:
        raise NotFoundException("章节不存在")

    return ApiResponse(
        message="章节更新成功",
        data=ChapterResponse.model_validate(chapter),
    )


# ============================================================
# DELETE /projects/{project_id}/chapters/{chapter_id} - 删除章节
# ============================================================


@router.delete(
    "/{project_id}/chapters/{chapter_id}",
    response_model=ApiResponse,
)
async def delete_chapter(
    project_id: uuid.UUID,
    chapter_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除章节

    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    success = await chapter_service.delete_chapter(db, chapter_id)

    if not success:
        raise NotFoundException("章节不存在")

    return ApiResponse(
        message="章节已删除",
    )


# ============================================================
# PUT /projects/{project_id}/chapters/reorder - 章节重排
# ============================================================


@router.put(
    "/{project_id}/chapters/reorder",
    response_model=ApiResponse[list[ChapterResponse]],
)
async def reorder_chapters(
    project_id: uuid.UUID,
    data: ChapterReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量更新章节序号

    按 chapter_order 的顺序依次更新章节的 chapter_number。
    需要项目所属权校验。
    """
    await _verify_project_ownership(db, project_id, current_user.id)

    chapters = await chapter_service.reorder_chapters(db, project_id, data)

    return ApiResponse(
        message="章节重排成功",
        data=[ChapterResponse.model_validate(c) for c in chapters],
    )
