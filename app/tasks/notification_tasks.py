import logging
import uuid
from celery.exceptions import MaxRetriesExceededError
from app.celery_app import celery_app
from app.services.notification_service import NotificationService
from app.api.admin_deps import get_remote_db
from app.database.postgres import remote_session
from app.repositories.admin_repo import AdminRepo
from app.core.metrics import metrics
from app.core.log_utils import structured_log
from app.tasks.dlq_utils import persist_dlq_entry_sync

logger = logging.getLogger("celery_tasks")

import smtplib
import requests

def is_retryable_exception(exc: Exception) -> bool:
    """
    Categorizes exceptions to avoid retrying permanent failures.
    """
    # SMTP Errors
    if isinstance(exc, (smtplib.SMTPConnectError, smtplib.SMTPHeloError, smtplib.SMTPServerDisconnected)):
        return True # Network/Connection issue
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return False # Invalid email
    if isinstance(exc, smtplib.SMTPDataError):
        # 5xx in data often means spam block or invalid content
        return str(exc).startswith('5') == False 

    # HTTP / WhatsApp Errors
    if isinstance(exc, requests.exceptions.RequestException):
        if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
            return True
        # If we got a 400 Bad Request or 401 Unauthorized, don't retry
        if exc.response is not None:
            if exc.response.status_code in [400, 401, 403, 404]:
                return False
            if exc.response.status_code >= 500:
                return True
    
    # Rate Limits
    if "Rate limit exceeded" in str(exc):
        return True # Retry later when bucket refills
        
    # Default to retry for safety unless explicitly known non-retryable
    return True

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_whatsapp_notification_task(self, key_data: dict, app_name: str):
    """
    Dedicated parallel task for WhatsApp delivery.
    """
    key_id = key_data.get("id")
    target = str(key_data.get("whatsapp_number", "unknown"))
    structured_log(logger, logging.INFO, "whatsapp_task_started", task_id=self.request.id, key_id=key_id, target=target)
    
    try:
        status = NotificationService.send_whatsapp_license_sync(key_data, app_name)
        
        if key_id and status == "sent":
            import asyncio
            async def update_db():
                async with remote_session() as db:
                    await AdminRepo.update_key_notification_status(db, uuid.UUID(key_id), "whatsapp", "sent")
            asyncio.run(update_db())
            
        return {"status": status}
        
    except Exception as e:
        retryable = is_retryable_exception(e)
        structured_log(logger, logging.WARNING, "whatsapp_task_error", 
                       task_id=self.request.id, attempt=self.request.retries + 1, 
                       retryable=retryable, error=str(e), target=target)
        
        if retryable:
            try:
                raise self.retry(exc=e)
            except MaxRetriesExceededError:
                pass # Fall through to DLQ
        
        # DLQ Event (Permanent failure or Retries Exhausted)
        persist_dlq_entry_sync(
            channel="whatsapp",
            target=target,
            payload=key_data,
            error=str(e),
            retry_count=self.request.retries,
            notification_type="license_generation",
            can_retry=retryable,
            message_content=key_data.get("message")
        )
        metrics.NOTIFICATION_DLQ_TOTAL.labels(channel="whatsapp").inc()
        
        if key_id:
            import asyncio
            async def update_db_fail():
                async with remote_session() as db:
                    await AdminRepo.update_key_notification_status(db, uuid.UUID(key_id), "whatsapp", "failed")
            asyncio.run(update_db_fail())
        raise

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_email_notification_task(self, key_data: dict, app_name: str):
    """
    Dedicated parallel task for Email delivery.
    """
    key_id = key_data.get("id")
    target = str(key_data.get("email", "unknown"))
    structured_log(logger, logging.INFO, "email_task_started", task_id=self.request.id, key_id=key_id, target=target)
    
    try:
        status = NotificationService.send_email_license_sync(key_data, app_name)
        
        if key_id and status == "sent":
            import asyncio
            async def update_db():
                async with remote_session() as db:
                    await AdminRepo.update_key_notification_status(db, uuid.UUID(key_id), "email", "sent")
            asyncio.run(update_db())
            
        return {"status": status}
        
    except Exception as e:
        retryable = is_retryable_exception(e)
        structured_log(logger, logging.WARNING, "email_task_error", 
                       task_id=self.request.id, attempt=self.request.retries + 1, 
                       retryable=retryable, error=str(e), target=target)
        
        if retryable:
            try:
                raise self.retry(exc=e)
            except MaxRetriesExceededError:
                pass # Fall through to DLQ

        # DLQ Event
        persist_dlq_entry_sync(
            channel="email",
            target=target,
            payload=key_data,
            error=str(e),
            retry_count=self.request.retries,
            notification_type="license_generation",
            can_retry=retryable,
            message_content=key_data.get("message")
        )
        metrics.NOTIFICATION_DLQ_TOTAL.labels(channel="email").inc()

        if key_id:
            import asyncio
            async def update_db_fail():
                async with remote_session() as db:
                    await AdminRepo.update_key_notification_status(db, uuid.UUID(key_id), "email", "failed")
            asyncio.run(update_db_fail())
        raise
