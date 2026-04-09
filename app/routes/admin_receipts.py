"""
Admin Receipts Routes — Read-only receipt viewer for the SaaS Admin Panel.

All endpoints:
  - Protected by get_current_admin (JWT bearer token)
  - Read from PostgreSQL ONLY (get_remote_db)
  - Fully paginated and filterable
  - Audit-logged on every access (GAP-6 FIX)

Endpoint map:
  GET /admin/receipts                          — All receipts, filterable
  GET /admin/receipts/{receipt_id}             — Single receipt detail
  GET /admin/apps/{app_id}/receipts            — Scoped to an App
  GET /admin/apps/{app_id}/machines            — Machines under an App (drill-down)
  GET /admin/keys/{key_id}/receipts            — Scoped to an ActivationKey (company)
  GET /admin/keys/{key_id}/machines            — Machines under a Key (drill-down)
  GET /admin/machines/{machine_id}/receipts    — Scoped to a single Machine

Production hardening applied:
  GAP-5: machine_id exposed as an explicit query param on app/key-scoped endpoints.
  GAP-6: Structured audit logging on every admin data access.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_manager import get_remote_db
from app.api.admin_deps import get_current_admin
from app.services.admin_receipt_service import AdminReceiptService
from app.repositories.admin_repo import AdminRepo
from app.schemas.admin_schemas import (
    PaginatedReceiptsResponse,
    ReceiptAdminRead,
    MachineAdminRead,
    SortField,
    SortDir,
)

router = APIRouter(prefix="/admin", tags=["Admin — Receipts"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Shared query-param dependency
# ─────────────────────────────────────────────────────────────

def receipt_filters(
    date_from: Optional[datetime] = Query(None, description="Start of date range (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="End of date range (ISO 8601)"),
    is_synced: Optional[bool] = Query(None, description="True=synced, False=pending/failed"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in truck no / operator"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(50, ge=5, le=200, description="Items per page"),
    sort_by: SortField = Query(SortField.created_at, description="Sort column"),
    sort_dir: SortDir = Query(SortDir.desc, description="Sort direction"),
):
    """
    Reusable filter dependency injected into all receipt endpoints.
    Note: machine_id is intentionally excluded — it conflicts with path params on
    machine-scoped endpoints and must be injected per-endpoint instead.
    """
    return {
        "machine_id": None,   # Set per-endpoint when filtering by machine
        "date_from": date_from,
        "date_to": date_to,
        "is_synced": is_synced,
        "search": search,
        "page": page,
        "limit": limit,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }


# ─────────────────────────────────────────────────────────────
# All Receipts (across all tenants)
# ─────────────────────────────────────────────────────────────

@router.get("/receipts", response_model=PaginatedReceiptsResponse, summary="List all receipts")
async def list_all_receipts(
    filters: dict = Depends(receipt_filters),
    # GAP-5 FIX: machine_id available as query param on the global endpoint
    machine_id: Optional[str] = Query(None, description="Filter by machine ID"),
    db: AsyncSession = Depends(get_remote_db),
    admin: dict = Depends(get_current_admin),
):
    """
    Returns all receipts across all apps/tenants.
    Supports full filter set: machine_id, date range, sync status, search, sort, pagination.
    """
    if machine_id:
        filters["machine_id"] = machine_id

    # GAP-6: Audit log every admin data access
    logger.info(
        "[AdminAudit] GET /admin/receipts | admin=%s | filters=%s",
        admin.get("sub"), {k: v for k, v in filters.items() if v is not None}
    )
    return await AdminReceiptService.list_receipts(db, **filters)


# ─────────────────────────────────────────────────────────────
# Single Receipt Detail
# ─────────────────────────────────────────────────────────────

@router.get("/receipts/{receipt_id}", response_model=ReceiptAdminRead, summary="Get receipt detail")
async def get_receipt_detail(
    receipt_id: int,
    db: AsyncSession = Depends(get_remote_db),
    admin: dict = Depends(get_current_admin),
):
    """Fetch a single receipt by its database ID with full tenant enrichment."""
    # GAP-6: Audit log
    logger.info("[AdminAudit] GET /admin/receipts/%d | admin=%s", receipt_id, admin.get("sub"))
    return await AdminReceiptService.get_receipt(db, receipt_id)


# ─────────────────────────────────────────────────────────────
# App-Scoped Receipts
# ─────────────────────────────────────────────────────────────

@router.get("/apps/{app_id}/receipts", response_model=PaginatedReceiptsResponse, summary="Receipts for an App")
async def list_receipts_for_app(
    app_id: uuid.UUID,
    filters: dict = Depends(receipt_filters),
    # GAP-5 FIX: machine_id available on app-scoped endpoint
    machine_id: Optional[str] = Query(None, description="Further filter by machine ID"),
    db: AsyncSession = Depends(get_remote_db),
    admin: dict = Depends(get_current_admin),
):
    """
    Returns receipts scoped to a specific App (product).
    All machines belonging to any ActivationKey under this App are included.
    Optionally filter further by machine_id.
    """
    app = await AdminRepo.get_app_by_uuid(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    if machine_id:
        filters["machine_id"] = machine_id

    # GAP-6: Audit log
    logger.info(
        "[AdminAudit] GET /admin/apps/%s/receipts | admin=%s | machine_id=%s",
        app_id, admin.get("sub"), machine_id
    )
    return await AdminReceiptService.list_receipts(db, app_id=app_id, **filters)


@router.get("/apps/{app_id}/machines", response_model=List[MachineAdminRead], summary="Machines under an App")
async def list_machines_for_app(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db),
    admin: dict = Depends(get_current_admin),
):
    """
    Drill-down: returns all machines registered under an App.
    Each machine includes a receipt count for the UI summary.
    """
    app = await AdminRepo.get_app_by_uuid(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    logger.info("[AdminAudit] GET /admin/apps/%s/machines | admin=%s", app_id, admin.get("sub"))
    return await AdminReceiptService.list_machines_for_app(db, app_id)


# ─────────────────────────────────────────────────────────────
# ActivationKey-Scoped Receipts (Tenant/Company level)
# ─────────────────────────────────────────────────────────────

@router.get("/keys/{key_id}/receipts", response_model=PaginatedReceiptsResponse, summary="Receipts for a License Key")
async def list_receipts_for_key(
    key_id: uuid.UUID,
    filters: dict = Depends(receipt_filters),
    # GAP-5 FIX: machine_id available on key-scoped endpoint
    machine_id: Optional[str] = Query(None, description="Further filter by machine ID"),
    db: AsyncSession = Depends(get_remote_db),
    admin: dict = Depends(get_current_admin),
):
    """
    Returns receipts scoped to an ActivationKey (one company/tenant).
    Uses Machine.key_id = ActivationKey.token linkage.
    Optionally filter further by machine_id.
    """
    key = await AdminRepo.get_key_by_uuid(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Activation key not found")

    if machine_id:
        filters["machine_id"] = machine_id

    # GAP-6: Audit log — includes company_name for observability
    logger.info(
        "[AdminAudit] GET /admin/keys/%s/receipts | admin=%s | company=%s | machine_id=%s",
        key_id, admin.get("sub"), key.company_name, machine_id
    )
    return await AdminReceiptService.list_receipts(db, key_token=key.token, **filters)


@router.get("/keys/{key_id}/machines", response_model=List[MachineAdminRead], summary="Machines under a License Key")
async def list_machines_for_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_remote_db),
    admin: dict = Depends(get_current_admin),
):
    """
    Drill-down: returns all machines registered under a specific ActivationKey (company).
    Each machine includes a receipt count.
    """
    key = await AdminRepo.get_key_by_uuid(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Activation key not found")

    logger.info(
        "[AdminAudit] GET /admin/keys/%s/machines | admin=%s | company=%s",
        key_id, admin.get("sub"), key.company_name
    )
    return await AdminReceiptService.list_machines_for_key(db, key.token)


# ─────────────────────────────────────────────────────────────
# Machine-Scoped Receipts
# ─────────────────────────────────────────────────────────────

@router.get("/machines/{machine_id}/receipts", response_model=PaginatedReceiptsResponse, summary="Receipts for a Machine")
async def list_receipts_for_machine(
    machine_id: str,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    is_synced: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=5, le=200),
    sort_by: SortField = Query(SortField.created_at),
    sort_dir: SortDir = Query(SortDir.desc),
    db: AsyncSession = Depends(get_remote_db),
    admin: dict = Depends(get_current_admin),
):
    """
    Returns receipts from a specific machine.
    machine_id is the string identifier stored on the device.
    """
    # GAP-6: Audit log
    logger.info(
        "[AdminAudit] GET /admin/machines/%s/receipts | admin=%s",
        machine_id, admin.get("sub")
    )
    return await AdminReceiptService.list_receipts(
        db,
        machine_id=machine_id,
        date_from=date_from,
        date_to=date_to,
        is_synced=is_synced,
        search=search,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
