"""
AdminReceiptService — Business logic layer for the Admin Receipt Viewer.

Architecture:
    Route → AdminReceiptService → AdminReceiptRepo → PostgreSQL

Key responsibilities:
  - Translate raw SQLAlchemy rows into validated Pydantic models
  - Extract dynamic fields (truck_no) from custom_data JSON
  - Compute derived fields (net_weight)
  - Build pagination envelopes
  - Enforce business rules (valid page/limit ranges)
"""
import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repo import AdminReceiptRepo
from app.schemas.admin_schemas import (
    ReceiptAdminRead,
    PaginatedReceiptsResponse,
    MachineAdminRead,
    SortField,
    SortDir,
)


def _extract_truck_no(custom_data: dict) -> Optional[str]:
    """
    Attempts to extract truck number from dynamic custom_data JSON.
    Weighbridge labels vary per tenant — we try common keys.
    """
    if not custom_data or not isinstance(custom_data, dict):
        return None
    # Try common label patterns used in weighbridge receipts
    for key in ("truck_no", "truckNo", "Truck No", "vehicle_no", "Vehicle No", "vehicle", "Truck Number"):
        val = custom_data.get(key)
        if val:
            return str(val)
    # Fallback: scan all values for any key containing "truck" or "vehicle"
    for k, v in custom_data.items():
        if any(kw in k.lower() for kw in ("truck", "vehicle", "lorry")) and v:
            return str(v)
    return None


def _row_to_receipt(row) -> ReceiptAdminRead:
    """
    Converts a SQLAlchemy named-tuple row (from multi-column SELECT) to
    ReceiptAdminRead.
    Row columns: Receipt, ak_company, ak_status, app_name, app_id_str,
                 employee_name, employee_username
    """
    receipt = row.Receipt
    custom_data = receipt.custom_data or {}

    gross = float(receipt.gross_weight) if receipt.gross_weight is not None else 0.0
    tare = float(receipt.tare_weight) if receipt.tare_weight is not None else 0.0

    return ReceiptAdminRead(
        id=receipt.id,
        local_id=receipt.local_id,
        machine_id=receipt.machine_id,
        date_time=receipt.date_time,
        gross_weight=gross,
        tare_weight=tare,
        net_weight=round(gross - tare, 2),
        rate=float(receipt.rate) if receipt.rate is not None else None,
        truck_no=_extract_truck_no(custom_data),
        custom_data=custom_data,
        share_token=receipt.share_token,
        whatsapp_status=receipt.whatsapp_status,
        is_synced=receipt.is_synced,
        sync_attempts=receipt.sync_attempts,
        last_error=receipt.last_error,
        synced_at=receipt.synced_at,
        created_at=receipt.created_at,
        # Tenant enrichment (None for legacy machines with no key_id)
        app_name=getattr(row, "app_name", None),
        app_id_str=getattr(row, "app_id_str", None),
        company_name=getattr(row, "ak_company", None),
        key_status=getattr(row, "ak_status", None),
        # Employee enrichment (None for pre-auth receipts without user_id)
        user_id=getattr(receipt, "user_id", None),
        employee_name=getattr(row, "employee_name", None),
        employee_username=getattr(row, "employee_username", None),
    )


class AdminReceiptService:

    # ─────────────────────────────────────────────────
    # Receipt Listing (primary endpoint)
    # ─────────────────────────────────────────────────

    @staticmethod
    async def list_receipts(
        db: AsyncSession,
        *,
        app_id: Optional[uuid.UUID] = None,
        key_token: Optional[str] = None,
        machine_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        is_synced: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        sort_by: SortField = SortField.created_at,
        sort_dir: SortDir = SortDir.desc,
    ) -> PaginatedReceiptsResponse:
        """
        Primary listing endpoint. Returns paginated, enriched receipts.
        Reads from PostgreSQL only.
        """
        # Guard: clamp to sensible range
        page = max(1, page)
        limit = max(5, min(limit, 200))

        rows, total = await AdminReceiptRepo.get_receipts(
            db,
            app_uuid=app_id,
            key_token=key_token,
            machine_id=machine_id,
            date_from=date_from,
            date_to=date_to,
            is_synced=is_synced,
            search=search,
            page=page,
            limit=limit,
            sort_by=sort_by.value,
            sort_dir=sort_dir.value,
        )

        items = [_row_to_receipt(row) for row in rows]
        pages = math.ceil(total / limit) if total > 0 else 1

        return PaginatedReceiptsResponse(
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            items=items,
        )

    # ─────────────────────────────────────────────────
    # Single Receipt Detail
    # ─────────────────────────────────────────────────

    @staticmethod
    async def get_receipt(db: AsyncSession, receipt_id: int) -> ReceiptAdminRead:
        row = await AdminReceiptRepo.get_receipt_by_id(db, receipt_id)
        if not row:
            raise HTTPException(status_code=404, detail="Receipt not found")
        return _row_to_receipt(row)

    # ─────────────────────────────────────────────────
    # Drill-down: Machines for a Key
    # ─────────────────────────────────────────────────

    @staticmethod
    async def list_machines_for_key(
        db: AsyncSession, key_token: str
    ):
        """Returns machines belonging to an ActivationKey."""
        rows = await AdminReceiptRepo.get_machines_for_key(db, key_token)
        return [
            MachineAdminRead(
                id=row.Machine.id,
                machine_id=row.Machine.machine_id,
                name=row.Machine.name,
                location=row.Machine.location,
                is_active=row.Machine.is_active,
                is_synced=row.Machine.is_synced,
                last_sync_at=row.Machine.last_sync_at,
                receipt_count=row.receipt_count or 0,
                created_at=row.Machine.created_at,
            )
            for row in rows
        ]

    # ─────────────────────────────────────────────────
    # Drill-down: Machines for an App
    # ─────────────────────────────────────────────────

    @staticmethod
    async def list_machines_for_app(
        db: AsyncSession, app_id: uuid.UUID
    ):
        """Returns machines belonging to an App (across all its keys)."""
        rows = await AdminReceiptRepo.get_machines_for_app(db, app_id)
        return [
            MachineAdminRead(
                id=row.Machine.id,
                machine_id=row.Machine.machine_id,
                name=row.Machine.name,
                location=row.Machine.location,
                is_active=row.Machine.is_active,
                is_synced=row.Machine.is_synced,
                last_sync_at=row.Machine.last_sync_at,
                receipt_count=row.receipt_count or 0,
                created_at=row.Machine.created_at,
            )
            for row in rows
        ]
