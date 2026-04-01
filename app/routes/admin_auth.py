from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_manager import get_remote_db
from app.schemas.admin_schemas import AdminToken
from app.services.admin_auth_service import AdminAuthService

router = APIRouter(prefix="/admin/auth", tags=["Admin Auth"])


@router.post("/login", response_model=AdminToken)
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_remote_db)
):
    """
    Admin login endpoint. Returns a JWT token for all protected admin routes.
    Default credentials (after seeding): admin@weighbridge.com / Admin123!
    """
    return await AdminAuthService.authenticate_admin(db, form_data.username, form_data.password)


@router.post("/seed", tags=["Admin Setup"])
async def seed_admin(db: AsyncSession = Depends(get_remote_db)):
    """
    One-time setup endpoint that creates the default admin user.
    Run this once on fresh deployments. Safe to call multiple times (idempotent).
    """
    await AdminAuthService.seed_first_admin(db)
    return {
        "message": "Admin user seeded.",
        "email": "admin@weighbridge.com",
        "password": "Admin123!",
        "note": "Change credentials immediately in production."
    }
