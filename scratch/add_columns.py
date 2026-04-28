import asyncio
import os
from sqlalchemy import text
from app.database.postgres import remote_engine

async def main():
    async with remote_engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE activation_keys ADD COLUMN connection_status VARCHAR NOT NULL DEFAULT 'PENDING';"))
            print("Added connection_status")
        except Exception as e:
            print(f"Error 1: {e}")
        try:
            await conn.execute(text("ALTER TABLE activation_keys ADD COLUMN last_heartbeat_at TIMESTAMP WITH TIME ZONE;"))
            print("Added last_heartbeat_at")
        except Exception as e:
            print(f"Error 2: {e}")

if __name__ == '__main__':
    asyncio.run(main())
