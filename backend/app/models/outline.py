from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import BaseModel


class Outline(BaseModel):
    __tablename__ = "outlines"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)


class OutlineNode(BaseModel):
    __tablename__ = "outline_nodes"

    outline_id = Column(String(36), ForeignKey("outlines.id", ondelete="CASCADE"), nullable=False)
    volume_id = Column(String(36), ForeignKey("volumes.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("outline_nodes.id", ondelete="CASCADE"), nullable=True)
    chapter_number = Column(Integer, nullable=False)
    volume_chapter_number = Column(Integer, nullable=False)
    title = Column(String(300), default="")
    summary = Column(String(2000), default="")
    key_events = Column(JSON, default=list)
    tension_level = Column(Integer, default=5)
    target_words = Column(Integer, default=3500)
    narrative_line = Column(String(50), default="main")
    featured_character_ids = Column(JSON, default=list)
    featured_faction_ids = Column(JSON, default=list)
    featured_location_ids = Column(JSON, default=list)
    emotional_arc = Column(String(1000), default="")
    is_key_chapter = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    volume = relationship("Volume", back_populates="outline_nodes", lazy="noload")


class ForeshadowingPlan(BaseModel):
    __tablename__ = "foreshadowing_plans"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    outline_node_id = Column(String(36), ForeignKey("outline_nodes.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(300), nullable=False)
    description = Column(String(2000), default="")
    plant_stage = Column(String(500), default="")
    reveal_stage = Column(String(500), default="")
    plant_chapter = Column(Integer, nullable=True)
    reveal_chapter = Column(Integer, nullable=True)
    status = Column(String(20), default="planted")
    parent_id = Column(String(36), ForeignKey("foreshadowing_plans.id", ondelete="CASCADE"), nullable=True)
