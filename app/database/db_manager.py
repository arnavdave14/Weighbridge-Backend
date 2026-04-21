from app.database.sqlite import local_session
from app.database.postgres import remote_session
from app.config.settings import settings


async def get_db():
    """Dependency for Main SQLite Database (Local)."""
    async with local_session() as session:
        yield session


async def get_remote_db():
    """
    Dependency for Remote PostgreSQL Database.
    Used by Admin Panel routes that always require PostgreSQL
    (activation keys, notifications, etc.).
    """
    if not remote_session:
        raise Exception("Remote Database URL not configured")
    async with remote_session() as session:
        yield session


async def get_primary_db():
    """
    Unified dependency that selects the active database based on the
    USE_POSTGRES / effective_db_mode setting:

      USE_POSTGRES=true   (effective_db_mode='postgres')
         → yields a PostgreSQL session   [LAN multi-user mode]

      USE_POSTGRES=false  (effective_db_mode='local' | 'dual')
         → yields the local SQLite session  [single-machine offline mode]

    Used by the Settings API (/settings) and any future routes that
    should work transparently in both deployment modes.

    Important: Admin-only routes that manage activation keys (licenses)
    continue to use get_remote_db() directly, because those records
    always live in PostgreSQL.
    """
    if settings.effective_db_mode == "postgres":
        if not remote_session:
            raise Exception(
                "PostgreSQL is not configured. "
                "Set POSTGRES_URL in .env or switch USE_POSTGRES=false."
            )
        async with remote_session() as session:
            yield session
    else:
        async with local_session() as session:
            yield session
