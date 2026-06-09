from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from app.config import get_settings


def _sqlite_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite"):
        return None
    raw = database_url.split(":///", 1)[-1]
    parsed = urlparse(database_url)
    if parsed.path and database_url.startswith("sqlite:////"):
        return Path(parsed.path)
    return Path(raw)


def main() -> None:
    settings = get_settings()
    db_path = _sqlite_path(settings.DATABASE_URL)
    if not db_path:
        raise SystemExit("backup_db only supports SQLite DATABASE_URL. Use pg_dump or provider snapshots for PostgreSQL.")
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    if not db_path.exists():
        raise SystemExit(f"database file not found: {db_path}")

    backup_dir = db_path.parent / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{db_path.stem}-{stamp}{db_path.suffix}"
    shutil.copy2(db_path, target)
    print(f"backup_created: {target}")


if __name__ == "__main__":
    main()
