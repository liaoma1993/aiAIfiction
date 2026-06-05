from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models import BaseModel


class Faction(BaseModel):
    __tablename__ = "factions"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    faction_type = Column(String(30), nullable=False)
    description = Column(String(2000), default="")
    headquarters = Column(String(500), default="")
    territory = Column(String(1000), default="")
    core_creed = Column(String(1000), default="")
    hierarchy = Column(JSON, default=list)
    notable_members = Column(JSON, default=list)
    faction_timeline = Column(JSON, default=list)
    emblem_description = Column(String(1000), default="")
    color_scheme = Column(String(200), default="")
    core_conflict_of_interest = Column(String(2000), default="")
    internal_faction_cracks = Column(String(1000), default="")
    reputation_and_reality = Column(String(1000), default="")
    strength_trajectory = Column(String(500), default="")
    sort_order = Column(Integer, default=0)

    project = relationship("Project", back_populates="factions", lazy="noload")
    members = relationship("Character", foreign_keys="Character.primary_faction_id", lazy="noload")


class FactionRelation(BaseModel):
    __tablename__ = "faction_relations"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    faction_a_id = Column(String(36), ForeignKey("factions.id", ondelete="CASCADE"), nullable=False)
    faction_b_id = Column(String(36), ForeignKey("factions.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(30), nullable=False)
    timeline_changes = Column(JSON, default=list)
