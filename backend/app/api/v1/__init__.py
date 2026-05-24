"""
API v1

提供 v1 版本所有 API 路由。
"""

from app.api.v1.auth import router as auth_router
from app.api.v1.outlines import router as outlines_router
from app.api.v1.projects import router as projects_router

__all__ = ["auth_router", "projects_router", "outlines_router"]
