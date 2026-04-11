from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db_manager import get_db
from app.services.integrity_service import IntegrityService
from app.services.audit_service import AuditService
from app.api.admin_deps import get_current_admin
import logging

router = APIRouter(prefix="/integrity", tags=["Security — Integrity"])
logger = logging.getLogger(__name__)

@router.get("/status")
async def get_integrity_status(
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ADMIN ONLY: Checks the current cryptographic health of the receipt chain.
    """
    report = await IntegrityService.verify_chain_integrity(db)
    report["override_active"] = IntegrityService.get_override_mode()
    report["override_expires_at"] = IntegrityService.get_override_expiry()
    return report

@router.post("/override")
async def enable_integrity_override(
    reason: str = Body(..., embed=True),
    duration_minutes: int = Body(60, embed=True),
    admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    ADMIN ONLY: Temporarily bypass integrity blocking.
    Requires an explicit reason. This action is logged with CRITICAL severity.
    Override auto-expires after duration_minutes (Max 1440m / 24h).
    """
    # Log critical audit event
    await AuditService.log_event(
        db=db,
        action_type="ENABLE_INTEGRITY_OVERRIDE",
        resource_type="SECURITY",
        actor_type="USER",
        actor_id=admin.get("sub"),
        severity="CRITICAL",
        metadata={
            "reason": reason,
            "duration_minutes": duration_minutes,
            "requested_by": admin.get("sub")
        }
    )
    await db.commit()
    
    IntegrityService.set_override_mode(duration_minutes)
    expiry = IntegrityService.get_override_expiry()
    
    return {
        "message": f"Integrity override ENABLED for {duration_minutes} minutes.",
        "expires_at": expiry.isoformat() if expiry else None,
        "warning": "This action has been audited and reported to the central server."
    }
