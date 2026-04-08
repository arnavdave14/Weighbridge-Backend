import logging
import re
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from app.services import email_service, whatsapp_service
from app.core.metrics import metrics
from app.core.log_utils import structured_log
from app.core.rate_limiter import rate_limiter
from app.config.settings import settings

logger = logging.getLogger("notification_service")

class NotificationService:
    @staticmethod
    def validate_contact_info(email: str | None, phone: str | None) -> Tuple[bool, bool]:
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
        """
        Asynchronous orchestrator for dispatching notifications.
        Gracefully handles failures per channel and logs structurally.
        """
        email = key_data.get("email")
        phone = key_data.get("whatsapp_number")
        
        is_valid_email, is_valid_phone = NotificationService.validate_contact_info(email, phone)
        
        tasks = []
        if is_valid_email:
            tasks.append(NotificationService._send_email_safe(email, key_data, app_name))
            
        if is_valid_phone:
            tasks.append(NotificationService._send_whatsapp_safe(phone, key_data, app_name))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            failed_channels = {}
            for res in results:
                if isinstance(res, Exception):
                    # We can pack the exception into the failed_channels dict
                    # But we'd need to know which channel the exception came from.
                    pass
            
            # Since tracking exceptions perfectly via gather is tricky, 
            # I will refactor the safe handlers to raise if they fail, or return their channel.

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
    async def _notify_license_generation_async_orchestrated(
        key_data: Dict[str, Any],
        app_name: str,
        skip_channels: list = None
    ) -> Dict[str, Any]:
        email = key_data.get("email")
        phone = key_data.get("whatsapp_number")
        
        skip = skip_channels or []
        is_valid_email, is_valid_phone = NotificationService.validate_contact_info(email, phone)
        
        result_state = {
            "success": [],
            "failed": {}
        }

        # Sequential await here is safer for exact error tracing than gather
        # and performance is acceptable for background workers processing singular jobs.
        
        # 1. Check Rate Limit (Tenant-scoped)
        company_name = key_data.get("company_name", "unknown")
        is_allowed, remaining = rate_limiter.check(
            f"notify:{company_name}", 
            settings.NOTIFICATION_RATE_LIMIT_PER_MINUTE
        )
        
        if not is_allowed:
            error_msg = f"Rate limit exceeded for tenant: {company_name}"
            structured_log(logger, logging.WARNING, "rate_limit_exceeded", channel="all", target=company_name, error_message=error_msg)
            result_state["failed"]["rate_limit"] = error_msg
            return result_state

        if is_valid_email and "email" not in skip:
            start_time = time.time()
            try:
                await NotificationService._send_email_safe(email, key_data, app_name)
                result_state["success"].append("email")
                metrics.NOTIFICATIONS_TOTAL.labels(channel="email", status="sent").inc()
            except Exception as e:
                result_state["failed"]["email"] = str(e)
                metrics.NOTIFICATIONS_TOTAL.labels(channel="email", status="failed").inc()
            finally:
                metrics.NOTIFICATION_LATENCY_SECONDS.labels(channel="email").observe(time.time() - start_time)
                
        if is_valid_phone and "whatsapp" not in skip:
            start_time = time.time()
            try:
                await NotificationService._send_whatsapp_safe(phone, key_data, app_name)
                result_state["success"].append("whatsapp")
                metrics.NOTIFICATIONS_TOTAL.labels(channel="whatsapp", status="sent").inc()
            except Exception as e:
                result_state["failed"]["whatsapp"] = str(e)
                metrics.NOTIFICATIONS_TOTAL.labels(channel="whatsapp", status="failed").inc()
            finally:
                metrics.NOTIFICATION_LATENCY_SECONDS.labels(channel="whatsapp").observe(time.time() - start_time)
                
        return result_state
            
    @staticmethod
    async def _send_email_safe(email: str, key_data: Dict[str, Any], app_name: str):
        structured_log(logger, logging.INFO, "notification_initiated", channel="email", target=email)
        
        result = await email_service.send_license_email(email, key_data, app_name)
        
        if result.get("status") == "failed":
            error_msg = result.get("reason", "Unknown API error")
            structured_log(logger, logging.ERROR, "notification_failure", channel="email", target=email, error_message=error_msg)
            raise Exception(f"Email failure: {error_msg}")
            
        structured_log(logger, logging.INFO, "notification_completed", channel="email", target=email, result=result)

    @staticmethod
    async def _send_whatsapp_safe(phone: str, key_data: Dict[str, Any], app_name: str):
        structured_log(logger, logging.INFO, "notification_initiated", channel="whatsapp", target=phone)
        
        result = await whatsapp_service.send_license_whatsapp(phone, key_data, app_name)
        
        if result.get("status") == "failed":
            error_msg = result.get("message", "Unknown API error")
            structured_log(logger, logging.ERROR, "notification_failure", channel="whatsapp", target=phone, error_message=error_msg)
            raise Exception(f"WhatsApp failure: {error_msg}")
            
        structured_log(logger, logging.INFO, "notification_completed", channel="whatsapp", target=phone, result=result)
