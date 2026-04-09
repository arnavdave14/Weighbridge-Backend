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
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """
    JWT-protected endpoint — verifies a hardware activation key.
    Requires a valid admin Bearer token in the Authorization header.

    Security chain:
    1. Admin Bearer token is validated first.
    2. Hash-compare raw key against all stored bcrypt hashes.
    3. Ensure the matched key belongs to the requested App (cross-tenant check).
    4. Verify status is 'active' and expiry has not passed.
    5. If machine_id is provided, pre-register Machine in PostgreSQL with key_id.
    6. Return all company-specific configuration if valid.
    """
    return await AdminAppService.verify_hardware_activation(
        db=db,
        raw_key=req.activation_key,
        requested_app_id_str=req.app_id,
        machine_id=req.machine_id,    # GAP-1: pass through optional machine_id
    )
