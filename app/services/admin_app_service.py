"""
Admin App Service — Business logic for App and ActivationKey management.
"""
import logging
import uuid
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.repositories.admin_repo import AdminRepo
from app.schemas.admin_schemas import AppCreate, AppUpdate, ActivationKeyCreate, ActivationKeyUpdate
from app.core.security import get_password_hash, verify_password, encrypt_password
from app.models.admin_models import App, ActivationKey, ActivationKeySchema, ActivationKeyHistory
from app.core.validation_engine import get_etag
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


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
    async def create_app(db: AsyncSession, app_in: AppCreate) -> App:
        # 1. Uniqueness Check (Global - even deleted apps)
        existing = await db.execute(select(App).where(App.app_name == app_in.app_name))
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail=f"Application name '{app_in.app_name}' is already taken.")

        try:
            return await AdminRepo.create_app(
                db, 
                app_id=app_in.app_id if hasattr(app_in, 'app_id') else f"WB-APP-{uuid.uuid4().hex[:6].upper()}", 
                app_name=app_in.app_name, 
                description=app_in.description
            )
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Conflict: Application with name or ID already exists.")

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

    @staticmethod
    async def update_app(db: AsyncSession, app_id: uuid.UUID, app_update: "AppUpdate") -> App:
        db_app = await AdminRepo.get_app_by_uuid(db, app_id)
        if not db_app:
            raise HTTPException(status_code=404, detail="Application not found")
        
        update_data = app_update.model_dump(exclude_unset=True)
        
        # Handle password encryption
        if "smtp_password" in update_data and update_data["smtp_password"]:
            update_data["smtp_password"] = encrypt_password(update_data["smtp_password"])
            
        return await AdminRepo.update_app(db, db_app, update_data)

    @staticmethod
    async def test_smtp(db: AsyncSession, key_id: uuid.UUID, test_receiver_email: Optional[str] = None) -> dict:
        from app.services.email_provider import SMTPProvider
        from app.core.security import decrypt_password
        
        key = await AdminRepo.get_key_by_uuid(db, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Activation key not found")
        
        if not key.smtp_user or not key.smtp_password:
            raise HTTPException(status_code=400, detail="SMTP User and Password must be configured before testing.")
        
        # Use explicit test receiver or fall back to smtp_user
        receiver = test_receiver_email or key.smtp_user
        
        try:
            decrypted_pass = decrypt_password(key.smtp_password)
            provider = SMTPProvider(
                host=key.smtp_host,
                port=key.smtp_port,
                user=key.smtp_user,
                password=decrypted_pass
            )
            
            test_subject = f"SMTP Verification: {key.company_name}"
            test_body = f"Hello,\n\nThis is a test email to verify your SMTP configuration for {key.company_name}.\n\nIf you received this, your settings are VALID."
            
            res = await provider.send_email(
                to_email=receiver,
                subject=test_subject,
                body=test_body,
                from_email=key.from_email or key.smtp_user,
                from_name=key.from_name or "SMTP Tester"
            )
            
            new_status = "VALID" if res["status"] == "success" else "INVALID"
            key.smtp_status = new_status

            if res["status"] == "success":
                key.email_verified = True
                key.email_verified_at = datetime.now(timezone.utc)
            else:
                key.email_verified = False
                key.email_verified_at = None

            await AdminRepo.update_key(db, key)
            await db.commit()
            
            if res["status"] == "success":
                return {"status": "success", "message": f"Test email delivered to {receiver}. Configuration is VALID."}
            else:
                return {"status": "failed", "reason": res.get("reason", "Unknown failure")}
                
        except Exception as e:
            logger.error(f"SMTP Test Error for Key {key_id}: {e}")
            key.smtp_status = "INVALID"
            key.email_verified = False
            key.email_verified_at = None
            try:
                await db.commit()
            except Exception:
                pass
            return {"status": "failed", "reason": str(e)}

    @staticmethod
    async def test_whatsapp(db: AsyncSession, key_id: uuid.UUID, test_receiver_phone: Optional[str] = None) -> dict:
        """
        Attempts to send a test WhatsApp message using the ActivationKey's configured channel.
        Sends the test message to test_receiver_phone (admin) or key.mobile_number as fallback.
        On success, writes whatsapp_verified=True back to DB.
        """
        from app.services.notification_service import NotificationService
        
        key = await AdminRepo.get_key_by_uuid(db, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Activation key not found")
        
        if not key.whatsapp_sender_channel:
            raise HTTPException(status_code=400, detail="WhatsApp Sender Channel must be configured before testing.")
        
        # Use explicit test receiver or fall back to company's mobile_number
        receiver = test_receiver_phone or key.mobile_number
        if not receiver:
            raise HTTPException(status_code=400, detail="Provide a 'test_receiver_phone' or configure the company's Mobile Number first.")
            
        try:
            test_data = {
                "id": str(key.id),
                "company_name": key.company_name,
                "message": f"✅ WhatsApp sender verification for {key.company_name}. Channel {key.whatsapp_sender_channel} is working correctly."
            }
            
            res = await NotificationService._send_whatsapp_safe(
                phone=receiver,
                key_data=test_data,
                app_name="System Verification",
                sender_channel=key.whatsapp_sender_channel
            )
            
            if res in ["success", "sent"]:
                key.whatsapp_verified = True
                key.whatsapp_verified_at = datetime.now(timezone.utc)
                await AdminRepo.update_key(db, key)
                await db.commit()
                return {"status": "success", "message": f"Test message delivered to {receiver}. Channel is VALID."}
            else:
                key.whatsapp_verified = False
                key.whatsapp_verified_at = None
                await AdminRepo.update_key(db, key)
                await db.commit()
                return {"status": "failed", "reason": res}
                
        except Exception as e:
            logger.error(f"WhatsApp Test Error for Key {key_id}: {e}")
            key.whatsapp_verified = False
            key.whatsapp_verified_at = None
            try:
                await AdminRepo.update_key(db, key)
                await db.commit()
            except Exception:
                pass
            return {"status": "failed", "reason": str(e)}

    # ─────────────────────────────────────────
    # ActivationKey (Company License) Operations
    # ─────────────────────────────────────────

    @staticmethod
    async def generate_keys(db: AsyncSession, key_in: ActivationKeyCreate, admin_id: Optional[uuid.UUID] = None) -> List[dict]:
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

            try:
                # --- Step 1: Pre-generation Uniqueness Check ---
                # Check for existing ACTIVE or EXPIRING_SOON licenses for this exact combination
                existing_check = await db.execute(
                    select(ActivationKey).where(
                        ActivationKey.app_id == key_in.app_id,
                        ActivationKey.company_name == key_in.company_name,
                        ActivationKey.status.in_(["ACTIVE", "EXPIRING_SOON"])
                    )
                )
                if existing_check.scalars().first():
                    raise HTTPException(
                        status_code=400, 
                        detail=f"An active license already exists for '{key_in.company_name}' for this application."
                    )

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
                    labels=[label.model_dump() for label in key_in.labels] if key_in.labels else [],
                    bill_header_1=key_in.bill_header_1,
                    bill_header_2=key_in.bill_header_2,
                    bill_header_3=key_in.bill_header_3,
                    bill_footer=key_in.bill_footer,

                    # Communication Settings
                    smtp_enabled=key_in.smtp_enabled,
                    smtp_host=key_in.smtp_host,
                    smtp_port=key_in.smtp_port,
                    smtp_user=key_in.smtp_user,
                    smtp_password=encrypt_password(key_in.smtp_password) if key_in.smtp_password else None,
                    from_email=key_in.from_email,
                    from_name=key_in.from_name,
                    whatsapp_sender_channel=key_in.whatsapp_sender_channel,
                    email_sender=key_in.email_sender,

                    # Server / LAN Connection Config
                    server_ip=key_in.server_ip,
                    port=key_in.port if key_in.port is not None else 8000,
                )

                # Create audit history for generation
                await AdminRepo.create_history_entry(
                    db, 
                    key_id=db_key.id,
                    new_status="ACTIVE",
                    reason="GENERATION",
                    new_expiry=db_key.expiry_date,
                    changed_by=admin_id
                )

                # Create Version 1 of Schema
                initial_labels = key_in.labels or []
                schema_v1 = ActivationKeySchema(
                    activation_key_id=db_key.id,
                    version=1,
                    labels=db_key.labels,
                    etag=get_etag(db_key.labels)
                )
                db.add(schema_v1)
                await db.flush() # Ensure identity constraint is checked before loop continues

                generated.append({
                    "id": str(db_key.id),
                    "raw_activation_key": raw_key,   # Shown to admin ONCE — never stored plain
                    "company_name": db_key.company_name,
                    "expiry_date": db_key.expiry_date.isoformat(),
                    "status": db_key.status,
                    "email": db_key.email,
                    "whatsapp_number": db_key.whatsapp_number,
                    "message": key_in.message,
                    "subject": key_in.subject,
                    "body": key_in.body,
                    "app_id_str": app.app_id,
                    # Server / LAN Connection Config
                    "server_ip": db_key.server_ip,
                    "port": db_key.port,
                })
            except Exception as e:
                if isinstance(e, IntegrityError):
                    await db.rollback()
                    raise HTTPException(
                        status_code=400, 
                        detail="Conflict: A license with these details already exists or was generated simultaneously."
                    )
                raise e

        # Commit all successful generations
        await db.commit()
        return generated

    @staticmethod
    async def update_key(db: AsyncSession, key_id: uuid.UUID, update_in: ActivationKeyUpdate, admin_id: Optional[uuid.UUID] = None):
        """Update company details, billing, expiry, or status on a key."""
        key = await AdminRepo.get_key_by_uuid(db, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Activation key not found")

        update_data = update_in.model_dump(exclude_unset=True)

        # ── Verification Reset Logic ─────────────────────────────────────────
        # If WhatsApp channel changes, mark it as unverified (stale verification guard)
        WA_FIELDS = {"whatsapp_sender_channel"}
        SMTP_FIELDS = {"smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_enabled"}

        if WA_FIELDS & update_data.keys():
            update_data["whatsapp_verified"] = False
            update_data["whatsapp_verified_at"] = None

        if SMTP_FIELDS & update_data.keys():
            update_data["email_verified"] = False
            update_data["email_verified_at"] = None
        # ────────────────────────────────────────────────────────────────────

        # Versioning Trigger: If labels change, increment version and create snapshot
        if "labels" in update_data and update_data["labels"] != key.labels:
            key.current_version += 1
            new_labels_raw = update_data["labels"]
            # Ensure labels are serialized as dicts, not Pydantic objects
            new_labels = [label.model_dump() if hasattr(label, 'model_dump') else label for label in new_labels_raw]
            
            new_schema_version = ActivationKeySchema(
                activation_key_id=key.id,
                version=key.current_version,
                labels=new_labels,
                etag=get_etag(new_labels)
            )
            update_data["labels"] = new_labels # Update the data passed to setattr later
            db.add(new_schema_version)

        for field, value in update_data.items():
            if field == "smtp_password" and value:
                value = encrypt_password(value)
            setattr(key, field, value)

        # Atomic Status Recalculation if expiry changes
        prev_status = key.status
        prev_expiry = key.expiry_date
        
        if "expiry_date" in update_data:
            now = datetime.now(timezone.utc)
            new_expiry = update_data["expiry_date"]
            if new_expiry > now:
                # Re-activate if it was expired
                key.status = "ACTIVE"
                key.expired_at = None
                key.last_notification_sent = None # Reset sequence
                
                # Check for "Expiring Soon" window (7 days)
                if new_expiry <= (now + timedelta(days=7)):
                    key.status = "EXPIRING_SOON"
            else:
                key.status = "EXPIRED"
                key.expired_at = now

        updated_key = await AdminRepo.update_key(db, key)
        
        # Track history if status or expiry changed
        if "status" in update_data or "expiry_date" in update_data:
            reason = "EXTENSION" if "expiry_date" in update_data else "STATUS_CHANGE"
            await AdminRepo.create_history_entry(
                db,
                key_id=key.id,
                prev_status=prev_status,
                new_status=key.status,
                prev_expiry=prev_expiry,
                new_expiry=key.expiry_date,
                reason=reason,
                changed_by=admin_id
            )
            
        return updated_key

    @staticmethod
    async def test_whatsapp_stateless(sender_channel: str, test_receiver_phone: str) -> dict:
        """
        Stateless WhatsApp test — no key_id required.
        Used in the pre-generation wizard (Step 3) where no license exists yet.
        Does NOT update any DB record.
        """
        from app.services.whatsapp_service import send_whatsapp
        
        if not sender_channel:
            return {"status": "failed", "reason": "WhatsApp Sender Channel is required."}
        if not test_receiver_phone:
            return {"status": "failed", "reason": "A test receiver phone number is required."}

        try:
            result = await send_whatsapp(
                phone=test_receiver_phone,
                message="✅ WhatsApp sender connectivity test. This confirms your channel is working correctly.",
                sender_channel=sender_channel
            )
            if result.get("status") == "success":
                return {"status": "success", "message": f"Test message delivered to {test_receiver_phone}."}
            else:
                return {"status": "failed", "reason": result.get("message", "Provider rejected the message.")}
        except Exception as e:
            logger.error(f"Stateless WA test error: {e}")
            return {"status": "failed", "reason": str(e)}

    @staticmethod
    async def test_smtp_stateless(
        smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str,
        from_email: Optional[str], from_name: Optional[str],
        test_receiver_email: str
    ) -> dict:
        """
        Stateless SMTP test — no key_id required.
        Used in the pre-generation wizard (Step 3) where no license exists yet.
        Does NOT update any DB record.
        """
        from app.services.email_provider import SMTPProvider
        
        if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
            return {"status": "failed", "reason": "SMTP Host, Port, User, and Password are all required."}
        if not test_receiver_email:
            return {"status": "failed", "reason": "A test receiver email is required."}

        try:
            provider = SMTPProvider(
                host=smtp_host,
                port=smtp_port,
                user=smtp_user,
                password=smtp_password
            )
            res = await provider.send_email(
                to_email=test_receiver_email,
                subject="SMTP Connectivity Test",
                body="This is a test email to verify your SMTP configuration. If you received this, your settings are working correctly.",
                from_email=from_email or smtp_user,
                from_name=from_name or "System Test"
            )
            if res.get("status") == "success":
                return {"status": "success", "message": f"Test email delivered to {test_receiver_email}."}
            else:
                return {"status": "failed", "reason": res.get("reason", "Unknown failure")}
        except Exception as e:
            logger.error(f"Stateless SMTP test error: {e}")
            return {"status": "failed", "reason": str(e)}

    @staticmethod
    async def rotate_token(db: AsyncSession, key_id: uuid.UUID):
        """
        Rotates the machine token with a 1-hour grace period for the previous token.
        """
        key = await AdminRepo.get_key_by_uuid(db, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Activation key not found")

        # Set grace period for old token
        key.previous_token_hash = key.token # Storing raw token as 'hash' for simplicity
        key.token_rotation_grace_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Generate new token
        key.token = secrets.token_urlsafe(48)
        key.token_updated_at = datetime.now(timezone.utc)

        return await AdminRepo.update_key(db, key)

    @staticmethod
    async def revoke_key(db: AsyncSession, key_id: uuid.UUID, admin_id: Optional[uuid.UUID] = None):
        key = await AdminRepo.get_key_by_uuid(db, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Activation key not found")
        
        prev_status = key.status
        key.status = "REVOKED"
        key.revoked_at = datetime.now(timezone.utc)
        res = await AdminRepo.update_key(db, key)
        
        await AdminRepo.create_history_entry(
            db,
            key_id=key.id,
            prev_status=prev_status,
            new_status="REVOKED",
            reason="REVOCATION",
            changed_by=admin_id
        )
        return res

    # ─────────────────────────────────────────
    # Hardware Device Activation
    # ─────────────────────────────────────────

    @staticmethod
    async def verify_hardware_activation(
        db: AsyncSession,
        raw_key: str,
        requested_app_id_str: str,
        machine_id: Optional[str] = None,  # GAP-1: optional pre-registration
    ) -> dict:
        """
        Called by the physical weighbridge device during initial setup.
        Validates the raw key AND checks it belongs to the requested App.
        If it belongs to a DIFFERENT app → log a notification + fail.

        GAP-1 FIX: If machine_id is provided, the Machine is immediately
        upserted in PostgreSQL with key_id = matched_key.token.
        This ensures tenant linkage exists before the first receipt sync,
        so the admin panel enriches data from day one.

        The upsert is idempotent:
          - New machine   → INSERT with key_id
          - Known machine → UPDATE key_id only if currently NULL
            (prevents accidental reassignment on re-activation)
        """
        # --- Fallback Recalculation Layer ---
        # Before any verification, we should ensure all keys in memory have fresh statuses
        # We do this by iterating and checking current time against expiry.
        # This acts as a safety layer for if Celery beat is down.
        pass # We will do it lazily for the matched key below to save overhead.

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
                notif_type="error",
                notification_type="hardware_activation_failure"
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
                notification_type="hardware_activation_mismatch",
                app_id=app.id if app else None,
                activation_key_id=matched_key.id,
            )
            raise HTTPException(
                status_code=403,
                detail="This key does not belong to the selected application."
            )

        # --- RECALCULATE STATUS (Fallback check) ---
        now = datetime.now(timezone.utc)
        await AdminAppService._ensure_status_freshness(db, matched_key, now)

        if matched_key.status != "ACTIVE" and matched_key.status != "EXPIRING_SOON":
            await AdminRepo.create_notification(
                db,
                message=f"Attempt to use {matched_key.status} key for company '{matched_key.company_name}'.",
                notif_type="warning",
                notification_type="hardware_activation_status_locked",
                app_id=matched_key.app_id,
                activation_key_id=matched_key.id,
            )
            raise HTTPException(status_code=403, detail=f"License is {matched_key.status}")

        # Check expiry (redundant but safe)
        if matched_key.expiry_date < now:
            raise HTTPException(status_code=403, detail="License has expired")

        # GAP-1 FIX: Pre-register Machine in PostgreSQL if machine_id provided.
        # This is a best-effort operation — failure MUST NOT block activation.
        if machine_id:
            try:
                from app.models.models import Machine
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                from sqlalchemy import text

                # Build the UPSERT:
                # - INSERT new row with key_id set
                # - On conflict (machine_id already exists): update key_id ONLY
                #   if it is currently NULL (idempotent — never overwrites a valid tenant link)
                upsert_stmt = pg_insert(Machine).values(
                    machine_id=machine_id,
                    name=machine_id,        # placeholder; device will update on first sync
                    is_active=True,
                    key_id=matched_key.token,
                    is_synced=False,
                    sync_attempts=0,
                ).on_conflict_do_update(
                    index_elements=["machine_id"],
                    set_={
                        # Only update key_id if the existing row has no tenant linkage
                        # COALESCE(excluded, current) ensures we never overwrite a valid key_id
                        "key_id": text(
                            "COALESCE(machines.key_id, EXCLUDED.key_id)"
                        ),
                    },
                )
                await db.execute(upsert_stmt)
                # Note: commit is called below with the notification
                logger.info(
                    "[Activation] Pre-registered machine=%s with key_id=%s (company=%s)",
                    machine_id, matched_key.token, matched_key.company_name
                )

                await AdminRepo.create_notification(
                    db,
                    message=(
                        f"Hardware activation successful: machine '{machine_id}' "
                        f"linked to '{matched_key.company_name}'."
                    ),
                    notif_type="info",
                    notification_type="hardware_activation_success",
                    app_id=app.id,
                    activation_key_id=matched_key.id,
                )
            except Exception as exc:
                # GAP-1 is best-effort: log but never fail activation
                logger.error(
                    "[Activation] Machine pre-registration failed for %s: %s",
                    machine_id, exc
                )

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
            # LAN Server Connection Config
            # The device stores these and uses them to build its API base URL:
            #   http://{server_ip}:{port}
            "server_ip": matched_key.server_ip,
            "port": matched_key.port,
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
            "active_keys": status_counts.get("ACTIVE", 0) + status_counts.get("EXPIRING_SOON", 0),
            "expired_keys": status_counts.get("EXPIRED", 0),
            "revoked_keys": status_counts.get("REVOKED", 0),
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

    @staticmethod
    async def _ensure_status_freshness(db: AsyncSession, key: ActivationKey, now: datetime):
        """
        Safety layer: Recalculates status in-place if background worker is delayed.
        Ensures audit logging for these automated transitions.
        """
        prev_status = key.status
        if key.expiry_date < now and key.status not in ["EXPIRED", "REVOKED"]:
            key.status = "EXPIRED"
            key.expired_at = now
            await AdminRepo.update_key(db, key)
            await AdminRepo.create_history_entry(
                db, 
                key_id=key.id, 
                prev_status=prev_status, 
                new_status="EXPIRED", 
                reason="AUTO_EXPIRY_FALLBACK"
            )
            logger.warning("[Fallback] Key %s auto-expired during activation fallback check.", key.id)
        
        elif key.status == "ACTIVE" and key.expiry_date <= (now + timedelta(days=7)):
            key.status = "EXPIRING_SOON"
            await AdminRepo.update_key(db, key)
            await AdminRepo.create_history_entry(
                db, 
                key_id=key.id, 
                prev_status=prev_status, 
                new_status="EXPIRING_SOON", 
                reason="AUTO_STATUS_TRANSITION_FALLBACK"
            )
            logger.info("[Fallback] Key %s transitioned to EXPIRING_SOON during activation fallback check.", key.id)
