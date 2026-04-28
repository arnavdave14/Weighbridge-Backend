from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

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

class HeartbeatRequest(BaseModel):
    activation_key: str

@router.post("/heartbeat", summary="Client software heartbeat")
async def client_heartbeat(
    req: HeartbeatRequest,
    db: AsyncSession = Depends(get_remote_db)
):
    """
    Called periodically or on startup by the client software to indicate it is running.
    """
    # 1. We must verify the key by extracting token
    from app.services.admin_app_service import AdminAppService
    # Wait, we can just do a direct DB query for the key hash. 
    # Actually AdminAppService.verify_hardware_activation does it, but we just want to update heartbeat.
    # Let's extract the UUID from WB-XXXX-XXXX-XXXX
    import re
    from sqlalchemy import select, update
    from app.models.admin_models import ActivationKey
    from sqlalchemy.sql import func
    
    # We should search for the key by ID or hash. AdminAppService uses hash.
    # We can just use the AdminAppService to get the key, or let's do a simple update if we know the token or ID.
    # The client only knows `WB-XXXX-XXXX-XXXX`.
    import bcrypt
    
    # Since bcrypt verify is slow, it's better to add a separate token for heartbeat, or just use the hash.
    # Wait, AdminAppService.get_activation_key is probably there.
    # For now, let's just do a simple query for ACTIVE keys and check hash.
    keys = (await db.execute(select(ActivationKey).where(ActivationKey.status == "ACTIVE"))).scalars().all()
    
    target_key = None
    for k in keys:
        try:
            if bcrypt.checkpw(req.activation_key.encode(), k.key_hash.encode()):
                target_key = k
                break
        except Exception:
            pass
            
    if not target_key:
        raise HTTPException(status_code=401, detail="Invalid key")
        
    target_key.connection_status = "ACTIVE"
    target_key.last_heartbeat_at = func.now()
    await db.commit()
    
    return {"status": "ok"}

