"""
AI Fiction - GenerationTask & TaskLog 模型
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Text,
    ForeignKey,
    Index,
    func,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import BaseModel


class GenerationTask(BaseModel):
    """生成任务模型"""

    __tablename__ = "generation_task"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )

    current_stage: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_chapters: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    completed_chapters: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    result_summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    precision_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment='精细度控制配置: {preset, world_constraint_strictness, character_consistency_strictness, foreshadowing_tracking_precision, relationship_awareness, creativity_level, quality_threshold, style_intensity}',
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_stage: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    max_retry: Mapped[int] = mapped_column(
        Integer,
        default=3,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_gtask_project_id", "project_id"),
        Index("idx_gtask_status", "status"),
    )


class TaskLog(Base):
    """任务日志模型（只记创建时间，不需要 updated_at，故不继承 BaseModel）"""

    __tablename__ = "task_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=func.gen_random_uuid(),
        index=True,
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    stage: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    log_level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="info",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    meta_data: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=func.now(),
    )

    __table_args__ = (
        Index("idx_tlog_task_id", "task_id"),
    )
