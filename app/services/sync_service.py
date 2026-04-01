import asyncio
import base64
import logging
import uuid
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db_manager import get_db
from app.database.sqlite import local_session
from app.models.models import Receipt, ReceiptImage, SyncLog, Machine, SyncQueue
from app.schemas.schemas import ReceiptSync, SyncResponse
from app.services.image_upload_service import upload_image_to_cloud
from app.repositories.receipt_repo import ReceiptRepository
from app.repositories.machine_repo import MachineRepository
from app.repositories.sync_repo import SyncRepository

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
BATCH_SIZE = 25
WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"

class SyncService:
    @staticmethod
    async def enqueue_task(db: AsyncSession, table_name: str, record_id: int, operation: str = "INSERT"):
        """Add a new task to the sync queue via SyncRepository."""
        await SyncRepository.add_task(db, table_name, record_id, operation)
        logger.info(f"[SyncQueue] Enqueued {table_name} {record_id} for {operation}")

    @staticmethod
    async def process_batch_sync(db: AsyncSession, sync_data: ReceiptSync) -> SyncResponse:
        """
        STRICT WRITE FLOW:
        1. Save data ONLY in SQLite first.
        2. Insert a record into sync_queue (INSERT or UPDATE).
        3. NO PostgreSQL dependency in this flow.
        """
        synced_count = 0
        failed_count = 0
        errors = []

        # 1. Machine Check/Update (Local SQLite)
        machine = await MachineRepository.get_by_machine_id(db, sync_data.machine_id)

        if not machine:
            machine = Machine(
                machine_id=sync_data.machine_id,
                settings=sync_data.settings or {},
                last_sync_at=datetime.now(timezone.utc)
            )
            await MachineRepository.create(db, machine)
            await db.flush()
            # Enqueue machine sync (INSERT)
            await SyncService.enqueue_task(db, "machines", machine.id, "INSERT")
        else:
            if sync_data.settings:
                machine.settings = sync_data.settings
            machine.last_sync_at = datetime.now(timezone.utc)
            # Enqueue machine sync (UPDATE)
            await SyncService.enqueue_task(db, "machines", machine.id, "UPDATE")

        # 2. Process Receipts
        for r_schema in sync_data.receipts:
            try:
                # Duplicate check (Local SQLite)
                existing = await ReceiptRepository.get_by_machine_and_local_id(
                    db, sync_data.machine_id, r_schema.local_id
                )
                if existing:
                    synced_count += 1
                    continue

                new_receipt = Receipt(
                    machine_id=sync_data.machine_id,
                    local_id=r_schema.local_id,
                    date_time=r_schema.date_time,
                    gross_weight=r_schema.gross_weight,
                    tare_weight=r_schema.tare_weight,
                    rate=r_schema.rate,
                    custom_data=r_schema.custom_data,
                    image_urls=[],
                    share_token=str(uuid.uuid4())[:12],
                    whatsapp_status="pending",
                    is_synced=False
                )
                await ReceiptRepository.create(db, new_receipt)
                await db.flush()

                # Process Images (Local SQLite)
                images_base64 = r_schema.images_base64 or []
                for position, b64_str in enumerate(images_base64):
                    if "," in b64_str:
                        b64_str = b64_str.split(",", 1)[1]
                    image_bytes = base64.b64decode(b64_str)
                    receipt_image = ReceiptImage(
                        receipt_id=new_receipt.id,
                        position=position,
                        image_data=image_bytes,
                        is_uploaded=False
                    )
                    db.add(receipt_image)

                # 3. ENQUEUE SYNC TASK (INSERT)
                await SyncService.enqueue_task(db, "receipts", new_receipt.id, "INSERT")
                synced_count += 1

            except Exception as e:
                failed_count += 1
                errors.append(f"Receipt {r_schema.local_id}: {str(e)}")
                logger.error(f"[Sync] Failed to save receipt {r_schema.local_id}: {e}")

        await db.commit()
        return SyncResponse(synced=synced_count, failed=failed_count, errors=errors)



