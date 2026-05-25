"""
AI Fiction - RuleComplianceReport 模型
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Integer,
    Boolean,
    ForeignKey,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class RuleComplianceReport(BaseModel):
    """规则合规检查报告模型"""

    __tablename__ = "rule_compliance_report"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )

    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chapter.id", ondelete="CASCADE"),
        nullable=True,
        comment="关联章节，NULL表示项目级汇总",
    )

    violations: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="违规项列表 [{rule_id, description, position?, severity: critical|major|minor}]",
    )

    violation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_clean: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    checked_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
