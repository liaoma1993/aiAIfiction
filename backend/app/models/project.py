from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.models import BaseModel


class Project(BaseModel):
    __tablename__ = "projects"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="未命名项目")
    genre = Column(String(50), nullable=False, default="")
    target_length = Column(String(20), default="medium")
    target_total_words = Column(Integer, default=500000)
    word_count_breakdown = Column(JSON, default=dict)
    story_brief = Column(String(2000), default="")
    master_outline = Column(Text, default="")
    pending_volume_plan = Column(JSON, default=None, nullable=True)
    writing_style = Column(JSON, default=dict)
    core_theme = Column(String(200), default="")
    secondary_themes = Column(JSON, default=list)
    motifs = Column(JSON, default=list)
    narrative_lines = Column(JSON, default=list)
    project_schema_mode = Column(String(30), default="legacy")
    arc_generation_version = Column(String(30), default="legacy")
    chapter_blueprint_version = Column(String(30), default="legacy")
    continuity_upgrade_notes = Column(JSON, default=dict)
    wizard_step = Column(Integer, default=0)
    status = Column(String(20), default="planning")

    volumes = relationship("Volume", back_populates="project", order_by="Volume.sort_order", lazy="noload")
    characters = relationship("Character", back_populates="project", lazy="noload")
    factions = relationship("Faction", back_populates="project", lazy="noload")
    chapters = relationship("Chapter", back_populates="project", lazy="noload")
