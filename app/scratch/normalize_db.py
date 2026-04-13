
import asyncio
from sqlalchemy import text
from app.database.postgres import remote_session

async def normalize_statuses():
    async with remote_session() as db:
        print("Normalizing activation_key statuses...")
        await db.execute(text("UPDATE activation_keys SET status = UPPER(status)"))
        await db.commit()
        print("✅ Statuses normalized to uppercase.")

if __name__ == "__main__":
    asyncio.run(normalize_statuses())
