"""
AI Fiction - ORM 模型包

统一导出所有 SQLAlchemy 模型，方便外部引用。
"""

from app.models.base import BaseModel
from app.models.user import User
from app.models.user_preference import UserPreference
from app.models.project import Project
from app.models.world_setting import WorldSetting
from app.models.character import Character
from app.models.outline import Outline, OutlineNode
from app.models.generation_task import GenerationTask, TaskLog
from app.models.chapter import Chapter
from app.models.chapter_version import ChapterVersion

__all__ = [
    "BaseModel",
    "User",
    "UserPreference",
    "Project",
    "WorldSetting",
    "Character",
    "Outline",
    "OutlineNode",
    "GenerationTask",
    "TaskLog",
    "Chapter",
    "ChapterVersion",
]
