from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.database import Base

import app.models.user  # noqa: F401
import app.models.project  # noqa: F401
import app.models.project_plan_session  # noqa: F401
import app.models.volume  # noqa: F401
import app.models.character  # noqa: F401
import app.models.character_state_snapshot  # noqa: F401
import app.models.faction  # noqa: F401
import app.models.timeline  # noqa: F401
import app.models.relationship_event  # noqa: F401
import app.models.outline  # noqa: F401
import app.models.chapter  # noqa: F401
import app.models.world_setting  # noqa: F401
import app.models.llm_provider  # noqa: F401
import app.models.writing_style_skill  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _sync_database_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_database_url(get_settings().DATABASE_URL),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database_url = get_settings().DATABASE_URL
    if "+asyncpg" in database_url:
        import asyncio

        asyncio.run(run_async_migrations_online(database_url))
        return

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _sync_database_url(database_url)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations_online(database_url: str) -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
