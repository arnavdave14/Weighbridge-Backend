
import asyncio
import uuid
from app.database.postgres import remote_session
from app.services.admin_app_service import AdminAppService
from app.schemas.admin_schemas import AppCreate, AppUpdate
from app.models.admin_models import App
from sqlalchemy import select
from unittest.mock import patch

async def grand_verification():
    print("🌟 Starting Grand Final Verification...")
    
    async with remote_session() as db:
        # 1. Test App Creation with default SMTP (disabled)
        app_name = f"Final Test App {uuid.uuid4().hex[:4]}"
        app_in = AppCreate(
            app_name=app_name,
            description="Integration test"
        )
        app = await AdminAppService.create_app(db, app_in)
        print(f"✅ Created App: {app.app_name}")
        assert app.smtp_enabled is False
        assert app.smtp_status == "UNTESTED"

        # 2. Test App Update with SMTP Encryption
        app_update = AppUpdate(
            smtp_enabled=True,
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_user="test@gmail.com",
            smtp_password="super_secret_password"
        )
        updated_app = await AdminAppService.update_app(db, app.id, app_update)
        print(f"✅ Updated App with SMTP settings. Password encrypted: {updated_app.smtp_password != 'super_secret_password'}")
        assert updated_app.smtp_enabled is True

        # 3. Test SMTP Validation Endpoint Logic
        print("🛠 Testing SMTP Validation Logic...")
        with patch("app.services.email_provider.SMTPProvider.send_email", return_value={"status": "success"}):
            res = await AdminAppService.test_smtp(db, app.id)
            print(f"✅ Test SMTP Result: {res}")
            
            # Refresh from DB
            await db.refresh(updated_app)
            print(f"✅ Final SMTP Status in DB: {updated_app.smtp_status}")
            assert updated_app.smtp_status == "VALID"

        # Cleanup
        await db.delete(updated_app)
        await db.commit()
    
    print("\n✨ ALL TESTS PASSED! The system is production-ready.")

if __name__ == "__main__":
    asyncio.run(grand_verification())
