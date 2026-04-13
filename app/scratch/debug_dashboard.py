
import asyncio
import uuid
from sqlalchemy.future import select
from app.database.postgres import remote_session
from app.models.admin_models import App, ActivationKey

async def inspect():
    async with remote_session() as db:
        res = await db.execute(select(ActivationKey))
        keys = res.scalars().all()
        print(f"\n--- [DEBUG] License Status Check ---")
        for k in keys:
            print(f"Company: {k.company_name} | Status: '{k.status}' | Expiry: {k.expiry_date}")
        
        apps = await db.execute(select(App))
        print(f"\n--- [DEBUG] Apps Check ---")
        for a in apps.scalars().all():
            keys_count = await db.execute(select(len(a.keys))) # Wait this is not how it works
            print(f"App: {a.app_name} | Deleted: {a.is_deleted}")

if __name__ == "__main__":
    asyncio.run(inspect())
