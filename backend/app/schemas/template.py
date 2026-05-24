"""
AI Fiction - 模板相关 Pydantic Schema
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import PaginatedResponse

# ============================================================
# 请求模型
# ============================================================


class TemplateCreate(BaseModel):
    """创建模板请求"""

    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(
        default=None, max_length=500, description="模板描述"
    )
    source_project_id: Optional[uuid.UUID] = Field(
        default=None, description="从已有项目创建时传入源项目 ID"
    )
    genre: str = Field(..., description="小说类型")
    target_length: str = Field(..., description="目标篇幅")
    writing_style: dict = Field(
        default_factory=dict, description="写作风格配置"
    )
    story_brief: Optional[str] = Field(
        default=None, description="故事梗概"
    )
    world_setting: Optional[str] = Field(
        default=None, description="世界观设定内容"
    )
    characters: Optional[list] = Field(
        default=None, description="角色列表快照"
    )


class ApplyTemplateRequest(BaseModel):
    """从模板创建项目请求"""

    title: str = Field(..., min_length=1, max_length=100, description="新项目标题")


# ============================================================
# 响应模型
# ============================================================


class TemplateResponse(BaseModel):
    """模板响应"""

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    genre: str
    target_length: str
    usage_count: int = 0
    source_project_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateDetailResponse(TemplateResponse):
    """模板详情响应（含完整快照数据）"""

    writing_style: dict
    story_brief: Optional[str] = None
    world_setting: dict
    characters: list


class TemplateListResponse(PaginatedResponse[TemplateResponse]):
    """模板列表响应"""
    pass
