"""
Migration: Add communication verification status fields to activation_keys table.

Run with:
    ./venv/bin/python3 scripts/migrate_add_verification_status.py
"""
import asyncio
import logging
from sqlalchemy import text
from app.database.postgres import remote_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")

MIGRATION_SQL = [
    """
    ALTER TABLE activation_keys
    ADD COLUMN IF NOT EXISTS whatsapp_verified BOOLEAN NOT NULL DEFAULT FALSE;
    """,
    """
    ALTER TABLE activation_keys
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;
    """,
    """
    ALTER TABLE activation_keys
    ADD COLUMN IF NOT EXISTS whatsapp_verified_at TIMESTAMPTZ NULL;
    """,
    """
    ALTER TABLE activation_keys
    ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ NULL;
    """,
]

async def run_migration():
    logger.info("Starting migration: add_verification_status_fields")
    async with remote_session() as db:
        for stmt in MIGRATION_SQL:
            logger.info(f"Executing: {stmt.strip()[:80]}...")
            await db.execute(text(stmt))
        await db.commit()
    logger.info("✅ Migration complete. 4 columns added to activation_keys.")

if __name__ == "__main__":
    asyncio.run(run_migration())
