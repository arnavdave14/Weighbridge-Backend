import asyncio
from sqlalchemy import text
from app.database.postgres import remote_session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    if not remote_session:
        print("Remote session not available")
        return
        
    async with remote_session() as session:
        logger.info("Checking for missing columns in 'receipts' table...")
        
        # SQL to add columns if they don't exist
        # PostgreSQL doesn't have a simple 'IF NOT EXISTS' for columns, 
        # so we use a DO block or individual checks.
        
        migration_sql = """
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='receipts' AND column_name='tenant_id') THEN
                ALTER TABLE receipts ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
                RAISE NOTICE 'Added tenant_id column';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='receipts' AND column_name='version_id') THEN
                ALTER TABLE receipts ADD COLUMN version_id INTEGER REFERENCES software_versions(id);
                RAISE NOTICE 'Added version_id column';
            END IF;
        END $$;
        """
        
        try:
            await session.execute(text(migration_sql))
            await session.commit()
            logger.info("✅ Migration completed successfully (or columns already exist).")
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise e

if __name__ == '__main__':
    asyncio.run(run_migration())
