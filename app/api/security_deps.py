from fastapi import Request, HTTPException
from app.services.integrity_service import IntegrityService

async def verify_integrity_block(request: Request):
    """
    Dependency to block critical operations if data integrity is compromised.
    Allows bypass only if IntegrityService override_mode is ENABLED.
    """
    integrity_failed = getattr(request.app.state, "integrity_failed", False)
    
    if integrity_failed and not IntegrityService.get_override_mode():
        raise HTTPException(
            status_code=403,
            detail={
                "error": "CRITICAL_INTEGRITY_FAILURE",
                "message": "Data integrity violation detected during system startup. "
                           "Record creation is locked for auditing. "
                           "An administrator must verify the chain and enable override mode to proceed."
            }
        )
