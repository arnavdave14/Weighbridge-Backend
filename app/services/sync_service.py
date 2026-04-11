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
from app.models.models import Receipt, ReceiptImage, Machine
from app.models.admin_models import ActivationKey
from app.schemas.schemas import ReceiptSync, SyncResponse
from app.services.image_upload_service import upload_image_to_cloud
from app.repositories.receipt_repo import ReceiptRepository
from app.repositories.machine_repo import MachineRepository
from app.repositories.admin_repo import AdminRepo
from app.repositories.sync_repo import SyncRepository
from app.core.validation_engine import ValidationEngine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.utils.crypto_util import generate_receipt_hash, GENESIS_HASH
from app.services.audit_service import AuditService

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
    async def process_batch_sync(
        db: AsyncSession,
        sync_data: ReceiptSync,
        activation_key: ActivationKey,
        schema_version: int
    ) -> SyncResponse:
        """
        APEX SYNC FLOW:
        1. Derive label config from activation_key (already resolved from PostgreSQL).
        2. Ensure Machine row exists in SQLite (upsert) — prevents FK violations.
        3. Validate each receipt unit (atomic validation per receipt).
        4. Perform transactional bulk-upsert for valid receipts.
        5. Return detailed audit (Synced, Duplicates, Field-wise error map).

        GAP-4 FIX: Schema lookup previously used the SQLite `db` session, but
        `activation_key_schemas` is a PostgreSQL-only (AdminBase) table. Instead of
        making a cross-DB call, we use `activation_key.labels` which is already
        loaded from PostgreSQL by `verify_apex_identity`. This is simpler, faster,
        and architecturally correct.

        GAP-8 FIX: Machine row is auto-upserted before receipts are inserted to
        prevent FK violations for machines that have never synced their row yet.
        """
        synced_count = 0
        duplicate_count = 0
        failed_count = 0
        error_map = {}
        valid_receipt_objects = []

        # GAP-4 FIX: Use activation_key.labels (already from PostgreSQL)
        # No cross-DB AdminRepo call needed.
        labels_config = activation_key.labels or []
        logger.info(
            f"[Sync] machine={sync_data.machine_id} key={activation_key.id} "
            f"schema_version={schema_version} labels={len(labels_config)}"
        )

        # GAP-8 FIX: Ensure Machine row exists in SQLite before inserting receipts.
        # This prevents FK violations (Receipt.machine_id → machines.machine_id).
        existing_machine = await MachineRepository.get_by_machine_id(db, sync_data.machine_id)
        if not existing_machine:
            logger.info(f"[Sync] Auto-creating machine row for {sync_data.machine_id}")
            new_machine = Machine(
                machine_id=sync_data.machine_id,
                name=sync_data.machine_id,   # Default to machine_id; device updates later
                is_active=True,
                # Store key_id so PostgreSQL gets it via sync worker (GAP-2)
                key_id=activation_key.token,
            )
            await MachineRepository.create(db, new_machine)
            await db.flush()  # Make machine_id available for FK before receipt insert
            logger.info(f"[Sync] Machine auto-created: {sync_data.machine_id}")
        else:
            # Backfill key_id if missing (handles machines activated before this fix)
            if not existing_machine.key_id:
                existing_machine.key_id = activation_key.token
                logger.info(f"[Sync] Backfilled key_id for existing machine {sync_data.machine_id}")

        # --- [Phase 2] Fetch last hash for chaining ---
        last_receipt_stmt = select(Receipt).order_by(Receipt.id.desc()).limit(1)
        res = await db.execute(last_receipt_stmt)
        last_receipt = res.scalar_one_or_none()
        current_chain_hash = last_receipt.current_hash if last_receipt and last_receipt.current_hash else GENESIS_HASH
        # -----------------------------------------------

        # Process Receipts
        for r_schema in sync_data.receipts:
            try:
                # A. Idempotency Check (Duplicate check)
                existing = await ReceiptRepository.get_by_machine_and_local_id(
                    db, sync_data.machine_id, r_schema.local_id
                )
                if existing:
                    duplicate_count += 1
                    continue

                # B. Normalization
                normalized_data = ValidationEngine.normalize_custom_data(r_schema.custom_data, labels_config)

                # C. Atomic Validation
                dummy_receipt = {"custom_data": normalized_data}
                is_valid, field_errors = ValidationEngine.validate_receipt(dummy_receipt, labels_config)

                if not is_valid:
                    failed_count += 1
                    error_map[r_schema.local_id] = field_errors
                    continue

                # D. Preparation for Bulk Insert
                new_receipt = Receipt(
                    machine_id=sync_data.machine_id,
                    local_id=r_schema.local_id,
                    date_time=r_schema.date_time,
                    gross_weight=r_schema.gross_weight,
                    tare_weight=r_schema.tare_weight,
                    rate=r_schema.rate,
                    custom_data=normalized_data,
                    share_token=str(uuid.uuid4())[:12],
                    whatsapp_status="pending",
                    is_synced=False,
                    user_id=r_schema.user_id or None,
                    # Correction System (Phase 2 Refined)
                    corrected_from_id=r_schema.corrected_from_id,
                    correction_reason=r_schema.correction_reason,
                    hash_version=1
                )
                
                # --- [Phase 2] Generate Cryptographic Hash ---
                # We use a dict of the record fields for stable hashing
                receipt_dict = {
                    "machine_id": new_receipt.machine_id,
                    "local_id": new_receipt.local_id,
                    "date_time": str(new_receipt.date_time),
                    "gross_weight": str(new_receipt.gross_weight),
                    "tare_weight": str(new_receipt.tare_weight),
                    "rate": str(new_receipt.rate),
                    "custom_data": new_receipt.custom_data,
                    "user_id": new_receipt.user_id,
                    "is_deleted": False,
                    "corrected_from_id": new_receipt.corrected_from_id,
                    "correction_reason": new_receipt.correction_reason
                }
                new_receipt.previous_hash = current_chain_hash
                new_receipt.current_hash = generate_receipt_hash(
                    receipt_dict, current_chain_hash, version=new_receipt.hash_version
                )
                
                # Advance the chain for the next record in the batch
                current_chain_hash = new_receipt.current_hash
                # ---------------------------------------------

                valid_receipt_objects.append(new_receipt)

            except Exception as e:
                failed_count += 1
                error_map[r_schema.local_id] = {"internal_error": str(e)}
                logger.error(f"[Sync] Logic error for receipt {r_schema.local_id}: {e}")

        # Transactional Bulk Insert
        if valid_receipt_objects:
            try:
                db.add_all(valid_receipt_objects)
                await db.flush()
                
                # --- [Phase 2] Audit Log for Batch Creation ---
                # Identify the common user if consistent in batch, or SYSTEM
                batch_user_id = valid_receipt_objects[0].user_id if valid_receipt_objects else None
                await AuditService.log_event(
                    db=db,
                    action_type="CREATE_BATCH",
                    resource_type="RECEIPT",
                    actor_type="USER" if batch_user_id else "SYSTEM",
                    actor_id=batch_user_id or WORKER_ID,
                    severity="INFO",
                    metadata={
                        "count": len(valid_receipt_objects),
                        "machine_id": sync_data.machine_id,
                        "first_local_id": valid_receipt_objects[0].local_id,
                        "last_local_id": valid_receipt_objects[-1].local_id
                    }
                )
                # --- [Phase 2 Hardening] Scale-out Checkpointing ---
                # Create a checkpoint after batch persistence to speed up future audits
                # Checkpoints are triggered every 1000 records
                from app.services.integrity_service import IntegrityService
                last_r = valid_receipt_objects[-1]
                await IntegrityService.create_checkpoint_if_needed(
                    db, 
                    last_id=last_r.id, 
                    last_hash=last_r.current_hash
                )
                # -----------------------------------------------
                
                synced_count += len(valid_receipt_objects)
            except Exception as e:
                logger.error(f"Bulk insert failed: {e}")
                raise e  # Rollback

        await db.commit()

        return SyncResponse(
            synced=synced_count,
            failed=failed_count,
            duplicates=duplicate_count,
            error_map=error_map
        )
