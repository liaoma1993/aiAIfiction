"""
AI Fiction - 章节相关 Pydantic Schema
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from typing_extensions import Literal

from app.schemas.common import ApiResponse


# ============================================================
# 枚举类型
# ============================================================

ChapterStatus = Literal[
    "planned",
    "generating",
    "completed",
    "reviewed",
    "failed",
]


# ============================================================
# 请求模型
# ============================================================


class ChapterCreate(BaseModel):
    """创建章节请求"""

    chapter_number: int = Field(..., ge=1, description="章节序号")
    title: Optional[str] = Field(default=None, max_length=200, description="章节标题")
    outline_node_id: Optional[uuid.UUID] = Field(
        default=None, description="关联的大纲节点 ID"
    )
    branch_name: Optional[str] = Field(
        default=None, max_length=100, description="分支名称"
    )
    branch_parent_chapter_id: Optional[uuid.UUID] = Field(
        default=None, description="分支父章节 ID"
    )


class ChapterUpdate(BaseModel):
    """更新章节请求，所有字段可选"""

    title: Optional[str] = Field(default=None, max_length=200, description="章节标题")
    status: Optional[ChapterStatus] = Field(default=None, description="章节状态")
    quality_score: Optional[int] = Field(
        default=None, ge=0, le=100, description="质量评分 (0-100)"
    )
    quality_label: Optional[str] = Field(default=None, description="质量标签")
    branch_name: Optional[str] = Field(default=None, description="分支名称")


class ChapterReorderItem(BaseModel):
    """章节重排单项"""

    chapter_id: uuid.UUID = Field(..., description="章节 ID")
    chapter_number: int = Field(..., ge=1, description="新章节序号")


class ChapterReorderRequest(BaseModel):
    """章节重排请求"""

    chapter_order: list[ChapterReorderItem] = Field(
        ..., min_length=1, description="按新顺序排列的章节序号列表"
    )


# ============================================================
# 响应模型
# ============================================================


class ChapterResponse(BaseModel):
    """章节响应"""

    id: uuid.UUID
    project_id: uuid.UUID
    outline_node_id: Optional[uuid.UUID] = None
    chapter_number: int
    title: Optional[str] = None
    status: str
    quality_score: Optional[int] = None
    quality_label: Optional[str] = None
    current_version_number: int
    branch_parent_chapter_id: Optional[uuid.UUID] = None
    branch_name: Optional[str] = None
    word_count: int
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChapterSummaryItem(BaseModel):
    """章节摘要项"""

    id: uuid.UUID
    chapter_number: int
    title: Optional[str] = None
    status: str
    word_count: int
    quality_score: Optional[int] = None
    current_version_number: int

    model_config = {"from_attributes": True}


class ChapterStatusSummary(BaseModel):
    """章节状态摘要响应"""

    project_id: uuid.UUID
    total: int = Field(default=0, description="章节总数")
    status_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="各状态章节数量统计",
    )
    chapters: list[ChapterSummaryItem] = Field(
        default_factory=list, description="章节摘要列表"
    )
