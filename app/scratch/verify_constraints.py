
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.database.postgres import remote_session
from app.models.admin_models import App, ActivationKey
from sqlalchemy import select, delete

async def test_unique_constraint():
    print("--- Running Unique Constraint Verification ---")
    async with remote_session() as db:
        # 1. Setup - find an app
        app_res = await db.execute(select(App).where(App.is_deleted == False))
        app = app_res.scalars().first()
        if not app:
            print("❌ No app found. Please create one first.")
            return

        identity = {
            "app_id": app.id,
            "company_name": "Test Unique Co",
            "email": "unique@test.com",
            "whatsapp_number": "+91000000000"
        }

        # 2. Cleanup previous test data
        await db.execute(delete(ActivationKey).where(ActivationKey.company_name == identity["company_name"]))
        await db.commit()

        # 3. Create First License (ACTIVE)
        print(f"Creating first license for {identity['company_name']}...")
        key1 = ActivationKey(
            **identity,
            key_hash="hash1",
            token="token1",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
            status="ACTIVE"
        )
        db.add(key1)
        await db.commit()
        print("✅ First license created.")

        # 4. Attempt Duplicate ACTIVE License
        print("Attempting to create duplicate ACTIVE license (Should FAIL)...")
        key2 = ActivationKey(
            **identity,
            key_hash="hash2",
            token="token2",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
            status="ACTIVE"
        )
        try:
            db.add(key2)
            await db.commit()
            print("❌ ERROR: Duplicate ACTIVE license was allowed!")
        except Exception as e:
            await db.rollback()
            print(f"✅ SUCCESS: Duplicate blocked by DB. Error: {type(e).__name__}")

        # 5. Revoke First, then Create Second (Should PASS - partial index rule)
        print("Revoking first license...")
        key1.status = "REVOKED"
        await db.merge(key1)
        await db.commit()
        print("✅ First license revoked.")

        print("Attempting to create second ACTIVE license after revocation (Should PASS)...")
        key3 = ActivationKey(
            **identity,
            key_hash="hash3",
            token="token3",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
            status="ACTIVE"
        )
        try:
            db.add(key3)
            await db.commit()
            print("✅ SUCCESS: Second license allowed after first was revoked.")
        except Exception as e:
            await db.rollback()
            print(f"❌ ERROR: Was blocked despite revocation. Error: {e}")

        # 6. Final Cleanup
        await db.execute(delete(ActivationKey).where(ActivationKey.company_name == identity["company_name"]))
        await db.commit()
        print("--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(test_unique_constraint())
