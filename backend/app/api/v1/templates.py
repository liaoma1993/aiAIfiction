"""
AI Fiction - 模板 CRUD API 路由

路由前缀: /templates
所有接口需要认证。
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginationParams, SortParams
from app.schemas.project import ProjectResponse
from app.schemas.template import (
    ApplyTemplateRequest,
    TemplateCreate,
    TemplateDetailResponse,
    TemplateListResponse,
    TemplateResponse,
)
from app.services import template_service
from app.utils.exceptions import NotFoundException

router = APIRouter(prefix="/templates", tags=["templates"])


# ============================================================
# POST /templates - 创建模板
# ============================================================


@router.post("", response_model=ApiResponse[TemplateResponse], status_code=201)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建模板

    支持两种方式：
    - 传入 source_project_id：从已有项目快照创建
    - 手动输入 genre、writing_style 等参数创建
    """
    template = await template_service.create_template(db, current_user.id, data)

    return ApiResponse(
        code=201,
        message="模板创建成功",
        data=TemplateResponse.model_validate(template),
    )


# ============================================================
# GET /templates - 获取模板列表
# ============================================================


@router.get("", response_model=ApiResponse[TemplateListResponse])
async def list_templates(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页条数"),
    sort_by: str | None = Query(default=None, description="排序字段"),
    sort_order: str = Query(default="desc", description="排序方向（asc/desc）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的模板列表

    支持分页和排序。默认按 updated_at 降序排列。
    """
    pagination = PaginationParams(page=page, page_size=page_size)
    sort = SortParams(sort_by=sort_by, sort_order=sort_order)

    templates, total = await template_service.get_user_templates(
        db, current_user.id, pagination=pagination, sort=sort
    )

    return ApiResponse(
        data=TemplateListResponse(
            items=[TemplateResponse.model_validate(t) for t in templates],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


# ============================================================
# GET /templates/{template_id} - 模板详情
# ============================================================


@router.get("/{template_id}", response_model=ApiResponse[TemplateDetailResponse])
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取模板详情（含完整快照数据）

    需要模板所属权校验，非所有者无法访问。
    """
    template = await template_service.get_template(
        db, template_id, current_user.id
    )

    if template is None:
        raise NotFoundException("模板不存在或无权访问")

    return ApiResponse(
        data=TemplateDetailResponse.model_validate(template),
    )


# ============================================================
# DELETE /templates/{template_id} - 删除模板
# ============================================================


@router.delete("/{template_id}", response_model=ApiResponse)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除模板（物理删除）

    需要模板所属权校验，非所有者无法操作。
    """
    success = await template_service.delete_template(
        db, template_id, current_user.id
    )

    if not success:
        raise NotFoundException("模板不存在或无权访问")

    return ApiResponse(
        message="模板已删除",
    )


# ============================================================
# POST /templates/{template_id}/apply - 从模板创建项目
# ============================================================


@router.post(
    "/{template_id}/apply",
    response_model=ApiResponse[ProjectResponse],
    status_code=201,
)
async def apply_template(
    template_id: uuid.UUID,
    data: ApplyTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从模板创建新项目

    使用模板中的世界观设定和角色快照创建新项目。
    模板不需要所属权校验——任何登录用户都可以使用公开模板。
    """
    project = await template_service.apply_template(
        db, template_id, current_user.id, data.title
    )

    if project is None:
        raise NotFoundException("模板不存在")

    return ApiResponse(
        code=201,
        message="项目创建成功",
        data=ProjectResponse.model_validate(project),
    )
