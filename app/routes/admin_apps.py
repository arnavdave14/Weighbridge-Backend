import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_manager import get_remote_db
from app.api.admin_deps import get_current_admin
from app.schemas.admin_schemas import (
    AppCreate, AppRead,
    ActivationKeyCreate, ActivationKeyRead, ActivationKeyUpdate,
    DashboardStats
)
from app.services.admin_app_service import AdminAppService
from app.repositories.admin_repo import AdminRepo

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
    """
    return await AdminAppService.generate_keys(db, key_in)


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


@router.put("/keys/{key_id}", response_model=ActivationKeyRead)
async def update_activation_key(
    key_id: uuid.UUID,
    update_in: ActivationKeyUpdate,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Update company details, billing configuration, expiry, or status."""
    return await AdminAppService.update_key(db, key_id, update_in)


@router.delete("/keys/{key_id}/revoke", response_model=ActivationKeyRead)
async def revoke_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db),
    _: dict = Depends(get_current_admin)
):
    """Permanently revoke a license key."""
    return await AdminAppService.revoke_key(db, key_id)
