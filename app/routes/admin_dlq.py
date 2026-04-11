from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.database.db_manager import get_remote_db
from app.repositories.admin_repo import AdminRepo
from app.schemas.admin_schemas import FailedNotificationRead
from app.tasks.notification_tasks import send_whatsapp_notification_task, send_email_notification_task

router = APIRouter(prefix="/admin/dlq", tags=["Admin - DLQ"])

@router.get("", response_model=List[FailedNotificationRead])
async def list_dlq_entries(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_remote_db)
):
    """List failed notifications for admin review."""
    return await AdminRepo.get_dlq_entries(db, channel=channel, status=status, limit=limit, offset=offset)

@router.post("/{entry_id}/retry")
async def retry_failed_notification(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db)
):
    """Manually re-trigger a failed notification back into the Celery queue."""
    entry = await AdminRepo.get_dlq_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")
        
    if entry.status == "resolved":
        raise HTTPException(status_code=400, detail="Cannot retry a resolved notification")

    if not entry.can_retry:
        raise HTTPException(
            status_code=400, 
            detail=f"This notification is marked as non-retryable. Reason: {entry.error_reason}"
        )

    # Queue back to Celery based on channel
    if entry.channel == "whatsapp":
        send_whatsapp_notification_task.delay(
            key_data=entry.payload,
            app_name="Retried via Admin Panel (WhatsApp)"
        )
    elif entry.channel == "email":
        send_email_notification_task.delay(
            key_data=entry.payload,
            app_name="Retried via Admin Panel (Email)"
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {entry.channel}")
    
    await AdminRepo.update_dlq_retry_stats(db, entry)
    return {"message": "Notification queued for retry", "id": entry_id, "retry_attempts": entry.retry_attempts_from_dlq + 1}

@router.patch("/{entry_id}/resolve")
async def resolve_failed_notification(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db)
):
    """Mark a failed notification as resolved (e.g. handled manually)."""
    entry = await AdminRepo.get_dlq_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")
        
    await AdminRepo.update_dlq_status(db, entry, "resolved")
    return {"message": "Notification marked as resolved", "id": entry_id}
