from sqlalchemy import Column, String, Integer, ForeignKey
from app.models import BaseModel


class RelationshipEvent(BaseModel):
    __tablename__ = "relationship_events"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    character_a_id = Column(String(36), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    character_b_id = Column(String(36), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    chapter_number = Column(Integer, nullable=False)
    old_relation = Column(String(200), nullable=False)
    new_relation = Column(String(200), nullable=False)
    trigger_event = Column(String(1000), nullable=False)
    description = Column(String(2000), default="")
    relation_type = Column(String(50), default="")
    intensity = Column(Integer, default=5)
