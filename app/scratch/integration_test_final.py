
import asyncio
import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from app.database.postgres import remote_session
from app.models.admin_models import App, ActivationKey, ActivationKeyHistory, AdminUser
from sqlalchemy import select, delete
from app.services.admin_app_service import AdminAppService
from app.services.notification_service import NotificationService
from app.schemas.admin_schemas import ActivationKeyCreate

# Setup logging to see the output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration_test")

async def run_integration_test():
    print("🚀 Starting Final Integration Test (WhatsApp & Email)")
    
    test_email = "davearnav2003@gmail.com"
    test_phone = "+919407184405"
    
    async with remote_session() as db:
        # 1. Setup Data
        app_res = await db.execute(select(App).where(App.is_deleted == False))
        app = app_res.scalars().first()
        admin_res = await db.execute(select(AdminUser))
        admin = admin_res.scalars().first()
        
        if not app or not admin:
            print(f"❌ Prerequisites missing. App: {bool(app)}, Admin: {bool(admin)}")
            return

        print(f"Using App: {app.app_name} | Admin: {admin.email}")
        
        # Cleanup any old test licenses for this specific identity to avoid constraint violations
        old_keys = (await db.execute(
            select(ActivationKey).where(
                ActivationKey.app_id == app.id,
                ActivationKey.company_name == "Final Integration Test Co",
                ActivationKey.email == test_email
            )
        )).scalars().all()
        for k in old_keys:
            await db.delete(k)
        await db.commit()

        # 2. Step 1: Generate License
        print("Generating test license...")
        key_in = ActivationKeyCreate(
            app_id=app.id,
            company_name="Final Integration Test Co",
            email=test_email,
            whatsapp_number=test_phone,
            expiry_date=datetime.now(timezone.utc) + timedelta(days=365),
            count=1
        )
        
        generated = await AdminAppService.generate_keys(db, key_in, admin_id=admin.id)
        key_id = uuid.UUID(generated[0]["id"])
        raw_key = generated[0]["raw_activation_key"]
        print(f"✅ License created: {key_id}")

        # 3. Step 2: Trigger WhatsApp
        print(f"Sending real WhatsApp to {test_phone}...")
        key_data = {
            "id": str(key_id),
            "company_name": "Final Integration Test Co",
            "whatsapp_number": test_phone,
            "email": test_email,
            "message": "🚀 *Final Integration Test*\nYour Weighbridge license is ready!\nKey: " + raw_key,
            "app_id_str": app.app_id
        }
        
        try:
            # Using the async internal method to avoid nested asyncio.run()
            wa_status = await NotificationService._send_whatsapp_license_async(key_data, app.app_name)
            print(f"✅ WhatsApp result: {wa_status}")
            
            # Re-fetch DB session to commit the history record if any
            async with remote_session() as hdb:
                await hdb.commit()
                
        except Exception as e:
            print(f"❌ WhatsApp FAILED: {e}")

        # 4. Step 3: Trigger Email
        print(f"Sending real Email to {test_email}...")
        key_data["subject"] = f"Final Integration Test: {app.app_name} License"
        key_data["body"] = f"Hello,\n\nYour production license is ready.\n\nKey: {raw_key}\n\nRegards,\nSupport Team"
        
        try:
            email_status = await NotificationService._send_email_license_async(key_data, app.app_name)
            print(f"✅ Email result: {email_status}")
            
            async with remote_session() as hdb:
                await hdb.commit()
        except Exception as e:
            print(f"❌ Email FAILED: {e}")

        # 5. Step 4: Verify Audit Trail
        print("Verifying Audit Trail...")
        async with remote_session() as vdb:
            hist_res = await vdb.execute(select(ActivationKeyHistory).where(ActivationKeyHistory.activation_key_id == key_id))
            history = hist_res.scalars().all()
            
            reasons = [h.reason for h in history]
            print(f"History events: {reasons}")
            
            if "WA_SENT" in reasons:
                print("✅ WhatsApp delivery logged in history.")
            else:
                print("❌ WhatsApp delivery log MISSING.")
                
            if "EMAIL_SENT" in reasons:
                print("✅ Email delivery logged in history.")
            else:
                print("❌ Email delivery log MISSING (Expected if SMTP placeholders used).")

        print("🚀 Integration Test Sequence Completed.")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
