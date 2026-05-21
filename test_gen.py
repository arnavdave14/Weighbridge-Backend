import asyncio
from datetime import datetime, timedelta, timezone
from app.database.postgres import remote_session
from app.models.admin_models import App, AdminUser
from sqlalchemy import select
from app.services.admin_app_service import AdminAppService
from app.schemas.admin_schemas import ActivationKeyCreate
import json
import random

async def main():
    async with remote_session() as db:
        apps = (await db.execute(select(App).limit(1))).scalars().all()
        app = apps[0]
        
        admins = (await db.execute(select(AdminUser).limit(1))).scalars().all()
        admin_id = admins[0].id if admins else None
        
        key_in = ActivationKeyCreate(
            app_id=app.id,
            company_name=f"Test API Verification {random.randint(1000, 9999)}",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
            quantity=1,
            port=random.randint(7000, 9000)
        )
        
        keys = await AdminAppService.generate_keys(db, key_in, admin_id=admin_id)
        
        print("KEYS:", keys[0])
        
asyncio.run(main())
