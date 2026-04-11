
import asyncio
from sqlalchemy import text
from app.database.postgres import remote_engine

async def run_migration():
    if not remote_engine:
        print("No remote engine configured.")
        return
    
    queries = [
        "ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS mobile_number VARCHAR;",
        "ALTER TABLE activation_keys ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR;"
    ]
    
    async with remote_engine.begin() as conn:
        for query in queries:
            print(f"Executing: {query}")
            await conn.execute(text(query))
        print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_migration())
