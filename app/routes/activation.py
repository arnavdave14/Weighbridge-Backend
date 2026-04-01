from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.db_manager import get_remote_db
from app.api.admin_deps import get_current_admin
from app.schemas.admin_schemas import HardwareActivationRequest, HardwareActivationResponse, NotificationRead
from app.services.admin_app_service import AdminAppService
from app.repositories.admin_repo import AdminRepo

router = APIRouter(prefix="/admin/activation", tags=["Admin — Activation"])


@router.post("/verify", response_model=HardwareActivationResponse)
async def verify_hardware_key(
    req: HardwareActivationRequest,
    db: AsyncSession = Depends(get_remote_db)
):
    """
    PUBLIC endpoint — called by the local weighbridge device to activate.
    No admin token required; the key IS the authentication.

    Security chain:
    1. Hash-compare raw key against all stored bcrypt hashes.
    2. Ensure the matched key belongs to the requested App (cross-tenant check).
    3. Verify status is 'active' and expiry has not passed.
    4. Return all company-specific configuration if valid.
    """
    return await AdminAppService.verify_hardware_activation(
        db=db,
        raw_key=req.activation_key,
        requested_app_id_str=req.app_id
    )
