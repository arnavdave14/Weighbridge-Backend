import random
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories.admin_repo import AdminRepo
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.admin_models import AdminUser
from app.services.email_service import send_otp_email
from app.config.settings import settings


class AdminAuthService:

    @staticmethod
    async def authenticate_admin(db: AsyncSession, email: str, password: str) -> dict:
        """
        Step 1: Validate credentials and send OTP.
        """
        admin = await AdminRepo.get_admin_by_email(db, email)
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(password, admin.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not admin.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")

        # Generate 6-digit OTP
        otp = f"{random.randint(100000, 999999)}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=1)

        # Store OTP in DB
        await AdminRepo.create_otp(db, email, otp, expires_at)

        # [DEV ONLY] Log OTP to console if email fails or for quick access
        if settings.DEV_MODE:
            print(f"\n🔑 [DEV MODE] OTP for {email}: {otp}\n")

        # Send OTP via Email
        await send_otp_email(email, otp)

        return {"message": "OTP sent to email"}

    @staticmethod
    async def verify_otp(db: AsyncSession, email: str, otp: str) -> dict:
        """
        Step 2: Verify OTP and issue JWT with session_id.
        """
        otp_record = await AdminRepo.get_otp(db, email, otp)
        
        if not otp_record:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        if datetime.now(timezone.utc) > otp_record.expires_at.replace(tzinfo=timezone.utc):
            await AdminRepo.delete_otp(db, otp_record)
            raise HTTPException(status_code=400, detail="OTP has expired")

        # OTP is valid, delete it
        await AdminRepo.delete_otp(db, otp_record)

        # Get admin user
        admin = await AdminRepo.get_admin_by_email(db, email)
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")

        # Generate new session ID (invalidates old ones)
        new_session_id = str(uuid.uuid4())
        await AdminRepo.update_admin_session(db, admin, new_session_id)

        # Issue token with session_id
        token = create_access_token(data={
            "sub": admin.email, 
            "root_admin": True,
            "session_id": new_session_id
        })
        
        return {"access_token": token, "token_type": "bearer"}

    @staticmethod
    async def seed_first_admin(db: AsyncSession) -> None:
        """Creates default admin if no admin users exist. Idempotent."""
        existing = await AdminRepo.get_admin_by_email(db, "admin@weighbridge.com")
        if not existing:
            hashed = get_password_hash("Admin123!")
            await AdminRepo.create_admin(db, "admin@weighbridge.com", hashed)
            print("✅ Default admin user seeded: admin@weighbridge.com")
        else:
            print("ℹ️  Admin already exists, skipping seed.")
