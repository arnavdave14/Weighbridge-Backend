from celery import Celery
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
