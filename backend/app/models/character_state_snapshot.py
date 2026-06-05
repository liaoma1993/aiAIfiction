from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import BaseModel


class CharacterStateSnapshot(BaseModel):
    __tablename__ = "character_state_snapshots"

    character_id = Column(String(36), ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    volume_id = Column(String(36), ForeignKey("volumes.id", ondelete="CASCADE"), nullable=True)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    chapter_number = Column(Integer, nullable=False)
    snapshot_label = Column(String(200), default="")
    position = Column(String(500), default="")
    ability_level = Column(String(100), default="")
    mental_state = Column(String(500), default="")
    physical_state = Column(String(200), default="")
    faction_id = Column(String(36), ForeignKey("factions.id", ondelete="CASCADE"), nullable=True)
    faction_rank = Column(String(100), nullable=True)
    important_items = Column(JSON, default=list)
    notes = Column(String(1000), default="")

    character = relationship("Character", back_populates="state_snapshots", lazy="noload")
