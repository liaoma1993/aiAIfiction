from sqlalchemy import select
from app.database import async_session
from app.models.user import User
from app.models.llm_provider import LLMProvider
from app.config import get_settings
from passlib.hash import bcrypt


async def seed_defaults():
    settings = get_settings()
    async with async_session() as db:
        # default user
        existing = (await db.execute(select(User).where(User.email == "admin@aifiction.com"))).scalar_one_or_none()
        if not existing:
            db.add(User(email="admin@aifiction.com", username="admin", password_hash=bcrypt.hash("admin123")))
            await db.flush()

        # default LLM provider if env var is set
        existing_provider = (await db.execute(select(LLMProvider).where(LLMProvider.is_active == True))).scalars().all()
        if not existing_provider and settings.DEEPSEEK_API_KEY:
            db.add(LLMProvider(
                name="默认DeepSeek",
                provider_type="deepseek",
                api_key=settings.DEEPSEEK_API_KEY,
                model=settings.DEEPSEEK_MODEL,
                base_url="https://api.deepseek.com",
                is_active=True,
            ))
        elif not existing_provider and settings.OPENAI_API_KEY:
            db.add(LLMProvider(
                name="默认OpenAI",
                provider_type="openai",
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL,
                base_url="https://api.openai.com/v1",
                is_active=True,
            ))
        await db.commit()
