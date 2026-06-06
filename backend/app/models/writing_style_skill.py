from sqlalchemy import Column, String, Boolean, ForeignKey, JSON, Integer
from app.models import BaseModel


class WritingStyleSkill(BaseModel):
    __tablename__ = "writing_style_skills"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False, default="未命名写作风格")
    description = Column(String(1000), default="")
    source_type = Column(String(30), default="sample")
    source_note = Column(String(500), default="")
    sample_word_count = Column(Integer, default=0)
    style_profile = Column(JSON, default=dict)
    prompt_fragment = Column(String(4000), default="")
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
