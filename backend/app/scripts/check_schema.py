from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.services.schema_migrations import MIGRATIONS


async def _main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    expected = [version for version, _, _ in MIGRATIONS]
    async with engine.connect() as conn:
        if settings.DATABASE_URL.startswith("sqlite"):
            rows = await conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
            has_migrations = bool(rows.fetchall())
        else:
            rows = await conn.exec_driver_sql(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'schema_migrations'"
            )
            has_migrations = bool(rows.fetchall())
        if not has_migrations:
            print("schema_migrations: missing")
            print(f"expected_head: {expected[-1] if expected else 'none'}")
            return
        result = await conn.exec_driver_sql("SELECT version FROM schema_migrations ORDER BY version")
        applied = [row[0] for row in result.fetchall()]
        missing = [version for version in expected if version not in applied]
        print(f"database_url: {settings.DATABASE_URL}")
        print(f"expected_head: {expected[-1] if expected else 'none'}")
        print(f"applied: {', '.join(applied) if applied else 'none'}")
        print(f"missing: {', '.join(missing) if missing else 'none'}")
        print("status: ok" if not missing else "status: migration_required")
    await engine.dispose()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
