"""
AI Fiction - ChapterVersion 模型
"""

import uuid

from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ChapterVersion(BaseModel):
    """章节版本模型"""

    __tablename__ = "chapter_version"

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapter.id", ondelete="CASCADE"),
        nullable=False,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_summary: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    trigger_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    modification_instruction: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    quality_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    quality_details: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    diff_from_previous: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    chapter: Mapped["Chapter"] = relationship(
        "Chapter",
        back_populates="versions",
    )

    __table_args__ = (
        Index("idx_version_chapter_id", "chapter_id"),
        UniqueConstraint("chapter_id", "version_number"),
    )
