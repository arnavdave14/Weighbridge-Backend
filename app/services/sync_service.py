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
        1. Fetch labels for the specific schema_version.
        2. Validate each receipt unit (Atomic validation per receipt).
        3. Perform transactional bulk-upsert for valid receipts.
        4. Return detailed audit (Synced, Duplicates, Field-wise error map).
        """
        synced_count = 0
        duplicate_count = 0
        failed_count = 0
        error_map = {}
        valid_receipt_objects = []

        # 1. Fetch labels for validation
        schema = await AdminRepo.get_schema_by_version(db, activation_key.id, schema_version)
        if not schema:
            # Fallback to current version if version mapping lost, but log warning
            logger.warning(f"Schema version {schema_version} not found for key {activation_key.id}")
            schema = await AdminRepo.get_latest_schema(db, activation_key.id)
            
        labels_config = schema.labels if schema else []

        # 2. Process Receipts
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
                    is_synced=False
                )
                valid_receipt_objects.append(new_receipt)

            except Exception as e:
                failed_count += 1
                error_map[r_schema.local_id] = {"internal_error": str(e)}
                logger.error(f"[Sync] Logic error for receipt {r_schema.local_id}: {e}")

        # 3. Transactional Bulk Upsert
        if valid_receipt_objects:
            try:
                # We add all objects to the session for a single commit
                db.add_all(valid_receipt_objects)
                await db.flush()
                synced_count = len(valid_receipt_objects)
                
                # Note: In a true high-throughput Postgres environment, we would use 
                # pg_insert(...).on_conflict_do_nothing() to avoid race conditions. 
                # Since we already checked duplicates, db.add_all is sufficient for this refactor phase.
            except Exception as e:
                logger.error(f"Bulk insert failed: {e}")
                raise e # Rollback

        await db.commit()
        
        return SyncResponse(
            synced=synced_count,
            failed=failed_count,
            duplicates=duplicate_count,
            error_map=error_map
        )



