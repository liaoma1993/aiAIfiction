"""
AI Fiction - 角色相关 Pydantic Schema
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ============================================================
# 请求模型
# ============================================================


class CharacterCreate(BaseModel):
    """创建角色请求"""

    name: str = Field(..., min_length=1, max_length=100, description="角色名称")
    gender: Optional[Literal["male", "female", "other"]] = Field(
        default=None, description="性别"
    )
    age: Optional[int] = Field(
        default=None, ge=0, le=10000, description="年龄"
    )
    appearance: Optional[str] = Field(default=None, description="外貌描述")
    personality: Optional[str] = Field(default=None, description="性格描述")
    background: Optional[str] = Field(default=None, description="背景故事")
    role_type: Literal["protagonist", "antagonist", "supporting"] = Field(
        default="supporting", description="角色类型"
    )
    genre_specific_fields: dict = Field(
        default_factory=dict, description="题材特有字段"
    )
    notes: Optional[str] = Field(default=None, description="备注")
    sort_order: int = Field(default=0, description="排序顺序")


class CharacterUpdate(BaseModel):
    """更新角色请求，所有字段可选"""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="角色名称"
    )
    gender: Optional[Literal["male", "female", "other"]] = Field(
        default=None, description="性别"
    )
    age: Optional[int] = Field(
        default=None, ge=0, le=10000, description="年龄"
    )
    appearance: Optional[str] = Field(default=None, description="外貌描述")
    personality: Optional[str] = Field(default=None, description="性格描述")
    background: Optional[str] = Field(default=None, description="背景故事")
    role_type: Optional[Literal["protagonist", "antagonist", "supporting"]] = Field(
        default=None, description="角色类型"
    )
    genre_specific_fields: Optional[dict] = Field(
        default=None, description="题材特有字段"
    )
    deepened_profile: Optional[str] = Field(
        default=None, description="AI深化后的完整档案"
    )
    relationships: Optional[list] = Field(
        default=None, description="角色关系列表"
    )
    growth_arc: Optional[str] = Field(
        default=None, description="角色成长弧光"
    )
    notes: Optional[str] = Field(default=None, description="备注")
    sort_order: Optional[int] = Field(default=None, description="排序顺序")


class ReorderRequest(BaseModel):
    """角色排序请求"""

    character_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="按目标顺序排列的角色 ID 列表"
    )


# ============================================================
# 响应模型
# ============================================================


class CharacterResponse(BaseModel):
    """角色响应"""

    id: uuid.UUID
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    role_type: str
    genre_specific_fields: dict
    deepened_profile: Optional[str] = None
    relationships: list
    growth_arc: Optional[str] = None
    notes: Optional[str] = None
    sort_order: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
