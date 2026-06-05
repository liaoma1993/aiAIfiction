from sqlalchemy import Column, String, ForeignKey, JSON
from app.models import BaseModel


class WorldSetting(BaseModel):
    __tablename__ = "world_settings"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False)
    geography = Column(JSON, default=dict)
    social_structure = Column(JSON, default=dict)
    power_system = Column(JSON, default=dict)
    history = Column(JSON, default=dict)
    culture = Column(JSON, default=dict)
    special_rules = Column(JSON, default=dict)
    world_logic = Column(JSON, default=dict)
    hard_rules = Column(JSON, default=list)
    tone_rules = Column(JSON, default=list)
    constraints = Column(JSON, default=list)
