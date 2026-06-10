from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.volumes import router as volumes_router
from app.api.v1.characters import router as characters_router
from app.api.v1.factions import router as factions_router
from app.api.v1.outlines import router as outlines_router
from app.api.v1.chapters import router as chapters_router
from app.api.v1.relationships import router as relationships_router
from app.api.v1.world_settings import router as world_settings_router
from app.api.v1.wizard import router as wizard_router
from app.api.v1.providers import router as providers_router
from app.api.v1.llm_call_logs import router as llm_call_logs_router
from app.api.v1.story import router as story_router
from app.api.v1.writing_style_skills import router as writing_style_skills_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(volumes_router)
api_router.include_router(characters_router)
api_router.include_router(factions_router)
api_router.include_router(outlines_router)
api_router.include_router(chapters_router)
api_router.include_router(relationships_router)
api_router.include_router(world_settings_router)
api_router.include_router(wizard_router)
api_router.include_router(providers_router)
api_router.include_router(llm_call_logs_router)
api_router.include_router(story_router)
api_router.include_router(writing_style_skills_router)
