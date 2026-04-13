
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from app.database.postgres import remote_session
from app.models.admin_models import App, ActivationKey, ActivationKeyHistory, AdminUser
from sqlalchemy import select, delete
from app.services.admin_app_service import AdminAppService
from app.services.notification_service import NotificationService
from app.schemas.admin_schemas import AppCreate, ActivationKeyCreate
from unittest.mock import patch, MagicMock

async def verify_smtp_system():
    print("🚀 Starting Multi-Tenant SMTP & Fallback Verification")
    
    async with remote_session() as db:
        # 1. Setup Data
        admin = (await db.execute(select(AdminUser))).scalars().first()
        if not admin:
            print("❌ Admin user missing.")
            return

        # Create a Test App with SMTP Config
        app_name = f"Test SMTP App {uuid.uuid4().hex[:4]}"
        app_in = AppCreate(
            app_name=app_name,
            description="Multi-tenant SMTP Test",
            smtp_enabled=True,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="test_password" # Will be encrypted by service
        )
        app = await AdminAppService.create_app(db, app_in)
        print(f"✅ Created App: {app.app_name} (SMTP Enabled)")

        # Create a License for this App
        test_email = "customer@example.com"
        key_in = ActivationKeyCreate(
            app_id=app.id,
            company_name="Test Company",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            email=test_email,
            notification_type="email",
            subject="Test Subject",
            body="Test Body"
        )
        keys = await AdminAppService.generate_keys(db, key_in, admin_id=admin.id)
        key_id = uuid.UUID(keys[0]["id"])
        print(f"✅ Generated Key: {key_id}")

        # ---------------------------------------------------------
        # SCENARIO 1: Company SMTP Success (Mocked)
        # ---------------------------------------------------------
        print("\n--- Scenario 1: Company SMTP Success ---")
        # Mark as VALID manually for test
        app.smtp_status = "VALID"
        await db.commit()
        
        with patch("app.services.email_provider.SMTPProvider.send_email", return_value={"status": "success"}):
            await NotificationService._send_email_safe(test_email, keys[0], app.app_name)
            
        # Verify history
        hist = (await db.execute(select(ActivationKeyHistory).where(
            ActivationKeyHistory.activation_key_id == key_id,
            ActivationKeyHistory.reason == "EMAIL_SENT_COMPANY"
        ))).scalars().first()
        
        if hist:
            print("✅ EMAIL_SENT_COMPANY logged in history.")
        else:
            print("❌ EMAIL_SENT_COMPANY NOT logged.")

        # ---------------------------------------------------------
        # SCENARIO 2: Company SMTP Failure -> Fallback to System
        # ---------------------------------------------------------
        print("\n--- Scenario 2: Company SMTP Failure -> Fallback ---")
        # Reset history check
        
        with patch("app.services.email_provider.SMTPProvider.send_email") as mock_send:
            # First call (company) fails, second call (system) succeeds
            mock_send.side_effect = [{"status": "failed", "reason": "Auth Error"}, {"status": "success"}]
            
            await NotificationService._send_email_safe(test_email, keys[0], app.app_name)

        # Verify history for fallback chain
        reasons = (await db.execute(select(ActivationKeyHistory.reason).where(
            ActivationKeyHistory.activation_key_id == key_id
        ))).scalars().all()
        
        print(f"Audit Trail: {reasons}")
        
        expected = ["EMAIL_FAILED_COMPANY", "EMAIL_FALLBACK_SYSTEM", "EMAIL_SENT_SYSTEM"]
        if all(r in reasons for r in expected):
            print("✅ Full Fallback Audit Trail verified!")
        else:
            print(f"❌ Fallback Audit Trail incomplete. Expected {expected}")

        # ---------------------------------------------------------
        # SCENARIO 3: Per-App Sender Identity
        # ---------------------------------------------------------
        print("\n--- Scenario 3: Sender Identity Override ---")
        app.from_name = "Custom Brand"
        app.from_email = "support@brand.com"
        await db.commit()
        
        with patch("app.services.email_service.send_license_email") as mock_service:
            mock_service.return_value = {"status": "success"}
            await NotificationService._send_email_safe(test_email, keys[0], app.app_name)
            
            # Check if custom name was passed
            call_args = mock_service.call_args
            if call_args and call_args.kwargs.get("sender_name") == "Custom Brand":
                print("✅ Custom sender name correctly propagated.")
            else:
                 print(f"❌ Custom sender name propagation failed. Got {call_args}")

        # Cleanup
        await db.delete(app)
        await db.commit()
        print("\n🚀 Verification Complete.")

if __name__ == "__main__":
    asyncio.run(verify_smtp_system())
