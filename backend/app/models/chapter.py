from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import BaseModel


class Chapter(BaseModel):
    __tablename__ = "chapters"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    outline_node_id = Column(String(36), ForeignKey("outline_nodes.id", ondelete="CASCADE"), nullable=True)
    volume_id = Column(String(36), ForeignKey("volumes.id", ondelete="CASCADE"), nullable=True, index=True)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(300), default="")
    summary = Column(String(2000), default="")
    arc_name = Column(String(100), default="")
    connects_from = Column(String(500), default="")
    connects_to = Column(String(500), default="")
    hook = Column(String(500), default="")
    story_state_snapshot = Column(String(3000), default="")
    characters_in_chapter = Column(JSON, default=list)
    key_events = Column(JSON, default=list)
    minor_events = Column(JSON, default=list)
    blueprint = Column(JSON, default=dict)
    continuity_checks = Column(JSON, default=dict)
    causality_links = Column(JSON, default=list)
    foreshadowing_tasks = Column(JSON, default=list)
    rhythm_profile = Column(JSON, default=dict)
    scene_count = Column(Integer, default=0)
    content = Column(String, default="")
    word_count = Column(Integer, default=0)
    target_words = Column(Integer, default=3500)
    status = Column(String(20), default="planned")
    narrative_line = Column(String(50), default="main")
    quality_score = Column(Integer, nullable=True)
    tension_actual = Column(Integer, nullable=True)
    version = Column(Integer, default=1)

    project = relationship("Project", back_populates="chapters", lazy="noload")


class ChapterVersion(BaseModel):
    __tablename__ = "chapter_versions"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    title = Column(String(300), default="")
    content = Column(String, default="")
    word_count = Column(Integer, default=0)
    source = Column(String(50), default="manual")
    note = Column(String(500), default="")
    generation_config = Column(JSON, default=dict)


class GenerationTask(BaseModel):
    __tablename__ = "generation_tasks"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    precision_config = Column(JSON, default=dict)
    result_summary = Column(JSON, default=dict)
    error_message = Column(String, nullable=True)
    celery_task_id = Column(String, nullable=True)
