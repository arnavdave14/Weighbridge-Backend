import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AuditLog
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        action_type: str,
        resource_type: str,
        actor_type: str = "SYSTEM",
        actor_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        severity: str = "INFO",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Creates an immutable audit log entry.
        """
        try:
            new_log = AuditLog(
                timestamp=datetime.now(timezone.utc),
                actor_type=actor_type,
                actor_id=actor_id,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                severity=severity,
                metadata_json=metadata
            )
            db.add(new_log)
            # We don't commit here; we rely on the caller's transaction
            logger.info(f"[AuditLog] {action_type} on {resource_type}:{resource_id} by {actor_type}:{actor_id}")
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            # We don't want audit logging failure to crash the main operation,
            # but in a high-security system, we might actually want that.
            # For now, we just log the error.
