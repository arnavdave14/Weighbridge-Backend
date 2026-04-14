import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Application imports
from app.database.postgres import remote_session
from app.models.admin_models import App, ActivationKey, ActivationKeyHistory, AdminUser, FailedNotification
from sqlalchemy import select, delete
from app.services.admin_app_service import AdminAppService
from app.services.notification_service import NotificationService
from app.schemas.admin_schemas import AppCreate
from app.core.rate_limiter import rate_limiter
from app.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_notifications")

async def verify_hardened_system():
    print("\n" + "="*50)
    print("🚀 Starting Production Hardening Verification")
    print("="*50)
    
    async with remote_session() as db:
        # --- [0. SETUP] ---
        admin = (await db.execute(select(AdminUser))).scalars().first()
        if not admin:
            print("❌ Admin user missing. Run reset_databases.py first.")
            return

        ts = int(datetime.now().timestamp())
        app_name = f"Hardened Test {ts}"
        custom_whatsapp_channel = "919893224689:5"
        
        app_in = AppCreate(app_name=app_name, description="Hardening Test")
        app = await AdminAppService.create_app(db, app_in)
        await db.commit()
        print(f"✅ Created App: {app.app_name}")

        test_email = "notif_customer@example.com"
        test_phone = "919999999999"
        key_id = uuid.uuid4()
        
        # Valid Starting Config
        dummy_key = ActivationKey(
            id=key_id, app_id=app.id, key_hash="...", token=f"H-TEST-{ts}", 
            company_name="Hardened Corp", 
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            smtp_enabled=True,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_password="valid_password",
            from_name="Hardened Sender",
            smtp_status="VALID",
            whatsapp_sender_channel=custom_whatsapp_channel
        )
        db.add(dummy_key)
        await db.commit()
        print(f"✅ Created Initial Key with Valid Config")

        key_data = {
            "id": str(key_id),
            "company_name": "Hardened Corp",
            "email": test_email,
            "whatsapp_number": test_phone,
            "subject": "Hardened Test",
            "body": "Hardened Body"
        }

        # --- [1. REDIS & CACHING CHECK] ---
        print("\n--- 1. Redis Connectivity & Caching ---")
        if rate_limiter.is_connected:
            print("✅ Redis is CONNECTED.")
            # Clear any stale cache
            rate_limiter.redis_client.delete(f"license_config:{key_id}")
            
            # Test Caching
            with patch("app.repositories.admin_repo.AdminRepo.get_key_by_uuid", wraps=AdminRepo.get_key_by_uuid) as mock_db:
                # 1st call -> DB
                await NotificationService._get_hydrated_key_config(str(key_id))
                # 2nd call -> Cache
                await NotificationService._get_hydrated_key_config(str(key_id))
                
                if mock_db.call_count == 1:
                    print("✅ Caching verified: Only 1 DB hit for multiple requests.")
                else:
                    print(f"❌ Caching failed: {mock_db.call_count} DB hits.")
        else:
            print("⚠️ Redis is OFFLINE (Fail-Open active).")

        # --- [2. STRICT VALIDATION CHECK] ---
        print("\n--- 2. Schema Validation Rejection ---")
        from pydantic import ValidationError
        from app.schemas.admin_schemas import ActivationKeyUpdate
        
        bad_tests = [
            ({"smtp_host": "wrong user"}, "Invalid SMTP host format"),
            ({"smtp_port": 0}, "SMTP port must be between 1 and 65535"),
            ({"whatsapp_sender_channel": "91999:bad"}, "WhatsApp channel components must be numeric"),
            ({"smtp_user": "notanemail"}, "SMTP User must be a valid email address")
        ]
        
        all_passed = True
        for config, expected_err in bad_tests:
            try:
                ActivationKeyUpdate(**config)
                print(f"❌ FAILED to reject bad config: {config}")
                all_passed = False
            except ValidationError as e:
                if expected_err.lower() in str(e).lower():
                    print(f"✅ Correctly rejected: {config.keys()} -> {expected_err}")
                else:
                    print(f"❌ Rejected with wrong message: {str(e)}")
                    all_passed = False
        if all_passed: print("✅ All schema validation tests passed.")

        # --- [3. ROBUST FALLBACK CHECK] ---
        print("\n--- 3. Robust Fallback (Partial Config) ---")
        # Make key configuration partial but keep it VALID status
        dummy_key.smtp_user = None 
        await db.commit()
        if rate_limiter.is_connected: rate_limiter.redis_client.delete(f"license_config:{key_id}")

        with patch("app.services.email_provider.SMTPProvider.send_email", return_value={"status": "success"}) as mock_send:
            await NotificationService._send_email_safe(test_email, key_data, "Hardened App")
            
            # Check history for EMAIL_SENT_SYSTEM
            hist_fallback = (await db.execute(select(ActivationKeyHistory).where(
                ActivationKeyHistory.activation_key_id == key_id,
                ActivationKeyHistory.reason == "EMAIL_SENT_SYSTEM"
            ))).scalars().first()
            
            if hist_fallback:
                print("✅ Fallback confirmed: Partial key config correctly triggered System SMTP.")
            else:
                print("❌ Fallback failed: System SMTP was not used for partial config.")

        # --- [4. IDEMPOTENCY LOCK CHECK] ---
        print("\n--- 4. Idempotency Implementation ---")
        from app.core.log_utils import generate_idempotency_key
        idem_key = generate_idempotency_key(str(key_id), test_email, "Hardened Test")
        
        is_dup1 = await NotificationService.is_idempotent_duplicate(idem_key)
        is_dup2 = await NotificationService.is_idempotent_duplicate(idem_key)
        
        if rate_limiter.is_connected:
            if not is_dup1 and is_dup2: print("✅ Redis Idempotency Lock verified.")
            else: print(f"❌ Idempotency failed. 1: {is_dup1}, 2: {is_dup2}")
        else:
            print("✅ Fail-Open: Duplicate prevention skipped when Redis is down.")

        # --- [CLEANUP] ---
        await db.delete(dummy_key)
        await db.delete(app)
        await db.commit()
        if rate_limiter.is_connected: rate_limiter.redis_client.delete(f"license_config:{key_id}")
        print("\n🚀 Hardening Verification Complete.")

if __name__ == "__main__":
    asyncio.run(verify_hardened_system())
