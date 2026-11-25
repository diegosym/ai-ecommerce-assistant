import sys
from pathlib import Path

import psycopg

from app.core.config import get_settings

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIRECTORY = REPOSITORY_ROOT / "db/migrations"


def migrate() -> None:
    migrations = sorted(MIGRATIONS_DIRECTORY.glob("*.sql"))
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        for migration in migrations:
            with connection.transaction():
                connection.execute(migration.read_text(encoding="utf-8"))
            print(f"Applied {migration.name}")
    print(f"Database schema is current ({len(migrations)} migration(s)).")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as error:
        print(f"Database migration failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
