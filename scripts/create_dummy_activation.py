import asyncio
from sqlalchemy import select
from app.database.postgres import remote_session
from app.models.core import Tenant, SoftwareVersion, User, UserActivation
import uuid
from datetime import datetime

async def create_dummy():
    if not remote_session:
        print("Remote session not available")
        return
        
    naive_now = datetime.utcnow()
    async with remote_session() as session:
        # Create Dummy Tenant
        tenant = Tenant(name=f"Dummy Sync Test Tenant {uuid.uuid4().hex[:4]}", created_at=naive_now)
        session.add(tenant)
        await session.flush()
        
        # Create Dummy Version
        version = SoftwareVersion(name=f"vTest.1.{uuid.uuid4().hex[:4]}", created_at=naive_now)
        session.add(version)
        await session.flush()
        
        # Create Dummy User
        user = User(
            tenant_id=tenant.id,
            email=f"dummy_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            is_active=True,
            is_superuser=False,
            created_at=naive_now
        )
        session.add(user)
        await session.flush()
        
        # Create Dummy Activation
        activation_key = f"TEST-SYNC-KEY-{uuid.uuid4().hex[:8].upper()}"
        activation = UserActivation(
            user_id=user.id,
            tenant_id=tenant.id,
            version_id=version.id,
            activation_key=activation_key,
            is_active=True,
            activated_at=naive_now
        )
        session.add(activation)
        await session.commit()
        
        print(f"--- SUCCESS ---")
        print(f"Created Dummy Tenant ID: {tenant.id}")
        print(f"Created Dummy User ID: {user.id}")
        print(f"Created Dummy Activation Key: {activation_key}")
        
        with open("dummy_test_keys.txt", "w") as f:
            f.write(f"TENANT_ID={tenant.id}\n")
            f.write(f"ACTIVATION_KEY={activation_key}\n")
            
if __name__ == '__main__':
    asyncio.run(create_dummy())
