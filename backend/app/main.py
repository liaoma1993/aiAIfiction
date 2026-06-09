from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import engine, Base
    import app.models.user
    import app.models.project
    import app.models.project_plan_session
    import app.models.volume
    import app.models.character
    import app.models.character_state_snapshot
    import app.models.faction
    import app.models.timeline
    import app.models.relationship_event
    import app.models.outline
    import app.models.chapter
    import app.models.world_setting
    import app.models.llm_provider
    import app.models.writing_style_skill
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from app.services.schema_migrations import run_schema_migrations
        await conn.run_sync(run_schema_migrations)
    from app.seed import seed_defaults
    await seed_defaults()
    from app.llm import refresh_provider_cache
    refresh_provider_cache()
    from app.services.task_manager import recover_interrupted_tasks
    await recover_interrupted_tasks()
    yield
    await engine.dispose()


app = FastAPI(
    title="AI Fiction Studio",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
