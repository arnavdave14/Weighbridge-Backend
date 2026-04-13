from celery import Celery
from celery.schedules import crontab
from app.config.settings import settings

celery_app = Celery(
    "weighbridge_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notification_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5 minutes maximum runtime
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "check-license-expiry-hourly": {
        "task": "app.tasks.notification_tasks.check_expiring_licenses",
        "schedule": crontab(minute=0), # Every hour at minute 0
    },
    "celery-heartbeat-every-minute": {
        "task": "app.tasks.notification_tasks.celery_heartbeat",
        "schedule": crontab(minute="*"), # Every minute
    },
}

