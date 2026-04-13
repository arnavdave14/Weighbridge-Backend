
import asyncio
import uuid
import json
from datetime import datetime, timezone, timedelta
from app.database.postgres import remote_session
from app.models.admin_models import App, ActivationKey, ActivationKeyHistory
from sqlalchemy import select, delete, update
from app.services.admin_app_service import AdminAppService
from app.schemas.admin_schemas import ActivationKeyCreate

async def verify_robustness():
    print("--- Running Robustness & Stabilization Verification ---")
    async with remote_session() as db:
        # Get an app
        app_res = await db.execute(select(App).where(App.is_deleted == False))
        app = app_res.scalars().first()
        if not app:
            print("❌ No app found.")
            return

        # 1. Test Audit History (Generation)
        print("Testing Audit History on Generation...")
        key_in = ActivationKeyCreate(
            app_id=app.id,
            company_name="Audit Test Co",
            email="audit@test.com",
            whatsapp_number="+919999999990",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            count=1
        )
        
        # Cleanup previously failed tests
        old_keys = (await db.execute(select(ActivationKey).where(ActivationKey.company_name == "Audit Test Co"))).scalars().all()
        for k in old_keys:
            await db.delete(k)
        await db.commit()

        generated = await AdminAppService.generate_keys(db, key_in)
        key_id = uuid.UUID(generated[0]["id"])
        
        # Check history
        hist_res = await db.execute(select(ActivationKeyHistory).where(ActivationKeyHistory.activation_key_id == key_id))
        hist = hist_res.scalars().all()
        if any(h.reason == "GENERATION" for h in hist):
            print("✅ Generation audit record found.")
        else:
            print("❌ Generation audit record MISSING.")

        # 2. Test IntegrityError Handling (Duplicate Generation)
        print("Testing IntegrityError (Duplicate Generation)...")
        try:
            # Attempt same generation again
            await AdminAppService.generate_keys(db, key_in)
            print("❌ ERROR: Duplicate generation allowed despite constraints!")
        except Exception as e:
            print(f"✅ SUCCESS: Duplicate blocked. Response: {getattr(e, 'detail', str(e))}")

        # 3. Test Extension & Audit
        print("Testing Extension & Audit...")
        from app.schemas.admin_schemas import ActivationKeyUpdate
        new_expiry = datetime.now(timezone.utc) + timedelta(days=60)
        await AdminAppService.update_key(db, key_id, ActivationKeyUpdate(expiry_date=new_expiry))
        
        hist_res = await db.execute(select(ActivationKeyHistory).where(ActivationKeyHistory.activation_key_id == key_id, ActivationKeyHistory.reason == "EXTENSION"))
        if hist_res.scalars().first():
            print("✅ Extension audit record found.")
        else:
            print("❌ Extension audit record MISSING.")

        # 4. Test Fallback Expiry Check
        print("Testing Fallback Expiry Check...")
        # Force a key to be EXPIRED in dates but ACTIVE in status
        await db.execute(
            update(ActivationKey)
            .where(ActivationKey.id == key_id)
            .values(expiry_date=datetime.now(timezone.utc) - timedelta(days=1), status="ACTIVE")
        )
        await db.commit()
        
        # Re-fetch it to ensure it's "stale" in status
        stale_key = (await db.execute(select(ActivationKey).where(ActivationKey.id == key_id))).scalars().first()
        print(f"Initial status: {stale_key.status} (Expiry: {stale_key.expiry_date})")
        
        # Trigger fallback check (via a internal verification call)
        await AdminAppService._ensure_status_freshness(db, stale_key, datetime.now(timezone.utc))
        await db.commit()
        
        # Check if status flipped
        fresh_key = (await db.execute(select(ActivationKey).where(ActivationKey.id == key_id))).scalars().first()
        print(f"Final status: {fresh_key.status}")
        if fresh_key.status == "EXPIRED":
            print("✅ Fallback expiry check successfully flipped status.")
        else:
            print("❌ Fallback expiry check FAILED to flip status.")

        # Cleanup
        final_keys = (await db.execute(select(ActivationKey).where(ActivationKey.company_name == "Audit Test Co"))).scalars().all()
        for k in final_keys:
            await db.delete(k)
        await db.commit()
        print("--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_robustness())
