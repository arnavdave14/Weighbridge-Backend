import asyncio
import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from app.database.sqlite import local_session
from app.database.postgres import remote_session
from app.models.models import Receipt, ReceiptImage, SyncLog, Machine, SyncQueue
from app.repositories.receipt_repo import ReceiptRepository
from app.repositories.machine_repo import MachineRepository
from app.repositories.sync_repo import SyncRepository
from app.services.image_upload_service import upload_image_to_cloud
from app.config.settings import settings

logger = logging.getLogger(__name__)
WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"

async def process_sync_queue():
    """
    Main loop to process pending sync tasks from SQLite to PostgreSQL.
    Lifecycle: PENDING -> PROCESSING -> DONE / FAILED / DEAD.
    """
    async with local_session() as db:
        # 1. Atomically acquire a batch of tasks
        tasks = await SyncRepository.acquire_tasks(
            db, 
            worker_id=WORKER_ID,
            limit=settings.SYNC_BATCH_SIZE, 
            max_retries=settings.MAX_SYNC_RETRIES
        )
        
        if not tasks:
            return

        # Tasks are already marked as PROCESSING by acquire_tasks()
        print(f"[SyncWorker] Found {len(tasks)} tasks")
        logger.info(f"[SyncWorker][{WORKER_ID}] Claimed {len(tasks)} tasks.")

        for task in tasks:
            # CAPTURE ATTRIBUTES LOCALLY to avoid "expired object" errors after rollback
            t_id = task.id
            t_table = task.table_name
            t_record_id = task.record_id
            t_retries = task.retry_count
            
            try:
                print(f"[SyncWorker] Processing {t_table}:{t_record_id}")
                
                success = False
                if t_table == "receipts":
                    success = await _sync_receipt(db, t_record_id)
                elif t_table == "machines":
                    success = await _sync_machine(db, t_record_id)
                
                if success:
                    # ATOMIC UPDATE FOR SUCCESS
                    await db.execute(
                        update(SyncQueue)
                        .where(SyncQueue.id == t_id)
                        .values(
                            status="DONE", 
                            worker_id=None, 
                            last_attempt=datetime.now(timezone.utc),
                            last_error=None
                        )
                    )
                    await db.commit()
                    print(f"[SyncWorker] SUCCESS: {t_table}:{t_record_id}")
                    logger.info(f"[SyncWorker][OK] {t_table}:{t_record_id}")
                else:
                    raise Exception("Sync operation failed (returned False)")

            except Exception as e:
                # CRITICAL: Clear failed transaction state immediately
                await db.rollback()
                
                new_retries = t_retries + 1
                new_status = "DEAD" if new_retries >= settings.MAX_SYNC_RETRIES else "FAILED"
                
                # ATOMIC UPDATE FOR FAILURE
                await db.execute(
                    update(SyncQueue)
                    .where(SyncQueue.id == t_id)
                    .values(
                        status=new_status,
                        retry_count=new_retries,
                        last_error=str(e),
                        worker_id=None,
                        last_attempt=datetime.now(timezone.utc)
                    )
                )
                await db.commit()
                
                print(f"[SyncWorker] {new_status}: {t_table}:{t_record_id} -> {e}")
                logger.error(f"[SyncWorker][ERR] {t_table}:{t_record_id} - {e}")

async def _sync_receipt(local_db: AsyncSession, receipt_id: int) -> bool:
    """Orchestrates single receipt sync: Images -> Metadata (Always UPSERT)."""
    # Use selectinload to avoid "greenlet_spawn has not been called" lazy-loading error
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    stmt = select(Receipt).where(Receipt.id == receipt_id).options(selectinload(Receipt.images))
    result = await local_db.execute(stmt)
    receipt = result.scalar_one_or_none()
    
    if not receipt:
        return True # Stale queue entry

    # Increment sync attempts on the source record (ONLY in worker)
    receipt.sync_attempts += 1
    
    # Resilient image sync
    collected_urls = list(receipt.image_urls or [])
    updated_images = False
    for img in receipt.images:
        if not img.is_uploaded and img.image_data:
            try:
                fname = f"RST_{receipt.local_id}_img{img.position}.jpg"
                url = await upload_image_to_cloud(img.image_data, fname)
                if url:
                    img.image_url = url
                    img.is_uploaded = True
                    img.image_data = None 
                    collected_urls.append(url)
                    updated_images = True
            except Exception as e:
                print(f"[SyncWorker] Image upload failed for receipt {receipt_id}: {e}")
                logger.warning(f"[SyncWorker][IMG] Failed upload: {e}")
    
    if updated_images:
        receipt.image_urls = collected_urls

    if not remote_session:
        print("[SyncWorker] Remote database session not configured.")
        return False
        
    try:
        print(f"[SyncWorker] Syncing receipt {receipt.local_id} to PostgreSQL...")
        print(f"[SyncWorker] Connecting to PostgreSQL...")
        async with remote_session() as remote_db:
            # Always UPSERT (ON CONFLICT DO UPDATE)
            stmt = pg_insert(Receipt).values(
                machine_id=receipt.machine_id,
                local_id=receipt.local_id,
                date_time=receipt.date_time,
                gross_weight=receipt.gross_weight,
                tare_weight=receipt.tare_weight,
                rate=receipt.rate,
                custom_data=receipt.custom_data,
                image_urls=receipt.image_urls,
                share_token=receipt.share_token,
                whatsapp_status=receipt.whatsapp_status,
                created_at=receipt.created_at,
                updated_at=receipt.updated_at
            ).on_conflict_do_update(
                constraint="uq_machine_receipt",
                set_={
                    "gross_weight": receipt.gross_weight,
                    "tare_weight": receipt.tare_weight,
                    "rate": receipt.rate,
                    "custom_data": receipt.custom_data,
                    "image_urls": receipt.image_urls,
                    "whatsapp_status": receipt.whatsapp_status,
                    "updated_at": receipt.updated_at
                }
            )
            await remote_db.execute(stmt)
            await remote_db.commit()
            print(f"[SyncWorker] PostgreSQL sync completed")

        # Success: Mark as synced in SQLite
        receipt.is_synced = True
        receipt.synced_at = datetime.now(timezone.utc)
        return True
    except Exception as e:
        logger.error(f"[SyncWorker][PG_PUSH] Receipt {receipt_id} failed: {e}")
        return False

async def _sync_machine(local_db: AsyncSession, machine_id: int) -> bool:
    """Orchestrates machine settings sync to PostgreSQL (Always UPSERT).

    GAP-2 FIX: key_id is now included in both the INSERT values and the
    ON CONFLICT UPDATE set, so tenant linkage is never lost during sync.

    GAP-7 FIX: is_synced, last_sync_at, sync_attempts, updated_at are
    included so PostgreSQL mirrors real sync state from SQLite.
    """
    machine = await local_db.get(Machine, machine_id)
    if not machine or not remote_session:
        return True if not machine else False

    # Increment sync attempts on the source record (ONLY in worker)
    machine.sync_attempts += 1

    try:
        print(f"[SyncWorker] Syncing machine {machine.machine_id} (key_id={machine.key_id}) to PostgreSQL...")
        async with remote_session() as remote_db:
            stmt = pg_insert(Machine).values(
                machine_id=machine.machine_id,
                name=machine.name,
                location=machine.location,
                settings=machine.settings,
                is_active=machine.is_active,
                # GAP-2: persist tenant linkage token
                key_id=machine.key_id,
                # GAP-7: persist sync state accurately
                is_synced=machine.is_synced,
                sync_attempts=machine.sync_attempts,
                last_sync_at=machine.last_sync_at,
                created_at=machine.created_at,
                updated_at=machine.updated_at,
            ).on_conflict_do_update(
                index_elements=["machine_id"],
                set_={
                    "name": machine.name,
                    "location": machine.location,
                    "settings": machine.settings,
                    "is_active": machine.is_active,
                    # GAP-2: always propagate key_id (never overwrite with NULL)
                    "key_id": machine.key_id,
                    # GAP-7: keep sync counters current
                    "is_synced": machine.is_synced,
                    "sync_attempts": machine.sync_attempts,
                    "last_sync_at": machine.last_sync_at,
                    "updated_at": machine.updated_at,
                }
            )
            await remote_db.execute(stmt)
            await remote_db.commit()
            print(f"[SyncWorker] PostgreSQL machine sync completed for {machine.machine_id}")

        machine.is_synced = True
        return True
    except Exception as e:
        logger.error(f"[SyncWorker][PG_PUSH] Machine {machine_id} failed: {e}")
        return False

async def run_sync_worker_loop():
    """Main entry point for independent background sync worker."""
    if settings.DB_MODE not in ["dual", "postgres"]:
        logger.info(f"Sync Worker disabled (DB_MODE={settings.DB_MODE}).")
        return

    if not remote_session:
        logger.warning("Sync Worker started but REMOTE_DATABASE_URL/POSTGRES_URL is not configured. Sync will be skipped.")
        
    print("[SyncWorker] Worker started...")
    logger.info(f"Starting Independent Sync Worker [{WORKER_ID}] - Batch: {settings.SYNC_BATCH_SIZE}")
    while True:
        try:
            await process_sync_queue()
        except Exception as e:
            logger.error(f"[SyncWorker] Critical loop failure: {e}")
        # Reduced sleep for development/debugging
        await asyncio.sleep(settings.SYNC_INTERVAL_SECONDS if settings.ENVIRONMENT == "production" else 5)

if __name__ == "__main__":
    # Allows running as: python -m app.sync.sync_worker
    import asyncio
    print("[DEBUG] Starting single sync cycle...")
    asyncio.run(process_sync_queue())
    print("[DEBUG] Sync cycle completed.")
