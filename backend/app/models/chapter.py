"""
AI Fiction - Chapter 模型
"""

import uuid

from sqlalchemy import String, Integer, Text, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Chapter(BaseModel):
    """小说章节模型"""

    __tablename__ = "chapter"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )

    outline_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outline_node.id", ondelete="SET NULL"),
        nullable=True,
    )

    chapter_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="planned",
    )

    quality_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    quality_label: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    current_version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    branch_parent_chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapter.id", ondelete="SET NULL"),
        nullable=True,
    )

    branch_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    word_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    versions: Mapped[list["ChapterVersion"]] = relationship(
        "ChapterVersion",
        back_populates="chapter",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_chapter_project_id", "project_id"),
        Index("idx_chapter_status", "project_id", "status"),
        UniqueConstraint("project_id", "chapter_number", "branch_name"),
    )
