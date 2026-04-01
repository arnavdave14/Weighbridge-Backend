from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, update
from app.models.models import SyncQueue, SyncLog
from typing import List, Optional
from datetime import datetime, timezone

class SyncRepository:
    @staticmethod
    async def add_task(db: AsyncSession, table_name: str, record_id: int, operation: str = "INSERT"):
        new_task = SyncQueue(
            table_name=table_name,
            record_id=record_id,
            operation=operation,
            status="PENDING"
        )
        db.add(new_task)
        return new_task

    @staticmethod
    async def acquire_tasks(
        db: AsyncSession, 
        worker_id: str,
        limit: int, 
        max_retries: int
    ) -> List[SyncQueue]:
        """
        Atomically claims a batch of tasks for a worker using RETURNING.
        Ensures absolute safety in multi-worker environments.
        """
        # 1. Create a subquery of IDs to claim
        subquery = (
            select(SyncQueue.id)
            .where(
                and_(
                    SyncQueue.status.in_(["PENDING", "FAILED"]),
                    SyncQueue.retry_count < max_retries,
                    SyncQueue.worker_id == None
                )
            )
            .order_by(SyncQueue.created_at.asc())
            .limit(limit)
            .scalar_subquery()
        )

        # 2. Atomic Update + Returning
        stmt = (
            update(SyncQueue)
            .where(SyncQueue.id.in_(subquery))
            .values(
                status="PROCESSING",
                worker_id=worker_id,
                last_attempt=datetime.now(timezone.utc)
            )
            .returning(SyncQueue)
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: int) -> Optional[SyncQueue]:
        return await db.get(SyncQueue, task_id)

    @staticmethod
    async def create_log(db: AsyncSession, log: SyncLog) -> SyncLog:
        db.add(log)
        return log
