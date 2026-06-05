from sqlalchemy import Column, String, Boolean, Integer
from app.models import BaseModel


class LLMProvider(BaseModel):
    __tablename__ = "llm_providers"

    name = Column(String(100), nullable=False, default="")
    provider_type = Column(String(30), nullable=False, default="openai")
    api_key = Column(String(500), nullable=False, default="")
    model = Column(String(100), nullable=False, default="")
    base_url = Column(String(500), nullable=False, default="")
    is_active = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
