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

@celery_app.task
def celery_heartbeat():
    """
    Simple task pulsed by Celery Beat to verify worker health.
    Updates a timestamp in Redis.
    """
    from datetime import datetime, timezone
    import redis
    from app.config.settings import settings
    
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.set("celery_last_heartbeat", datetime.now(timezone.utc).isoformat())
        return "beat"
    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")
        return "error"


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
                    await AdminRepo.create_history_entry(
                        db,
                        key_id=uuid.UUID(key_id),
                        new_status="ACTIVE", # Current status remains
                        reason="WA_SENT"
                    )
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
                    await AdminRepo.create_history_entry(
                        db,
                        key_id=uuid.UUID(key_id),
                        new_status="ACTIVE",
                        reason="WA_FAILED"
                    )
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
                    await AdminRepo.create_history_entry(
                        db,
                        key_id=uuid.UUID(key_id),
                        new_status="ACTIVE",
                        reason="EMAIL_SENT"
                    )
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
                    await AdminRepo.create_history_entry(
                        db,
                        key_id=uuid.UUID(key_id),
                        new_status="ACTIVE",
                        reason="EMAIL_FAILED"
                    )
            asyncio.run(update_db_fail())
        raise

@celery_app.task(bind=True)
def check_expiring_licenses(self):
    """
    Scheduled background task to scan for expiring licenses 
    and send alerts at 7, 3, and 1 day intervals.
    """
    from datetime import datetime, timezone, timedelta
    from app.repositories.admin_repo import AdminRepo
    from app.services.notification_service import NotificationService
    
    async def run_scan():
        async with remote_session() as db:
            keys = await AdminRepo.get_expiring_keys(db)
            now = datetime.now(timezone.utc)
            
            for key in keys:
                # 1. Calculate time remaining
                remaining = key.expiry_date - now
                days = remaining.days
                
                # 2. Check if we are in a notification window (7, 3, 1 days)
                # And ensure we haven't already notified today (idempotency)
                target_windows = [7, 3, 1]
                
                if days in target_windows:
                    last_notif = key.last_notification_sent
                    if last_notif:
                        # If we notified less than 20 hours ago, skip
                        if (now - last_notif).total_seconds() < (20 * 3600):
                            continue

                    # 3. Trigger Notification
                    app_name = "Weighbridge Software"
                    app_id_str = "unknown"
                    if key.app_id:
                        app = await AdminRepo.get_app_by_uuid(db, key.app_id)
                        if app: 
                            app_name = app.app_name
                            app_id_str = app.app_id

                    key_data = {
                        "id": str(key.id),
                        "company_name": key.company_name,
                        "email": key.email,
                        "whatsapp_number": key.whatsapp_number,
                        "expiry_date": key.expiry_date.strftime("%Y-%m-%d"),
                        "app_id_str": app_id_str
                    }
                    
                    prev_status = key.status
                    # Determine new status
                    if key.status == "ACTIVE":
                        key.status = "EXPIRING_SOON"
                    
                    key.last_notification_sent = now
                    db.add(key)
                    
                    # Log to history
                    await AdminRepo.create_history_entry(
                        db,
                        key_id=key.id,
                        prev_status=prev_status,
                        new_status=key.status,
                        reason="AUTO_STATUS_TRANSITION_CELERY"
                    )
                    
                    # Create system notification in admin panel
                    await AdminRepo.create_notification(
                        db,
                        message=f"License for '{key.company_name}' expires in {days} days ({key_data['expiry_date']}). Automated alert dispatched.",
                        notif_type="warning",
                        notification_type="license_expiry_alert",
                        app_id=key.app_id,
                        activation_key_id=key.id
                    )
                    
                    # Fire Celery sub-tasks (to keep this loop fast & isolated from delivery failures)
                    send_whatsapp_notification_task.delay(key_data, app_name)
                    send_email_notification_task.delay(key_data, app_name)
                    
                # 4. Handle auto-expiry if days < 0
                elif days < 0 and key.status != "EXPIRED":
                    prev_status = key.status
                    key.status = "EXPIRED"
                    key.expired_at = now
                    db.add(key)
                    
                    # Log to history
                    await AdminRepo.create_history_entry(
                        db,
                        key_id=key.id,
                        prev_status=prev_status,
                        new_status="EXPIRED",
                        reason="AUTO_EXPIRY_CELERY"
                    )
                    await AdminRepo.create_notification(
                        db,
                        message=f"License for '{key.company_name}' has expired. All devices blocked.",
                        notif_type="error",
                        notification_type="license_expired",
                        app_id=key.app_id,
                        activation_key_id=key.id
                    )

            await db.commit()

    import asyncio
    asyncio.run(run_scan())
    return {"status": "completed"}

