import asyncio
from app.database.db_manager import get_remote_db
from sqlalchemy.future import select
from app.models.admin_models import ActivationKey

async def check_keys():
    async for db in get_remote_db():
        result = await db.execute(select(ActivationKey))
        keys = result.scalars().all()
        print(f"Total keys: {len(keys)}")
        for k in keys:
            print(f"ID: {k.id}, Status: {k.status}, IP: {k.server_ip}, Port: {k.port}")
        break

if __name__ == "__main__":
    asyncio.run(check_keys())
