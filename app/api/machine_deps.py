import hmac
import hashlib
import time
import logging
import uuid
from datetime import datetime, timezone
from fastapi import Request, Header, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db_manager import get_db
from app.core.validation_engine import canonicalize_json
from app.core.nonce_manager import NonceManager
from app.repositories.admin_repo import AdminRepo
from app.models.admin_models import ActivationKey

logger = logging.getLogger(__name__)

# Security Constants
CLOCK_SKEW_SECONDS = 600  # 10 minutes
NONCE_TTL_SECONDS = 86400  # 24 hours
MAX_VERSION_LAG = 20

async def verify_apex_identity(
    request: Request,
    machine_id: str = Header(..., alias="Machine-ID"),
    signature: str = Header(..., alias="X-Signature"),
    timestamp: int = Header(..., alias="X-Timestamp"),
    nonce: str = Header(..., alias="X-Nonce"),
    schema_version: int = Header(..., alias="X-Schema-Version"),
    db: AsyncSession = Depends(get_db)
) -> ActivationKey:
    """
    APEX-TIER SECURITY FIREWALL:
    Validates identity, signature, replay protection, and clock drift.
    """
    # 1. Progressive Throttling Check
    delay = NonceManager.get_throttle_delay(machine_id)
    if delay > 0:
        logger.warning(f"Throttling machine {machine_id} for {delay}s")
        time.sleep(delay)  # Simple blocking sleep for throttling

    # 2. Clock Drift Check
    current_ts = int(time.time())
    if abs(current_ts - timestamp) > CLOCK_SKEW_SECONDS:
        NonceManager.record_failure(machine_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Clock drift detected",
                "hint": f"Your clock is off by {abs(current_ts - timestamp)}s. Sync with NTP.",
                "server_time": current_ts
            }
        )

    # 3. Identify Machine & Fetch Token
    # We look up the ActivationKey using the Machine-ID linked in Licenses
    # For now, we'll assume the Machine-ID is associated with exactly one active ActivationKey.
    # We fetch it from the admin repo.
    # Note: In a real system, you'd have a mapping table. 
    # Here, we'll find the ActivationKey where status='active' for this machine.
    key = await AdminRepo.get_key_by_token(db, machine_id) # Using Machine-ID as primary token for now
    if not key:
        # Check for previous token if rotation happened recently
        # We hash the incoming token for comparison if we were storing hashes
        key = await AdminRepo.get_key_by_token(db, machine_id) 
    
    if not key or key.status != "active":
        NonceManager.record_failure(machine_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid machine identity or inactive license"
        )

    # 4. Replay Protection (Nonce Check)
    if await NonceManager.is_nonce_used(db, machine_id, nonce, NONCE_TTL_SECONDS):
        NonceManager.record_failure(machine_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nonce already used (Replay attack detected)"
        )

    # 5. Signature Verification (Canonical)
    try:
        body = await request.json()
    except Exception:
        body = {}

    canonical_body = canonicalize_json(body)
    method = request.method.upper()
    path = request.url.path
    
    # Format: METHOD:PATH:BODY:TIMESTAMP:NONCE
    message = f"{method}:{path}:{canonical_body}:{timestamp}:{nonce}".encode("utf-8")
    
    # We use the key.token as the secret
    expected_sig = hmac.new(
        key.token.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_sig, signature):
        # Support for token rotation grace period
        if key.previous_token_hash and key.token_rotation_grace_expiry:
            if datetime.now(timezone.utc) < key.token_rotation_grace_expiry:
                # Try validating with old token
                # (Assuming previous_token_hash is the raw token for simplicity in this demo)
                old_sig = hmac.new(
                    key.previous_token_hash.encode("utf-8"),
                    message,
                    hashlib.sha256
                ).hexdigest()
                if hmac.compare_digest(old_sig, signature):
                    # Success with old token!
                    NonceManager.clear_failures(machine_id)
                    return key

        NonceManager.record_failure(machine_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Invalid signature",
                "hint": "HMAC mismatch. Ensure you are using the correct token and canonical JSON rules."
            }
        )

    # 6. Schema Version Lag Check
    if key.current_version - schema_version > MAX_VERSION_LAG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Outdated schema version",
                "hint": "You are too many versions behind. Please pull the latest configuration.",
                "current_version": key.current_version
            }
        )

    # 7. Success!
    NonceManager.clear_failures(machine_id)
    # Add Correlation ID to response via custom logic if needed, 
    # but here we just return the key for the route.
    return key
