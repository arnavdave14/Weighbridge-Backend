import logging
from celery.exceptions import MaxRetriesExceededError
from app.celery_app import celery_app
from app.services.notification_service import NotificationService
from app.core.metrics import metrics
from app.core.log_utils import structured_log
from app.tasks.dlq_utils import persist_dlq_entry_sync

logger = logging.getLogger("celery_tasks")

@celery_app.task(bind=True, max_retries=5, retry_backoff=2, retry_backoff_max=32)
def send_notification_task(self, key_data: dict, app_name: str, skip_channels: list = None):
    """
    Celery task that delegates to the NotificationService orchestrator.
    Handles Celery-native retries.
    State is passed across retries via skip_channels to prevent duplicate messages.
    """
    skip_channels = skip_channels or []
    
    structured_log(logger, logging.INFO, "task_execution_started", task_id=self.request.id, skip_channels=skip_channels)
    
    # Run the synchronous wrapper which handles the internal asyncio event loop
    result_state = NotificationService.notify_license_generation_sync(
        key_data=key_data, 
        app_name=app_name, 
        skip_channels=skip_channels
    )
    
    successes = result_state.get("success", [])
    failures = result_state.get("failed", {})
    
    # Update skip_channels with any newly successful channels
    new_skip_channels = list(set(skip_channels + successes))
    
    if failures:
        error_msgs = ", ".join([f"{ch}: {err}" for ch, err in failures.items()])
        structured_log(logger, logging.WARNING, "task_partial_failure", task_id=self.request.id, attempt=self.request.retries + 1, error_message=error_msgs)
        
        try:
            # Increment retry metric
            for ch in failures.keys():
                metrics.NOTIFICATION_RETRIES_TOTAL.labels(channel=ch).inc()

            # Trigger Celery native exponential backoff retry.
            raise self.retry(
                exc=Exception(f"Failed channels: {error_msgs}"),
                kwargs={
                    "key_data": key_data,
                    "app_name": app_name,
                    "skip_channels": new_skip_channels
                }
            )
        except MaxRetriesExceededError:
            # Persistent DLQ Injection
            structured_log(logger, logging.CRITICAL, "dlq_event_persistent", task_id=self.request.id, target_data=key_data, failed_channels=failures, retry_count=self.request.retries, status="permanently_failed")
            
            # Record each failed channel in the DB DLQ table
            for channel, error in failures.items():
                target = key_data.get("email") if channel == "email" else key_data.get("whatsapp_number")
                persist_dlq_entry_sync(
                    channel=channel,
                    target=str(target),
                    payload=key_data,
                    error=error,
                    retry_count=self.request.retries
                )
                metrics.NOTIFICATION_DLQ_TOTAL.labels(channel=channel).inc()
            raise
        
    structured_log(logger, logging.INFO, "task_execution_completed", task_id=self.request.id)
    return result_state
