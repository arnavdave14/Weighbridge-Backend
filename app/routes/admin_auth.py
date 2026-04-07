from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_manager import get_remote_db
from app.schemas.admin_schemas import AdminToken, AdminOTPVerify, OTPResponse
from app.services.admin_auth_service import AdminAuthService

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])


@router.post("/login", response_model=OTPResponse)
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_remote_db)
):
    """
    Step 1: Admin login initiation. Validates credentials and sends OTP to email.
    """
    return await AdminAuthService.authenticate_admin(db, form_data.username, form_data.password)


@router.post("/verify-otp", response_model=AdminToken)
async def verify_otp(
    verify_in: AdminOTPVerify,
    db: AsyncSession = Depends(get_remote_db)
):
    """
    Step 2: Admin OTP verification. Issues JWT token if OTP is valid.
    """
    return await AdminAuthService.verify_otp(db, verify_in.email, verify_in.otp)


@router.post("/seed", tags=["Admin Setup"])
async def seed_admin(db: AsyncSession = Depends(get_remote_db)):
    """
    One-time setup endpoint that creates the default admin user.
    """
    await AdminAuthService.seed_first_admin(db)
    return {
        "message": "Admin user seeded.",
        "email": "admin@weighbridge.com",
        "password": "Admin123!",
        "note": "Change credentials immediately in production."
    }
