from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.db_manager import get_remote_db
from app.api.admin_deps import get_current_admin
from app.schemas.admin_schemas import NotificationRead
from app.repositories.admin_repo import AdminRepo

router = APIRouter(prefix="/admin/notifications", tags=["Admin — Notifications"])


@router.get("", response_model=List[NotificationRead])
async def list_notifications(
    limit: int = 100,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Retrieve security alerts: invalid activations, wrong app selections, system events."""
    return await AdminRepo.get_all_notifications(db, limit)
