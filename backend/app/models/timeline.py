from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON
from app.models import BaseModel


class TimelineEvent(BaseModel):
    __tablename__ = "timeline_events"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    narrative_line = Column(String(50), default="main")
    time_point = Column(String(200), nullable=False)
    absolute_day = Column(Integer, nullable=True)
    description = Column(String(2000), nullable=False)
    related_character_ids = Column(JSON, default=list)
    related_faction_ids = Column(JSON, default=list)
    related_location_ids = Column(JSON, default=list)
    is_major_event = Column(Boolean, default=False)
    event_type = Column(String(50), default="")


class StoryStateTrail(BaseModel):
    __tablename__ = "story_state_trails"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    chapter_number = Column(Integer, nullable=False)
    state_snapshot = Column(JSON, default=dict)
    change_description = Column(String(2000), default="")
