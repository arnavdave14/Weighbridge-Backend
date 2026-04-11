import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_manager import get_remote_db
from app.api.admin_deps import get_current_admin
from app.schemas.admin_schemas import (
    AppCreate, AppRead, AppUpdate,
    ActivationKeyCreate, ActivationKeyRead, ActivationKeyUpdate,
    DashboardStats
)
from app.services.admin_app_service import AdminAppService
from app.repositories.admin_repo import AdminRepo
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/admin/apps", tags=["Admin — Apps"])


# ─────────────────────────────────────────────────────────────
# Dashboard Stats
# ─────────────────────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Aggregated counts for the admin dashboard cards."""
    return await AdminAppService.get_dashboard_stats(db)


@router.get("/dashboard/activity", response_model=List[dict])
async def get_dashboard_activity(
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Activations and Revocations per day for the last 10 days."""
    return await AdminAppService.get_dashboard_activity(db)


# ─────────────────────────────────────────────────────────────
# App (Product) Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("", response_model=AppRead)
async def create_app(
    app_in: AppCreate,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Create a new software product (App). Not a company — a product."""
    return await AdminAppService.create_app(db, app_in)


@router.get("", response_model=List[AppRead])
async def list_apps(
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """List all active software products."""
    return await AdminAppService.list_apps(db)


@router.patch("/{app_id}", response_model=AppRead)
async def update_app(
    app_id: uuid.UUID,
    app_update: AppUpdate,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Update application details, including notification sender identities."""
    return await AdminAppService.update_app(db, app_id, app_update)


@router.delete("/{app_id}")
async def delete_app(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Soft-delete an application."""
    await AdminAppService.delete_app(db, app_id)
    return {"message": "Application soft-deleted successfully."}


@router.get("/history", response_model=List[AppRead])
async def get_app_history(
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """List all soft-deleted software products."""
    return await AdminAppService.get_app_history(db)


# ─────────────────────────────────────────────────────────────
# Activation Key (Company License) Endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/keys", response_model=List[dict])
async def generate_activation_keys(
    key_in: ActivationKeyCreate,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """
    Generate one or more activation keys for a specific App.
    Each key = one company license. Raw keys shown ONCE — save them.
    Asynchronously triggers email and WhatsApp notifications.
    """
    generated_keys = await AdminAppService.generate_keys(db, key_in)
    
    app_data = await AdminRepo.get_app_by_uuid(db, key_in.app_id)
    app_name = app_data.app_name if app_data else "Weighbridge Software"
    
    # Pre-validate to determine the synchronous status message safely
    is_valid_email, is_valid_phone = NotificationService.validate_contact_info(
        key_in.email, key_in.whatsapp_number
    )
    
    if is_valid_email and is_valid_phone:
        status_msg = "queued"
    elif is_valid_email:
        status_msg = "queued_for_email_only"
    elif is_valid_phone:
        status_msg = "queued_for_whatsapp_only"
    elif key_in.email or key_in.whatsapp_number:
        status_msg = "validation_failed"
    else:
        status_msg = "skipped"

    for key_data in generated_keys:
        key_data["notification_status"] = "queued"
        
        # Determine notification targets
        notif_type = key_in.notification_type or "both"
        
        # Parallel dispatch via Celery pool
        if notif_type in ["whatsapp", "both"] and key_in.whatsapp_number:
            from app.tasks.notification_tasks import send_whatsapp_notification_task
            send_whatsapp_notification_task.delay(
                key_data=key_data, 
                app_name=app_name
            )
            
        if notif_type in ["email", "both"] and key_in.email:
            from app.tasks.notification_tasks import send_email_notification_task
            send_email_notification_task.delay(
                key_data=key_data, 
                app_name=app_name
            )

    return generated_keys


@router.get("/{app_uuid}/keys", response_model=List[ActivationKeyRead])
async def list_keys_for_app(
    app_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """List all company licenses (activation keys) for a specific product."""
    return await AdminRepo.get_keys_for_app(db, app_uuid)


@router.get("/keys/all", response_model=List[ActivationKeyRead])
async def list_all_keys(
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin),
    limit: int = 200,
    offset: int = 0
):
    """List all activation keys across all apps with pagination."""
    return await AdminRepo.get_all_keys(db, limit=limit, offset=offset)


@router.patch("/keys/{key_uuid}/rotate-token")
async def rotate_key_token(
    key_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """
    Rotates the machine token for a license.
    Includes a 1-hour grace period for the old token to prevent sync interruptions.
    """
    return await AdminAppService.rotate_token(db, key_uuid)


@router.patch("/keys/{key_uuid}")
async def update_key_details(
    key_uuid: uuid.UUID,
    update_in: ActivationKeyUpdate,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Updates license metadata, branding, or custom labels."""
    return await AdminAppService.update_key(db, key_uuid, update_in)


@router.delete("/keys/{key_uuid}/revoke")
async def revoke_key(
    key_uuid: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Permanently revokes a license key."""
    return await AdminAppService.revoke_key(db, key_uuid)
