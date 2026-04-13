import logging
import re
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional, Union

from app.services import email_service, whatsapp_service
from app.core.metrics import metrics
from app.core.log_utils import structured_log
from app.core.rate_limiter import rate_limiter
from app.config.settings import settings
from app.config.settings import settings
from app.database.postgres import remote_session
from app.repositories.admin_repo import AdminRepo
from app.core.security import decrypt_password
from app.services.email_provider import SMTPProvider

logger = logging.getLogger("notification_service")

class NotificationService:
    @staticmethod
    def validate_contact_info(email: Optional[str], phone: Optional[str]) -> Tuple[bool, bool]:
        """
        Level 1 Pre-validation:
        Ensures email matches regex pattern and phone looks like a valid number.
        Returns: (is_valid_email, is_valid_phone)
        """
        is_valid_email = False
        is_valid_phone = False

        if email:
            # Simple regex check / pydantic check
            email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if re.match(email_regex, email):
                is_valid_email = True

        if phone:
            strip_phone = "".join(filter(str.isdigit, phone))
            # Just rough validation: a valid mobile is generally 10 to 15 digits
            if 10 <= len(strip_phone) <= 15:
                is_valid_phone = True

        return is_valid_email, is_valid_phone

    @staticmethod
    async def notify_license_generation_async(
        key_data: Dict[str, Any],
        app_name: str
    ):
        """Standard generation notification."""
        return await NotificationService._notify_license_generation_async_orchestrated(key_data, app_name)

    @staticmethod
    async def notify_license_expiry_async(
        key_data: Dict[str, Any],
        app_name: str,
        days_remaining: int
    ):
        """Specialized notification for impending license expiry."""
        company = key_data.get("company_name", "Customer")
        
        # Templates for expiry alerts
        subject = f"ACTION REQUIRED: Your {app_name} license expires in {days_remaining} days"
        body = (
            f"Dear {company},\n\n"
            f"This is a reminder that your license for {app_name} will expire in {days_remaining} days "
            f"on {key_data.get('expiry_date')}.\n\n"
            f"To avoid any interruption in your operations, please contact your administrator to renew your license.\n\n"
            f"Regards,\n"
            f"Support Team"
        )
        message = f"🚨 *License Expiry Alert*\nDear {company}, your license for {app_name} expires in {days_remaining} days. Please renew to avoid service disruption."

        key_data_copy = key_data.copy()
        key_data_copy["subject"] = subject
        key_data_copy["body"] = body
        key_data_copy["message"] = message

        return await NotificationService._notify_license_generation_async_orchestrated(key_data_copy, app_name)


    @staticmethod
    def send_whatsapp_license_sync(key_data: Dict[str, Any], app_name: str) -> str:
        """Synchronous wrapper for WhatsApp only."""
        return asyncio.run(NotificationService._send_whatsapp_license_async(key_data, app_name))

    @staticmethod
    def send_email_license_sync(key_data: Dict[str, Any], app_name: str) -> str:
        """Synchronous wrapper for Email only."""
        return asyncio.run(NotificationService._send_email_license_async(key_data, app_name))

    @staticmethod
    async def _send_whatsapp_license_async(key_data: Dict[str, Any], app_name: str) -> str:
        phone = key_data.get("whatsapp_number")
        if not phone: return "skipped"
        
        _, is_valid_phone = NotificationService.validate_contact_info(None, phone)
        if not is_valid_phone: return "invalid_contact"

        # Rate Limit
        company_name = key_data.get("company_name", "unknown")
        is_allowed, _ = rate_limiter.check(f"notify:{company_name}", settings.NOTIFICATION_RATE_LIMIT_PER_MINUTE)
        if not is_allowed: return "rate_limited"

        start_time = time.time()
        try:
            sender_channel = None
            app_id_str = key_data.get("app_id_str")
            if app_id_str:
                async with remote_session() as db:
                    app = await AdminRepo.get_app_by_app_id_string(db, app_id_str)
                    if app: sender_channel = app.whatsapp_sender_channel

            await NotificationService._send_whatsapp_safe(phone, key_data, app_name, sender_channel=sender_channel)
            metrics.NOTIFICATIONS_TOTAL.labels(channel="whatsapp", status="sent").inc()
            return "sent"
        except Exception as e:
            metrics.NOTIFICATIONS_TOTAL.labels(channel="whatsapp", status="failed").inc()
            raise e
        finally:
            metrics.NOTIFICATION_LATENCY_SECONDS.labels(channel="whatsapp").observe(time.time() - start_time)

    @staticmethod
    async def _send_email_license_async(key_data: Dict[str, Any], app_name: str) -> str:
        email = key_data.get("email")
        if not email: return "skipped"
        
        is_valid_email, _ = NotificationService.validate_contact_info(email, None)
        if not is_valid_email: return "invalid_contact"

        # Rate Limit
        company_name = key_data.get("company_name", "unknown")
        is_allowed, _ = rate_limiter.check(f"notify:{company_name}", settings.NOTIFICATION_RATE_LIMIT_PER_MINUTE)
        if not is_allowed: return "rate_limited"

        start_time = time.time()
        try:
            sender_name = None
            app_id_str = key_data.get("app_id_str")
            if app_id_str:
                async with remote_session() as db:
                    app = await AdminRepo.get_app_by_app_id_string(db, app_id_str)
                    if app: sender_name = app.email_sender

            await NotificationService._send_email_safe(email, key_data, app_name, sender_name=sender_name)
            metrics.NOTIFICATIONS_TOTAL.labels(channel="email", status="sent").inc()
            return "sent"
        except Exception as e:
            metrics.NOTIFICATIONS_TOTAL.labels(channel="email", status="failed").inc()
            raise e
        finally:
            metrics.NOTIFICATION_LATENCY_SECONDS.labels(channel="email").observe(time.time() - start_time)

    @staticmethod
    def notify_license_generation_sync(
        key_data: Dict[str, Any],
        app_name: str,
        skip_channels: list = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for Celery queue execution.
        Returns a dict of successful and failed channels.
        """
        return asyncio.run(NotificationService._notify_license_generation_async_orchestrated(key_data, app_name, skip_channels))

    @staticmethod
    async def is_idempotent_duplicate(idempotency_key: str) -> bool:
        """Checks Redis for an existing idempotency key. Resilient to Redis failure."""
        from app.core.rate_limiter import rate_limiter
        import redis
        try:
            r = rate_limiter.redis_client
            full_key = f"notif_idempotency:{idempotency_key}"
            # Returns True if set (not duplicate), False if already exists (duplicate)
            is_new = r.set(full_key, "1", ex=settings.NOTIF_IDEMPOTENCY_WINDOW, nx=True)
            return not is_new
        except redis.RedisError as e:
            logger.error(f"Redis Error in idempotency check: {e}. Defaulting to NOT duplicate.")
            return False

    @staticmethod
    async def _notify_license_generation_async_orchestrated(
        key_data: Dict[str, Any],
        app_name: str,
        skip_channels: list = None
    ) -> Dict[str, Any]:
        from app.core.log_utils import generate_idempotency_key, mask_phone, mask_email
        
        email = key_data.get("email")
        phone = key_data.get("whatsapp_number")
        key_id = key_data.get("id", "unknown")
        company_name = key_data.get("company_name", "unknown")

        skip = skip_channels or []
        is_valid_email, is_valid_phone = NotificationService.validate_contact_info(email, phone)
        
        result_state = {
            "success": [],
            "failed": {},
            "skipped": []
        }

        # 1. Validation Logic: Isoalted per channel
        # Email Check
        if "email" not in skip:
            if not email:
                result_state["skipped"].append("email")
            elif not is_valid_email:
                result_state["failed"]["email"] = "Invalid email format"
                structured_log(logger, logging.WARNING, "validation_failure", channel="email", target=email, error_message="Invalid email format")
            
        # WhatsApp Check
        if "whatsapp" not in skip:
            if not phone:
                result_state["skipped"].append("whatsapp")
            elif not is_valid_phone:
                result_state["failed"]["whatsapp"] = "Invalid phone format (10-15 digits)"
                structured_log(logger, logging.WARNING, "validation_failure", channel="whatsapp", target=phone, error_message="Invalid phone format")

        # 2. Hardening: Idempotency & Rate Limiting (Batch)
        # We only check for channels that passed validation and aren't skipped
        active_channels = []
        if is_valid_phone and "whatsapp" not in skip and "whatsapp" not in result_state["failed"]:
            active_channels.append(("whatsapp", phone))
        if is_valid_email and "email" not in skip and "email" not in result_state["failed"]:
            active_channels.append(("email", email))

        for channel, target in active_channels:
            # A. Idempotency Check
            idem_key = generate_idempotency_key(str(key_id), target, key_data.get("message", ""))
            if await NotificationService.is_idempotent_duplicate(idem_key):
                structured_log(logger, logging.INFO, "idempotency_skip", channel=channel, target=target, key_id=key_id)
                result_state["skipped"].append(channel)
                continue

            # B. Rate Limiting Check (Multi-Level)
            # Tenant level + Receiver level
            checks = [
                (f"tenant:{company_name}", settings.RATE_LIMIT_TENANT, 60),
                (f"receiver:{target}", settings.RATE_LIMIT_RECEIVER, 60)
            ]
            allowed, results = rate_limiter.check_multi(checks)
            
            if not allowed:
                tenant_allowed, _ = results[0]
                receiver_allowed, _ = results[1]
                error_msg = "Rate limit exceeded"
                if not tenant_allowed: error_msg += " (Tenant)"
                if not receiver_allowed: error_msg += " (Receiver)"
                
                structured_log(logger, logging.WARNING, "rate_limit_exceeded", channel=channel, target=target, error_message=error_msg)
                result_state["failed"][channel] = error_msg
                continue

            # 3. Execution (Sequential inside worker is fine)
            start_time = time.time()
            try:
                if channel == "whatsapp":
                    sender_channel = None
                    app_id_str = key_data.get("app_id_str")
                    if app_id_str:
                        async with remote_session() as db:
                            app = await AdminRepo.get_app_by_app_id_string(db, app_id_str)
                            if app: sender_channel = app.whatsapp_sender_channel
                    await NotificationService._send_whatsapp_safe(target, key_data, app_name, sender_channel=sender_channel)
                
                elif channel == "email":
                    sender_name = None
                    app_id_str = key_data.get("app_id_str")
                    if app_id_str:
                        async with remote_session() as db:
                            app = await AdminRepo.get_app_by_app_id_string(db, app_id_str)
                            if app: sender_name = app.email_sender
                    await NotificationService._send_email_safe(target, key_data, app_name, sender_name=sender_name)
                
                result_state["success"].append(channel)
                metrics.NOTIFICATIONS_TOTAL.labels(channel=channel, status="sent").inc()
            except Exception as e:
                result_state["failed"][channel] = str(e)
                metrics.NOTIFICATIONS_TOTAL.labels(channel=channel, status="failed").inc()
            finally:
                metrics.NOTIFICATION_LATENCY_SECONDS.labels(channel=channel).observe(time.time() - start_time)

        return result_state

    @staticmethod
    async def get_smtp_provider_for_app(app: Any) -> Optional[SMTPProvider]:
        """
        Logic:
        IF app.smtp_enabled == true AND smtp_status == VALID:
        → use company SMTP (decrypt password)
        ELSE:
        → return None (Fallback)
        """
        if not app.smtp_enabled or app.smtp_status != "VALID":
            return None
        
        try:
            decrypted_pass = decrypt_password(app.smtp_password)
            return SMTPProvider(
                host=app.smtp_host,
                port=app.smtp_port,
                user=app.smtp_user,
                password=decrypted_pass
            )
        except Exception as e:
            logger.error(f"Failed to initialize Company SMTP for App {app.app_name}: {e}")
            return None

    @staticmethod
    async def _send_email_safe(email: str, key_data: Dict[str, Any], app_name: str, sender_name: str = None):
        structured_log(logger, logging.INFO, "notification_initiated", channel="email", target=email)
        
        # 1. Resolve App and Provider
        app_id_str = key_data.get("app_id_str")
        key_id = key_data.get("id")
        
        app = None
        company_provider = None
        
        async with remote_session() as db:
            if app_id_str:
                app = await AdminRepo.get_app_by_app_id_string(db, app_id_str)
            
            if app:
                company_provider = await NotificationService.get_smtp_provider_for_app(app)

            # 2. Attempt Company SMTP if available
            if company_provider:
                res = await email_service.send_license_email(
                    email, key_data, app_name, 
                    sender_name=app.from_name or sender_name,
                    providerOverride=company_provider
                )
                
                if res.get("status") == "success":
                    await AdminRepo.create_history_entry(
                        db, key_id=uuid.UUID(key_id), new_status="ACTIVE",
                        reason="EMAIL_SENT_COMPANY"
                    )
                    structured_log(logger, logging.INFO, "notification_completed", channel="email", target=email, provider="company")
                    return
                else:
                    error_msg = res.get("reason", "Unknown failure")
                    await AdminRepo.create_history_entry(
                        db, key_id=uuid.UUID(key_id), new_status="ACTIVE",
                        reason="EMAIL_FAILED_COMPANY",
                        # We'll put the error in a dedicated message if we had one, 
                        # but for now we'll append to reason or just log it.
                    )
                    structured_log(logger, logging.WARNING, "notification_failure_company", channel="email", target=email, error_message=error_msg)
                    # Proceed to fallback
                    await AdminRepo.create_history_entry(
                        db, key_id=uuid.UUID(key_id), new_status="ACTIVE",
                        reason="EMAIL_FALLBACK_SYSTEM"
                    )

            # 3. System Fallback
            res = await email_service.send_license_email(email, key_data, app_name, sender_name=sender_name)
            
            if res.get("status") == "success":
                await AdminRepo.create_history_entry(
                    db, key_id=uuid.UUID(key_id), new_status="ACTIVE",
                    reason="EMAIL_SENT_SYSTEM"
                )
                structured_log(logger, logging.INFO, "notification_completed", channel="email", target=email, provider="system")
            else:
                error_msg = res.get("reason", "Unknown API error")
                await AdminRepo.create_history_entry(
                    db, key_id=uuid.UUID(key_id), new_status="ACTIVE",
                    reason="EMAIL_FAILED_SYSTEM"
                )
                structured_log(logger, logging.ERROR, "notification_failure_system", channel="email", target=email, error_message=error_msg)
                raise Exception(f"Email failure: {error_msg}")

    @staticmethod
    async def _send_whatsapp_safe(phone: str, key_data: Dict[str, Any], app_name: str, sender_channel: str = None):
        structured_log(logger, logging.INFO, "notification_initiated", channel="whatsapp", target=phone)
        
        result = await whatsapp_service.send_license_whatsapp(phone, key_data, app_name, sender_channel=sender_channel)
        
        if result.get("status") == "failed":
            error_msg = result.get("message", "Unknown API error")
            structured_log(logger, logging.ERROR, "notification_failure", channel="whatsapp", target=phone, error_message=error_msg)
            raise Exception(f"WhatsApp failure: {error_msg}")
            
        structured_log(logger, logging.INFO, "notification_completed", channel="whatsapp", target=phone, result=result)
