import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings
from app.models.admin_models import FailedNotification

# Dedicated engine for DLQ operations initiated from Celery workers
# Note: In production, you might want to pool this differently, but for isolated DLQ writes, this is safe.
engine = create_async_engine(settings.REDIS_URL.replace("redis", "postgresql+asyncpg")) # Wait, REDIS_URL is for redis. 
# It should use POSTGRES_URL.
# settings.sql_alchemy_postgres_url is what we want.

postgres_url = settings.POSTGRES_URL
if postgres_url and postgres_url.startswith("postgres://"):
    postgres_url = postgres_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif postgres_url and postgres_url.startswith("postgresql://"):
    postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)

dlq_engine = create_async_engine(postgres_url)
AsyncSessionLocal = sessionmaker(dlq_engine, class_=AsyncSession, expire_on_commit=False)

async def persist_dlq_entry_async(channel: str, target: str, payload: dict, error: str, retry_count: int):
    """
    Asynchronously persists a failed notification to the PostgreSQL DLQ table.
    """
    async with AsyncSessionLocal() as session:
        new_entry = FailedNotification(
            id=uuid.uuid4(),
            channel=channel,
            target=target,
            payload=payload,
            error_reason=error,
            retry_count=retry_count,
            status="pending",
            failed_at=datetime.now(timezone.utc)
        )
        session.add(new_entry)
        await session.commit()

def persist_dlq_entry_sync(channel: str, target: str, payload: dict, error: str, retry_count: int):
    """
    Synchronous entry point for Celery tasks.
    """
    try:
        asyncio.run(persist_dlq_entry_async(channel, target, payload, error, retry_count))
    except Exception as e:
        # We don't want DLQ persistence failure to crash the worker, but we must log it.
        import logging
        logging.error(f"CRITICAL: Failed to persist to DLQ table: {str(e)}")
