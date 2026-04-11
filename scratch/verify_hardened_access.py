import asyncio
from sqlalchemy import select
from app.database.sqlite import local_session
from app.models.models import Receipt

async def verify_app_access():
    print("--- Verifying App Access to Encrypted DB ---")
    async with local_session() as db:
        try:
            # Try a simple query
            res = await db.execute(select(Receipt).limit(1))
            receipts = res.scalars().all()
            print(f"✅ SUCCESS: App can read encrypted DB. Found {len(receipts)} records.")
        except Exception as e:
            print(f"❌ ERROR: App failed to read encrypted DB: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_app_access())
