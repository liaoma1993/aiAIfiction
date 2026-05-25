"""
AI Fiction - 大纲相关 Pydantic Schema
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 请求模型
# ============================================================


class OutlineNodeCreate(BaseModel):
    """创建大纲节点请求"""

    chapter_number: int = Field(..., ge=1, description="章节序号")
    title: Optional[str] = Field(default=None, max_length=200, description="章节标题")
    summary: str = Field(..., min_length=1, max_length=2000, description="本章概要")
    key_events: list[str] = Field(
        default_factory=list, description="关键事件列表"
    )
    emotional_arc: Optional[str] = Field(
        default=None, description="角色情绪变化弧线"
    )
    writing_guide: Optional[str] = Field(
        default=None, description="AI 生成的详细写作指南"
    )
    foreshadowing_items: list[str] = Field(
        default_factory=list, description="本章埋下的伏笔"
    )
    foreshadowing_resolved: list[str] = Field(
        default_factory=list, description="本章回收的伏笔"
    )
    sort_order: int = Field(default=0, description="排序序号")
    is_key_scene: Optional[bool] = Field(None, description="是否标记为关键场景")
    scene_template: Optional[dict] = Field(None, description="场景模板配置")


class OutlineNodeUpdate(BaseModel):
    """更新大纲节点请求，所有字段可选"""

    chapter_number: Optional[int] = Field(default=None, ge=1, description="章节序号")
    title: Optional[str] = Field(default=None, max_length=200, description="章节标题")
    summary: Optional[str] = Field(
        default=None, min_length=1, max_length=2000, description="本章概要"
    )
    key_events: Optional[list[str]] = Field(
        default=None, description="关键事件列表"
    )
    emotional_arc: Optional[str] = Field(
        default=None, description="角色情绪变化弧线"
    )
    writing_guide: Optional[str] = Field(
        default=None, description="AI 生成的详细写作指南"
    )
    foreshadowing_items: Optional[list[str]] = Field(
        default=None, description="本章埋下的伏笔"
    )
    foreshadowing_resolved: Optional[list[str]] = Field(
        default=None, description="本章回收的伏笔"
    )
    sort_order: Optional[int] = Field(default=None, description="排序序号")
    is_key_scene: Optional[bool] = Field(None, description="是否标记为关键场景")
    scene_template: Optional[dict] = Field(None, description="场景模板配置")


class OutlineConfirmRequest(BaseModel):
    """确认大纲请求"""

    is_confirmed: bool = Field(default=True, description="是否确认大纲")


class BatchCreateNodesRequest(BaseModel):
    """批量创建大纲节点请求"""

    nodes: list[OutlineNodeCreate] = Field(
        ..., min_length=1, description="要创建的节点列表"
    )


class ReorderNodesRequest(BaseModel):
    """节点排序请求"""

    node_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="按新顺序排列的节点 ID 列表"
    )


# ============================================================
# 响应模型
# ============================================================


class OutlineNodeResponse(BaseModel):
    """大纲节点响应"""

    id: uuid.UUID
    outline_id: uuid.UUID
    chapter_number: int
    title: Optional[str] = None
    summary: str
    key_events: list[str]
    emotional_arc: Optional[str] = None
    writing_guide: Optional[str] = None
    foreshadowing_items: list[str]
    foreshadowing_resolved: list[str]
    sort_order: int
    is_key_scene: bool = False
    scene_template: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutlineResponse(BaseModel):
    """大纲响应（含所有节点）"""

    id: uuid.UUID
    project_id: uuid.UUID
    is_confirmed: bool
    version: int
    nodes: list[OutlineNodeResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SceneTemplateUpdate(BaseModel):
    """场景模板更新请求（PUT /outline/nodes/{nid}/scene-template）"""

    is_key_scene: bool = Field(..., description="是否关键场景")
    scene_template: dict = Field(..., description="场景模板")
