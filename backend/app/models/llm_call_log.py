from sqlalchemy import Column, Index, Integer, String, ForeignKey, JSON, Text
from app.models import BaseModel


class LLMCallLog(BaseModel):
    __tablename__ = "llm_call_logs"
    __table_args__ = (Index("ix_llm_call_logs_created_at", "created_at"),)

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    project_name = Column(String(200), nullable=False, default="", index=True)
    task_id = Column(String(36), nullable=False, default="", index=True)
    function_name = Column(String(100), nullable=False, default="", index=True)
    provider_id = Column(String(36), nullable=False, default="")
    provider_name = Column(String(100), nullable=False, default="")
    provider_type = Column(String(30), nullable=False, default="")
    model_name = Column(String(120), nullable=False, default="", index=True)
    request_type = Column(String(30), nullable=False, default="chat")
    status = Column(String(20), nullable=False, default="success", index=True)
    system_prompt = Column(Text, nullable=False, default="")
    prompt = Column(Text, nullable=False, default="")
    response_content = Column(Text, nullable=False, default="")
    error_message = Column(Text, nullable=False, default="")
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=False, default=0)
    temperature = Column(String(20), nullable=False, default="")
    max_tokens = Column(Integer, nullable=False, default=0)
    request_payload = Column(JSON, default=dict)
    response_metadata = Column(JSON, default=dict)
