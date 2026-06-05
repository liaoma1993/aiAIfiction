from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import BaseModel


class Character(BaseModel):
    __tablename__ = "characters"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    role_type = Column(String(30), default="配角")
    personality = Column(String(1000), default="")
    background = Column(String(2000), default="")
    motivation = Column(String(1000), default="")
    behavior_pattern = Column(String(1000), default="")
    language_style = Column(String(500), default="")
    emotional_expression = Column(String(500), default="")
    appearance = Column(String(1000), default="")
    primary_faction_id = Column(String(36), ForeignKey("factions.id", ondelete="CASCADE"), nullable=True)
    faction_rank = Column(String(100), nullable=True)
    inner_conflict = Column(String(1000), default="")
    language_fingerprint = Column(String(1000), default="")
    relationship_dynamics = Column(JSON, default=list)
    faction_history = Column(JSON, default=list)
    growth_arc = Column(String(2000), default="")
    growth_arc_preset = Column(String(2000), default="")
    growth_stages = Column(JSON, default=list)
    relationships = Column(JSON, default=list)
    current_state = Column(JSON, default=dict)
    first_appeared_chapter = Column(Integer, nullable=True)
    first_appeared_title = Column(String(200), default="")
    character_class = Column(String(20), default="配角")

    project = relationship("Project", back_populates="characters", lazy="noload")
    primary_faction = relationship("Faction", foreign_keys=[primary_faction_id], lazy="noload")
    state_snapshots = relationship(
        "CharacterStateSnapshot", back_populates="character",
        order_by="CharacterStateSnapshot.chapter_number", lazy="noload"
    )
