from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.repositories.admin_repo import AdminRepo
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.admin_models import AdminUser


class AdminAuthService:

    @staticmethod
    async def authenticate_admin(db: AsyncSession, email: str, password: str) -> dict:
        admin = await AdminRepo.get_admin_by_email(db, email)
        if not admin:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(password, admin.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not admin.is_active:
            raise HTTPException(status_code=403, detail="Account is disabled")

        token = create_access_token(data={"sub": admin.email, "root_admin": True})
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
