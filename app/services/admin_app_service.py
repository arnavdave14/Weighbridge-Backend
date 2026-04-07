"""
Admin App Service — Business logic for App and ActivationKey management.
"""
import uuid
import secrets
from datetime import datetime, timezone
from typing import List
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repo import AdminRepo
from app.schemas.admin_schemas import AppCreate, ActivationKeyCreate, ActivationKeyUpdate
from app.core.security import get_password_hash, verify_password


def _generate_app_id() -> str:
    """Generate a permanent, human-readable App product ID: WB-APP-XXXX."""
    suffix = secrets.token_hex(3).upper()
    return f"WB-APP-{suffix}"


def _generate_activation_key_string() -> str:
    """Generate a raw activation key: WB-XXXX-XXXX-XXXX."""
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    return f"WB-{'-'.join(parts)}"


class AdminAppService:

    # ─────────────────────────────────────────
    # App (Product) Operations
    # ─────────────────────────────────────────

    @staticmethod
    async def create_app(db: AsyncSession, app_in: AppCreate):
        app_id_str = _generate_app_id()
        return await AdminRepo.create_app(
            db,
            app_id=app_id_str,
            app_name=app_in.app_name,
            description=app_in.description
        )

    @staticmethod
    async def list_apps(db: AsyncSession):
        return await AdminRepo.get_all_apps(db)

    @staticmethod
    async def delete_app(db: AsyncSession, app_id: uuid.UUID):
        app = await AdminRepo.get_app_by_uuid(db, app_id)
        if not app:
            raise HTTPException(status_code=404, detail="App not found")
        await AdminRepo.soft_delete_app(db, app)

    @staticmethod
    async def get_app_history(db: AsyncSession):
        return await AdminRepo.get_deleted_apps(db)

    # ─────────────────────────────────────────
    # ActivationKey (Company License) Operations
    # ─────────────────────────────────────────

    @staticmethod
    async def generate_keys(db: AsyncSession, key_in: ActivationKeyCreate) -> List[dict]:
        """
        Generate `count` activation keys for an App.
        Each key represents one company license with all company-specific data.

        Returns list of dicts with the RAW key string — shown to admin ONCE.
        """
        app = await AdminRepo.get_app_by_uuid(db, key_in.app_id)
        if not app:
            raise HTTPException(status_code=404, detail="App not found")

        generated = []

        for _ in range(key_in.count):
            raw_key = _generate_activation_key_string()
            hashed = get_password_hash(raw_key)
            internal_token = secrets.token_urlsafe(48)

            db_key = await AdminRepo.create_activation_key(
                db=db,
                app_id=key_in.app_id,
                key_hash=hashed,
                token=internal_token,
                expiry_date=key_in.expiry_date,
                company_name=key_in.company_name,
                logo_url=key_in.logo_url,
                signup_image_url=key_in.signup_image_url,
                email=key_in.email,
                address=key_in.address,
                phone=key_in.phone,
                mobile_number=key_in.mobile_number,
                whatsapp_number=key_in.whatsapp_number,
                labels=key_in.labels or [],
                bill_header_1=key_in.bill_header_1,
                bill_header_2=key_in.bill_header_2,
                bill_header_3=key_in.bill_header_3,
                bill_footer=key_in.bill_footer,
            )

            generated.append({
                "id": str(db_key.id),
                "raw_activation_key": raw_key,   # Shown to admin ONCE — never stored plain
                "company_name": db_key.company_name,
                "expiry_date": db_key.expiry_date.isoformat(),
                "status": db_key.status,
            })

        return generated

    @staticmethod
    async def update_key(db: AsyncSession, key_id: uuid.UUID, update_in: ActivationKeyUpdate):
        """Update company details, billing, expiry, or status on a key."""
        key = await AdminRepo.get_key_by_uuid(db, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Activation key not found")

        update_data = update_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(key, field, value)

        return await AdminRepo.update_key(db, key)

    @staticmethod
    async def revoke_key(db: AsyncSession, key_id: uuid.UUID):
        key = await AdminRepo.get_key_by_uuid(db, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Activation key not found")
        key.status = "revoked"
        key.revoked_at = datetime.now(timezone.utc)
        return await AdminRepo.update_key(db, key)

    # ─────────────────────────────────────────
    # Hardware Device Activation
    # ─────────────────────────────────────────

    @staticmethod
    async def verify_hardware_activation(
        db: AsyncSession,
        raw_key: str,
        requested_app_id_str: str
    ) -> dict:
        """
        Called by the physical weighbridge device.
        Validates the raw key AND checks it belongs to the requested App.
        If it belongs to a DIFFERENT app → log a notification + fail.
        """
        all_keys = await AdminRepo.get_all_keys(db)

        matched_key = None
        for k in all_keys:
            if verify_password(raw_key, k.key_hash):
                matched_key = k
                break

        if not matched_key:
            await AdminRepo.create_notification(
                db,
                message=f"Invalid activation key attempted: key does not exist.",
                notif_type="error"
            )
            raise HTTPException(status_code=401, detail="Invalid activation key")

        # Cross-check: key must belong to the requested App
        app = await AdminRepo.get_app_by_uuid(db, matched_key.app_id)
        if not app or app.app_id != requested_app_id_str:
            await AdminRepo.create_notification(
                db,
                message=(
                    f"Wrong app selected during activation. "
                    f"Key belongs to app '{app.app_id if app else 'unknown'}', "
                    f"but device requested '{requested_app_id_str}'."
                ),
                notif_type="error",
                app_id=app.id if app else None,
                activation_key_id=matched_key.id,
            )
            raise HTTPException(
                status_code=403,
                detail="This key does not belong to the selected application."
            )

        if matched_key.status != "active":
            await AdminRepo.create_notification(
                db,
                message=f"Attempt to use {matched_key.status} key for company '{matched_key.company_name}'.",
                notif_type="warning",
                app_id=matched_key.app_id,
                activation_key_id=matched_key.id,
            )
            raise HTTPException(status_code=403, detail=f"License is {matched_key.status}")

        # Check expiry
        now = datetime.now(timezone.utc)
        if matched_key.expiry_date < now:
            matched_key.status = "expired"
            await AdminRepo.update_key(db, matched_key)
            raise HTTPException(status_code=403, detail="License has expired")

        return {
            "status": "success",
            "token": matched_key.token,
            "company_name": matched_key.company_name,
            "expiry_date": matched_key.expiry_date,
            "labels": matched_key.labels or [],
            "bill_header_1": matched_key.bill_header_1,
            "bill_header_2": matched_key.bill_header_2,
            "bill_header_3": matched_key.bill_header_3,
            "bill_footer": matched_key.bill_footer,
            "logo_url": matched_key.logo_url,
            "signup_image_url": matched_key.signup_image_url,
            "email": matched_key.email,
            "address": matched_key.address,
            "phone": matched_key.phone,
            "mobile_number": matched_key.mobile_number,
            "whatsapp_number": matched_key.whatsapp_number,
        }

    # ─────────────────────────────────────────
    # Dashboard Aggregation
    # ─────────────────────────────────────────

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> dict:
        apps = await AdminRepo.get_all_apps(db)
        status_counts = await AdminRepo.count_keys_by_status(db)
        notif_count = await AdminRepo.count_recent_notifications(db)
        total_keys = sum(status_counts.values())

        return {
            "total_apps": len(apps),
            "total_keys": total_keys,
            "active_keys": status_counts.get("active", 0),
            "expired_keys": status_counts.get("expired", 0),
            "revoked_keys": status_counts.get("revoked", 0),
            "recent_notifications": notif_count,
        }

    @staticmethod
    async def get_dashboard_activity(db: AsyncSession) -> List[dict]:
        """
        Calculates activations and revocations for the last 10 days.
        """
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        days = []
        for i in range(9, -1, -1):
            day = now - timedelta(days=i)
            # Normalize to start and end of day for querying
            start_of_day = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            days.append((start_of_day, end_of_day))

        activity = []
        from sqlalchemy import select, func
        from app.models.admin_models import ActivationKey

        for start, end in days:
            # Count Activations (keys created)
            q_act = select(func.count(ActivationKey.id)).where(
                ActivationKey.created_at.between(start, end)
            )
            res_act = await db.execute(q_act)
            count_act = res_act.scalar() or 0

            # Count Revocations (keys revoked)
            q_rev = select(func.count(ActivationKey.id)).where(
                ActivationKey.revoked_at.between(start, end)
            )
            res_rev = await db.execute(q_rev)
            count_rev = res_rev.scalar() or 0

            activity.append({
                "day": start.strftime("%b %d"),
                "activations": count_act,
                "revocations": count_rev
            })

        return activity
