"""
API v1 路由汇总

汇总所有 v1 子路由，统一挂载到 /api/v1 前缀下。
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.characters import router as characters_router
from app.api.v1.outlines import router as outlines_router
from app.api.v1.projects import router as projects_router
from app.api.v1.world_settings import router as world_settings_router

api_router = APIRouter()

# 注册子路由
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(world_settings_router)
api_router.include_router(characters_router)
api_router.include_router(outlines_router)


@api_router.get("/health")
async def api_health():
    """API v1 健康检查"""
    return {"status": "ok", "version": "v1"}
