import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Receipt, ChainCheckpoint
from app.utils.crypto_util import generate_receipt_hash, GENESIS_HASH

logger = logging.getLogger(__name__)

class IntegrityService:
    # Threshold for fast startup check
    DYNAMIC_STARTUP_THRESHOLD = 1000
    CHECKPOINT_INTERVAL = 1000
    
    # In-memory storage for override state
    _override_expires_at: Optional[datetime] = None

    @staticmethod
    async def create_checkpoint_if_needed(db: AsyncSession, last_id: int, last_hash: str):
        """
        Creates a checkpoint if the record count has increased by the interval 
        since the last checkpoint.
        """
        # 1. Total records count
        count_stmt = select(func.count(Receipt.id))
        count_res = await db.execute(count_stmt)
        total_count = count_res.scalar() or 0
        
        if total_count == 0:
            return

        # 2. Get latest checkpoint
        cp_stmt = select(ChainCheckpoint).order_by(ChainCheckpoint.checkpoint_index.desc()).limit(1)
        cp_res = await db.execute(cp_stmt)
        latest_cp = cp_res.scalar_one_or_none()
        
        last_cp_index = latest_cp.checkpoint_index if latest_cp else 0
        
        # 3. Trigger if we've crossed the interval threshold
        if total_count - last_cp_index >= IntegrityService.CHECKPOINT_INTERVAL:
            # 4. Meta-Chain Hash Calculation
            # checkpoint_hash = SHA256(prev_cp_hash || current_data_hash)
            prev_hash = latest_cp.checkpoint_hash if latest_cp else GENESIS_HASH
            
            # Note: last_hash is the receipt's current_hash
            meta_payload = f"{prev_hash}||{last_hash}"
            meta_hash = hashlib.sha256(meta_payload.encode()).hexdigest()

            checkpoint = ChainCheckpoint(
                receipt_id=last_id,
                checkpoint_index=total_count,
                checkpoint_hash=meta_hash, # NOW STORES THE META-CHAIN HASH
                previous_checkpoint_hash=prev_hash
            )
            db.add(checkpoint)
            logger.info(f"💾 Created meta-chained checkpoint at index {total_count} (Anchor ID: {last_id})")

    @staticmethod
    async def verify_startup_integrity(db: AsyncSession) -> Dict[str, Any]:
        """
        Dynamic startup check:
        - If total records < 1000: Full chain check.
        - If total records >= 1000: Check last 1000 records.
        """
        count_stmt = select(func.count(Receipt.id))
        count_res = await db.execute(count_stmt)
        total_count = count_res.scalar() or 0
        
        if total_count <= IntegrityService.DYNAMIC_STARTUP_THRESHOLD:
            logger.info(f"[Integrity] Small dataset ({total_count} records). Performing full startup check.")
            return await IntegrityService.verify_recent_records(db, limit=None)
        else:
            logger.info(f"[Integrity] Large dataset ({total_count} records). Performing partial startup check (last {IntegrityService.DYNAMIC_STARTUP_THRESHOLD}).")
            return await IntegrityService.verify_recent_records(db, limit=IntegrityService.DYNAMIC_STARTUP_THRESHOLD)

    @staticmethod
    async def verify_recent_records(db: AsyncSession, limit: Optional[int] = None, start_from_checkpoint: bool = False) -> Dict[str, Any]:
        """
        Verifies a subset of the chain. 
        If limit is None and start_from_checkpoint=True, uses the latest checkpoint as an anchor.
        """
        expected_previous_hash = GENESIS_HASH
        receipts_stmt = select(Receipt).order_by(Receipt.id.asc())
        
        if start_from_checkpoint and limit is None:
            # 1. Validate Meta-Chain of Checkpoints (Defense-in-Depth)
            # We verify the last 3 checkpoints to ensure the Meta-Chain hasn't been substituted
            cp_stmt = select(ChainCheckpoint).order_by(ChainCheckpoint.checkpoint_index.desc()).limit(3)
            cp_res = await db.execute(cp_stmt)
            checkpoints = list(cp_res.scalars().all())
            
            if not checkpoints:
                return receipts_stmt, expected_previous_hash

            # Verify meta-chain links
            # We check if CP[i] correctly references CP[i+1]
            for i in range(len(checkpoints) - 1):
                curr_cp = checkpoints[i]
                prev_cp = checkpoints[i+1]
                if curr_cp.previous_checkpoint_hash != prev_cp.checkpoint_hash:
                    logger.critical(f"🚨 CHECKPOINT META-CHAIN BROKEN between CP {curr_cp.checkpoint_index} and {prev_cp.checkpoint_index}!")
                    raise RuntimeError("Checkpoint Meta-Chain Integrity Failure")

            # 2. Latest valid checkpoint is our anchor
            checkpoint = checkpoints[0]
            logger.debug(f"Anchoring verification to hardened checkpoint {checkpoint.checkpoint_index}")
            
            # Wait, the meta_hash was SHA256(prev_cp_hash || receipt_hash)
            # To verify the RECORD chain, we need the ORIGINAL receipt_hash.
            # But we only stored the meta_hash in ChainCheckpoint.checkpoint_hash.
            # ERROR in design? No: 
            # We can retrieve the record hash from the Receipt table and verify it matches the Meta-Chain.
            
            anchor_receipt = await db.get(Receipt, checkpoint.receipt_id)
            if not anchor_receipt:
                raise RuntimeError(f"Checkpoint anchor receipt {checkpoint.receipt_id} missing!")
            
            # Verify the anchor receipt matches the Meta-Chain hash
            expected_meta = hashlib.sha256(f"{checkpoint.previous_checkpoint_hash}||{anchor_receipt.current_hash}".encode()).hexdigest()
            if checkpoint.checkpoint_hash != expected_meta:
                 logger.critical(f"🚨 CHECKPOINT DATA MISMATCH at index {checkpoint.checkpoint_index}!")
                 raise RuntimeError("Checkpoint Data Corruption Detected")

            expected_previous_hash = anchor_receipt.current_hash
            receipts_stmt = receipts_stmt.where(Receipt.id > checkpoint.receipt_id)

        if limit:
            # Fetch (limit + 1) to validate the link of the last N
            receipts_stmt = select(Receipt).order_by(Receipt.id.desc()).limit(limit + 1)
            result = await db.execute(receipts_stmt)
            receipts = list(result.scalars().all())
            receipts.reverse()
            
            if len(receipts) > limit:
                anchor_receipt = receipts[0]
                expected_previous_hash = anchor_receipt.current_hash
                receipts = receipts[1:]
        else:
            result = await db.execute(receipts_stmt)
            receipts = result.scalars().all()

        if not receipts:
            return {"is_valid": True, "total_checked": 0}

        is_valid = True
        broken_id = None
        error_msg = None
        total_checked = 0
        
        for receipt in receipts:
            if receipt.previous_hash != expected_previous_hash:
                is_valid = False
                broken_id = receipt.id
                error_msg = f"Chain linkage broken at ID {receipt.id}. Expected {expected_previous_hash}, got {receipt.previous_hash}"
                break
                
            receipt_dict = {
                "machine_id": receipt.machine_id,
                "local_id": receipt.local_id,
                "date_time": receipt.date_time,
                "gross_weight": receipt.gross_weight,
                "tare_weight": receipt.tare_weight,
                "rate": receipt.rate,
                "custom_data": receipt.custom_data,
                "user_id": receipt.user_id,
                "is_deleted": receipt.is_deleted,
                "corrected_from_id": receipt.corrected_from_id,
                "correction_reason": receipt.correction_reason
            }
            computed_hash = generate_receipt_hash(receipt_dict, receipt.previous_hash, version=receipt.hash_version)
            
            if receipt.current_hash != computed_hash:
                is_valid = False
                broken_id = receipt.id
                error_msg = f"Data integrity violation at ID {receipt.id}. Hash mismatch (v{receipt.hash_version})."
                break
            
            expected_previous_hash = receipt.current_hash
            total_checked += 1
            
        return {
            "is_valid": is_valid,
            "total_checked": total_checked,
            "broken_id": broken_id,
            "error_msg": error_msg,
            "last_verified_at": str(receipts[-1].date_time) if receipts else None
        }

    @staticmethod
    async def verify_chain_integrity(db: AsyncSession) -> Dict[str, Any]:
        """Performs a scalable chain audit using checkpoints."""
        return await IntegrityService.verify_recent_records(db, limit=None, start_from_checkpoint=True)

    @classmethod
    def set_override_mode(cls, duration_minutes: int):
        """
        Enables override mode with a strict 24h cap.
        """
        # Strict hard cap: 24 hours (1440 minutes)
        safe_duration = min(duration_minutes, 1440)
        cls._override_expires_at = datetime.now(timezone.utc) + timedelta(minutes=safe_duration)
        
        expires_str = cls._override_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        logger.warning(f"🚨 INTEGRITY OVERRIDE ENABLED until {expires_str}. Duration: {safe_duration}m")

    @classmethod
    def get_override_mode(cls) -> bool:
        """
        Checks if override mode is active and not expired.
        """
        if cls._override_expires_at is None:
            return False
        
        is_active = datetime.now(timezone.utc) < cls._override_expires_at
        if not is_active:
            # Auto-expire
            cls._override_expires_at = None
            logger.info("🛡️ Integrity override mode has expired.")
            
        return is_active

    @classmethod
    def get_override_expiry(cls) -> Optional[datetime]:
        return cls._override_expires_at
