from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.database.db_manager import get_remote_db
from app.repositories.admin_repo import AdminRepo
from app.schemas.admin_schemas import FailedNotificationRead
from app.tasks.notification_tasks import send_notification_task

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

    # Queue back to Celery
    # We pass skip_channels=[] to force a full retry, or we can be smart and only retry that channel.
    # Since we store 'channel' in the record, we can retry only that channel.
    skip_channels = []
    # If we want to retry only the channel that failed:
    # However, the task handles multiple channels.
    # Let's just re-dispatch the payload.
    send_notification_task.delay(
        key_data=entry.payload,
        app_name="Retried via Admin Panel",
        skip_channels=[] # Full retry
    )
    
    await AdminRepo.update_dlq_status(db, entry, "retried")
    return {"message": "Notification queued for retry", "id": entry_id}

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
