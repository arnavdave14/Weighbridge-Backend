import asyncio
import logging
from sqlalchemy import text
from app.database.sqlite import local_engine, local_session
from app.database.postgres import remote_engine, remote_session
from app.database.base import Base
from app.database.admin_base import AdminBase
from app.services.admin_auth_service import AdminAuthService

# Import all models to ensure metadata is populated
from app.models.models import Machine, Receipt, ReceiptImage, License, SyncLog, SyncQueue
from app.models.admin_models import AdminUser, ActivationKey, App
from app.models.employee_model import Employee

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_sqlite():
    logger.info("Starting SQLite database cleanup...")
    async with local_engine.begin() as conn:
        # Drop all tables in Base (SQLite contains only Base tables)
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Dropped all tables from SQLite.")
        
        # Recreate tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Recreated all tables in SQLite.")

async def reset_postgres():
    if not remote_engine:
        logger.warning("Remote PostgreSQL engine not configured. Skipping.")
        return

    logger.info("Starting PostgreSQL database cleanup...")
    async with remote_engine.begin() as conn:
        # PostgreSQL contains both Base and AdminBase tables
        # Drop AdminBase first due to potential dependencies (though we avoid FKs)
        await conn.run_sync(AdminBase.metadata.drop_all)
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Dropped all tables from PostgreSQL.")
        
        # Recreate everything
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(AdminBase.metadata.create_all)
        logger.info("Recreated all tables in PostgreSQL.")

    # Seed the first admin
    async with remote_session() as db:
        await AdminAuthService.seed_first_admin(db)
        logger.info("Seeded default admin user in PostgreSQL.")

async def main():
    try:
        await reset_sqlite()
        await reset_postgres()
        logger.info("!!! DATABASE RESET COMPLETE !!!")
    except Exception as e:
        logger.error(f"Failed to reset databases: {e}")

if __name__ == "__main__":
    asyncio.run(main())
