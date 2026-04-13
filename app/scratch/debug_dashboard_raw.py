
import asyncio
from sqlalchemy import text
from app.database.postgres import remote_session

async def inspect():
    async with remote_session() as db:
        res = await db.execute(text("SELECT company_name, status FROM activation_keys"))
        rows = res.all()
        print("\n--- RAW DATABASE STATUSES ---")
        for row in rows:
            print(f"Company: {row[0]} | Status: '{row[1]}'")

if __name__ == "__main__":
    asyncio.run(inspect())
