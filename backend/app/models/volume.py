from sqlalchemy import Column, String, Integer, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models import BaseModel


class Volume(BaseModel):
    __tablename__ = "volumes"
    __table_args__ = (UniqueConstraint("project_id", "volume_number", name="uq_project_volume"),)

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    volume_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(200), default="")
    summary = Column(String(2000), default="")
    outline = Column(String(3000), default="")
    theme = Column(String(500), default="")
    target_words = Column(Integer, default=105000)
    default_chapter_words = Column(Integer, default=3500)
    chapter_count = Column(Integer, default=30)
    tension_curve = Column(JSON, default=list)
    emotional_arc_description = Column(String(500), default="")
    chapter_range_start = Column(Integer, nullable=False)
    chapter_range_end = Column(Integer, nullable=False)
    narrative_line_distribution = Column(JSON, default=dict)
    narrative_arcs = Column(JSON, default=list)
    sort_order = Column(Integer, default=0)

    project = relationship("Project", back_populates="volumes", lazy="noload")
    outline_nodes = relationship("OutlineNode", back_populates="volume", order_by="OutlineNode.sort_order", lazy="noload")
