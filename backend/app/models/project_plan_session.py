from sqlalchemy import Column, String, ForeignKey, JSON, Integer, UniqueConstraint
from app.models import BaseModel


class ProjectPlanSession(BaseModel):
    __tablename__ = "project_plan_sessions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_project_plan_session_user"),)

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    messages = Column(JSON, default=list)
    selected_genres = Column(JSON, default=list)
    chat_input = Column(String, default="")
    current_draft = Column(JSON, default=dict)
    suggestions = Column(JSON, default=list)
    selected_suggestion_index = Column(Integer, default=0)
    next_questions = Column(JSON, default=list)
    detail_options = Column(JSON, default=list)
