"""
Admin Repository — all DB access for the SaaS admin system.
Strictly uses PostgreSQL sessions (remote_db / get_remote_db).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.admin_models import App, ActivationKey, Notification, AdminUser, AdminOTP, ActivationKeySchema, MachineNonce, FailedNotification


class AdminRepo:

    # ─────────────────────────────────────────
    # App (Product) Operations
    # ─────────────────────────────────────────

    @staticmethod
    async def create_app(db: AsyncSession, app_id: str, app_name: str, description: Optional[str]) -> App:
        db_app = App(app_id=app_id, app_name=app_name, description=description)
        db.add(db_app)
        await db.commit()
        await db.refresh(db_app)
        return db_app

    @staticmethod
    async def get_all_apps(db: AsyncSession) -> List[App]:
        stmt = (
            select(App, func.count(ActivationKey.id).label("keys_count"))
            .outerjoin(App.keys)
            .where(App.deleted_at == None)
            .group_by(App.id)
            .order_by(App.created_at.desc())
        )
        result = await db.execute(stmt)
        apps_with_counts = []
        for app, count in result.all():
            app.keys_count = count
            apps_with_counts.append(app)
        return apps_with_counts

    @staticmethod
    async def get_deleted_apps(db: AsyncSession) -> List[App]:
        result = await db.execute(select(App).where(App.deleted_at != None).order_by(App.deleted_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def get_app_by_uuid(db: AsyncSession, app_uuid: uuid.UUID) -> Optional[App]:
        result = await db.execute(select(App).where(App.id == app_uuid))
        return result.scalars().first()

    @staticmethod
    async def get_app_by_app_id_string(db: AsyncSession, app_id_str: str) -> Optional[App]:
        """Lookup by the human-readable app_id string (e.g. WB-APP-XXXX)."""
        result = await db.execute(select(App).where(App.app_id == app_id_str, App.deleted_at == None))
        return result.scalars().first()

    @staticmethod
    async def soft_delete_app(db: AsyncSession, app: App) -> None:
        from datetime import datetime, timezone
        app.deleted_at = datetime.now(timezone.utc)
        db.add(app)
        await db.commit()

    # ─────────────────────────────────────────
    # ActivationKey Operations
    # ─────────────────────────────────────────

    @staticmethod
    async def create_activation_key(
        db: AsyncSession,
        app_id: uuid.UUID,
        key_hash: str,
        token: str,
        expiry_date: datetime,
        company_name: str,
        **kwargs
    ) -> ActivationKey:
        db_key = ActivationKey(
            app_id=app_id,
            key_hash=key_hash,
            token=token,
            expiry_date=expiry_date,
            company_name=company_name,
            **kwargs
        )
        db.add(db_key)
        await db.commit()
        await db.refresh(db_key)
        return db_key

    @staticmethod
    async def get_keys_for_app(db: AsyncSession, app_id: uuid.UUID) -> List[ActivationKey]:
        result = await db.execute(
            select(ActivationKey)
            .where(ActivationKey.app_id == app_id)
            .order_by(ActivationKey.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_all_keys(db: AsyncSession, limit: int = 100, offset: int = 0) -> List[ActivationKey]:
        result = await db.execute(
            select(ActivationKey)
            .order_by(ActivationKey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    @staticmethod
    async def get_key_by_uuid(db: AsyncSession, key_id: uuid.UUID) -> Optional[ActivationKey]:
        result = await db.execute(select(ActivationKey).where(ActivationKey.id == key_id))
        return result.scalars().first()

    @staticmethod
    async def update_key(db: AsyncSession, db_key: ActivationKey) -> ActivationKey:
        db.add(db_key)
        await db.commit()
        await db.refresh(db_key)
        return db_key

    @staticmethod
    async def get_key_by_token(db: AsyncSession, token: str) -> Optional[ActivationKey]:
        result = await db.execute(select(ActivationKey).where(ActivationKey.token == token))
        return result.scalars().first()

    @staticmethod
    async def get_key_by_previous_token(db: AsyncSession, token_hash: str) -> Optional[ActivationKey]:
        """Support for rotation grace period."""
        result = await db.execute(select(ActivationKey).where(ActivationKey.previous_token_hash == token_hash))
        return result.scalars().first()

    @staticmethod
    async def get_schema_by_version(db: AsyncSession, key_id: uuid.UUID, version: int) -> Optional[ActivationKeySchema]:
        result = await db.execute(
            select(ActivationKeySchema)
            .where(
                ActivationKeySchema.activation_key_id == key_id,
                ActivationKeySchema.version == version
            )
        )
        return result.scalars().first()

    @staticmethod
    async def get_latest_schema(db: AsyncSession, key_id: uuid.UUID) -> Optional[ActivationKeySchema]:
        result = await db.execute(
            select(ActivationKeySchema)
            .where(ActivationKeySchema.activation_key_id == key_id)
            .order_by(ActivationKeySchema.version.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def count_keys_by_status(db: AsyncSession) -> dict:
        result = await db.execute(
            select(ActivationKey.status, func.count(ActivationKey.id))
            .group_by(ActivationKey.status)
        )
        rows = result.all()
        counts = {"active": 0, "expired": 0, "revoked": 0}
        for status, count in rows:
            counts[status] = count
        return counts

    # ─────────────────────────────────────────
    # Notifications
    # ─────────────────────────────────────────

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        message: str,
        notif_type: str = "warning",
        app_id: Optional[uuid.UUID] = None,
        activation_key_id: Optional[uuid.UUID] = None
    ) -> None:
        notif = Notification(
            app_id=app_id,
            activation_key_id=activation_key_id,
            message=message,
            type=notif_type
        )
        db.add(notif)
        await db.commit()

    @staticmethod
    async def get_all_notifications(db: AsyncSession, limit: int = 100) -> List[Notification]:
        result = await db.execute(
            select(Notification)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def count_recent_notifications(db: AsyncSession, limit: int = 50) -> int:
        result = await db.execute(select(func.count(Notification.id)))
        return result.scalar() or 0

    # ─────────────────────────────────────────
    # Admin User Operations
    # ─────────────────────────────────────────

    @staticmethod
    async def get_admin_by_email(db: AsyncSession, email: str) -> Optional[AdminUser]:
        result = await db.execute(select(AdminUser).where(AdminUser.email == email))
        return result.scalars().first()

    @staticmethod
    async def create_admin(db: AsyncSession, email: str, hashed_password: str) -> AdminUser:
        admin = AdminUser(email=email, hashed_password=hashed_password)
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return admin

    @staticmethod
    async def update_admin_session(db: AsyncSession, admin: AdminUser, session_id: Optional[str]) -> AdminUser:
        admin.session_id = session_id
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return admin

    # ─────────────────────────────────────────
    # Admin OTP Operations
    # ─────────────────────────────────────────

    @staticmethod
    async def create_otp(db: AsyncSession, email: str, otp: str, expires_at: datetime) -> AdminOTP:
        # Delete any existing OTPs for this email first
        from sqlalchemy import delete
        await db.execute(delete(AdminOTP).where(AdminOTP.email == email))
        
        db_otp = AdminOTP(email=email, otp=otp, expires_at=expires_at)
        db.add(db_otp)
        await db.commit()
        await db.refresh(db_otp)
        return db_otp

    @staticmethod
    async def get_otp(db: AsyncSession, email: str, otp: str) -> Optional[AdminOTP]:
        result = await db.execute(
            select(AdminOTP)
            .where(AdminOTP.email == email, AdminOTP.otp == otp)
        )
        return result.scalars().first()

    @staticmethod
    async def delete_otp(db: AsyncSession, otp_record: AdminOTP) -> None:
        await db.delete(otp_record)
        await db.commit()

    # ─────────────────────────────────────────
    # Failed Notifications (DLQ)
    # ─────────────────────────────────────────

    @staticmethod
    async def create_dlq_entry(
        db: AsyncSession,
        channel: str,
        target: str,
        payload: dict,
        error: str,
        retry_count: int
    ) -> FailedNotification:
        from app.models.admin_models import FailedNotification
        entry = FailedNotification(
            channel=channel,
            target=target,
            payload=payload,
            error_reason=error,
            retry_count=str(retry_count), # matches the model's current String type
            status="pending"
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

    @staticmethod
    async def get_dlq_entries(
        db: AsyncSession,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[FailedNotification]:
        from app.models.admin_models import FailedNotification
        stmt = select(FailedNotification).order_by(FailedNotification.failed_at.desc())
        
        if channel:
            stmt = stmt.where(FailedNotification.channel == channel)
        if status:
            stmt = stmt.where(FailedNotification.status == status)
            
        result = await db.execute(stmt.limit(limit).offset(offset))
        return result.scalars().all()

    @staticmethod
    async def get_dlq_entry_by_id(db: AsyncSession, entry_id: uuid.UUID) -> Optional[FailedNotification]:
        from app.models.admin_models import FailedNotification
        result = await db.execute(select(FailedNotification).where(FailedNotification.id == entry_id))
        return result.scalars().first()

    @staticmethod
    async def update_dlq_status(db: AsyncSession, entry: FailedNotification, status: str) -> FailedNotification:
        entry.status = status
        if status in ["resolved", "retried"]:
            entry.resolved_at = datetime.now(timezone.utc)
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry

