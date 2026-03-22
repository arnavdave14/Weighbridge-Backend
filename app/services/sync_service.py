from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from typing import List, Dict, Any, Tuple
from app.models.models import Receipt, Machine, SyncLog
from app.schemas.schemas import ReceiptCreate, ReceiptSync, SyncResponse
from app.utils.token_util import generate_share_token

class SyncService:
    @staticmethod
    async def process_batch_sync(db: AsyncSession, sync_data: ReceiptSync) -> Tuple[SyncResponse, List[Receipt]]:
        synced_count = 0
        failed_count = 0
        new_receipts = []
        errors = []

        # 1. Ensure machine exists or create it
        result = await db.execute(select(Machine).where(Machine.machine_id == sync_data.machine_id))
        machine = result.scalar_one_or_none()
        if not machine:
            machine = Machine(machine_id=sync_data.machine_id, name=f"Machine {sync_data.machine_id}")
            db.add(machine)
            await db.flush()

        # 2. Process each receipt
        for receipt_data in sync_data.receipts:
            try:
                # Prepare data for insertion
                # We use PostgreSQL's ON CONFLICT DO NOTHING to avoid duplicates based on (machine_id, local_id)
                new_receipt_stmt = insert(Receipt).values(
                    machine_id=sync_data.machine_id,
                    local_id=receipt_data.local_id,
                    date_time=receipt_data.date_time,
                    gross_weight=receipt_data.gross_weight,
                    tare_weight=receipt_data.tare_weight,
                    rate=receipt_data.rate,
                    custom_data=receipt_data.custom_data,
                    share_token=generate_share_token()
                ).on_conflict_do_nothing(
                    index_elements=["machine_id", "local_id"]
                ).returning(Receipt)
                
                res = await db.execute(new_receipt_stmt)
                new_record = res.scalar_one_or_none()
                
                if new_record:
                    synced_count += 1
                    new_receipts.append(new_record)
                else:
                    # Duplicate (local_id already exists for this machine)
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Receipt {receipt_data.local_id}: {str(e)}")

        # 3. Update machine last sync
        machine.last_sync_at = datetime.now()
        
        # 4. Log the sync operation
        sync_log = SyncLog(
            machine_id=sync_data.machine_id,
            operation="batch_sync",
            status="success" if not errors else "partial_success",
            synced_count=synced_count,
            failed_count=failed_count,
            error_message="; ".join(errors) if errors else None
        )
        db.add(sync_log)
        
        await db.commit()
        return SyncResponse(synced=synced_count, failed=failed_count, errors=errors if errors else None), new_receipts
