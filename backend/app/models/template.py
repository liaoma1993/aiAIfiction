"""
AI Fiction - Template 模型

项目模板，保存 Project + WorldSetting + Characters 的快照。
"""

import uuid

from sqlalchemy import String, Integer, Text, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Template(BaseModel):
    """项目模板模型

    本质是 Project + WorldSetting + Characters 的快照，
    模板独立于源项目存在，源项目删除不影响模板。
    """

    __tablename__ = "template"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    genre: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    target_length: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    writing_style: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    story_brief: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    world_setting: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    characters: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_template_user_id", "user_id"),
        Index("idx_template_genre", "genre"),
    )
