import asyncio
import os
import sys

# Force a test database BEFORE any app imports
os.environ["SQLITE_PATH"] = "test_run_integrity.db"
os.environ["DATABASE_URL"] = ""
os.environ["REMOTE_DATABASE_URL"] = ""
os.environ["ENVIRONMENT"] = "testing"

from datetime import datetime
from decimal import Decimal
from app.utils.crypto_util import generate_receipt_hash, GENESIS_HASH
from app.database.sqlite import local_session, local_engine
from app.database.base import Base
from app.models.models import Receipt, Machine, ChainCheckpoint
from app.repositories.receipt_repo import ReceiptRepository
from app.services.integrity_service import IntegrityService
from sqlalchemy import select, func

async def test_deterministic_hashing():
    print("--- Testing Strictly Deterministic Hashing ---")
    data1 = {
        "gross_weight": 100, # Whole number
        "tare_weight": 50.1,
        "rate": None,
        "custom_data": {"a": 1, "b": "  trimmed  "}
    }
    data2 = {
        "gross_weight": Decimal("100.000"),
        "tare_weight": 50.10000001,
        "rate": None,
        "custom_data": {"b": "trimmed", "a": 1}
    }
    
    hash1 = generate_receipt_hash(data1, GENESIS_HASH)
    hash2 = generate_receipt_hash(data2, GENESIS_HASH)
    
    # Verify the internal normalization
    from app.utils.crypto_util import normalize_for_hash
    norm1 = normalize_for_hash(100)
    norm2 = normalize_for_hash(Decimal("100.000"))
    
    print(f"Norm 1 (int 100): {norm1}")
    print(f"Norm 2 (Decimal 100.000): {norm2}")
    
    if norm1 == "100.000" and norm1 == norm2 and hash1 == hash2:
        print("✅ Hashing is strictly deterministic (Fixed-precision strings).")
    else:
        print(f"❌ Hashing is NOT strictly deterministic! Got {norm1} vs {norm2}")
        sys.exit(1)

async def test_effective_records():
    print("\n--- Testing Effective Records ---")
    async with local_session() as db:
        # 1. Create Machine
        machine = Machine(machine_id="M1", name="Test Machine", is_active=True)
        db.add(machine)
        await db.commit()
        
        # 2. Create Record A
        r1 = Receipt(
            machine_id="M1", local_id=1, date_time=datetime.now(),
            gross_weight=1000, tare_weight=500, custom_data={},
            share_token="T1", whatsapp_status="pending",
            current_hash="H1", previous_hash=GENESIS_HASH,
            hash_version=1
        )
        db.add(r1)
        await db.commit()
        await db.refresh(r1)
        
        # 3. Correct A with B
        r2 = Receipt(
            machine_id="M1", local_id=2, date_time=datetime.now(),
            gross_weight=1100, tare_weight=500, custom_data={},
            share_token="T2", whatsapp_status="pending",
            corrected_from_id=r1.id, correction_reason="Error in weight",
            current_hash="H2", previous_hash="H1",
            hash_version=1
        )
        db.add(r2)
        await db.commit()
        
        # 4. Query Effective
        effective = await ReceiptRepository.get_all(db, include_history=False)
        all_records = await ReceiptRepository.get_all(db, include_history=True)
        
        print(f"Total records in DB: {len(all_records)}")
        print(f"Effective records: {len(effective)}")
        
        if len(effective) == 1 and effective[0].local_id == 2:
            print("✅ Effective record filtering works.")
        else:
            print(f"❌ Effective filtering failed.")
            sys.exit(1)

async def test_checkpoint_meta_chain():
    print("\n--- Testing Checkpoint Meta-Chaining ---")
    async with local_session() as db:
        # Clear existing
        from sqlalchemy import delete
        await db.execute(delete(ChainCheckpoint))
        await db.commit()
        
        # Create 2 Meta-Chained Checkpoints
        # Note: In real app these happen via IntegrityService.create_checkpoint_if_needed
        # but here we mock the sequence to verify the Meta-Chain logic
        
        # CP1
        cp1 = ChainCheckpoint(
            receipt_id=1, checkpoint_index=1000, 
            checkpoint_hash="META_HASH_1", previous_checkpoint_hash=GENESIS_HASH
        )
        db.add(cp1)
        await db.commit()
        
        # CP2 (Mismatched Meta-Chain link)
        cp2 = ChainCheckpoint(
            receipt_id=2, checkpoint_index=2000, 
            checkpoint_hash="META_HASH_2", previous_checkpoint_hash="WRONG_LINK"
        )
        db.add(cp2)
        await db.commit()
        
        print("Verifying broken meta-chain detection...")
        try:
            await IntegrityService.verify_chain_integrity(db)
            print("❌ Meta-chain failure NOT detected!")
            sys.exit(1)
        except RuntimeError as e:
            if "Meta-Chain Integrity Failure" in str(e):
                print("✅ Meta-chain failure detected correctly.")
            else:
                print(f"❌ Unexpected error: {e}")
                sys.exit(1)

async def test_integrated_checkpointing():
    print("\n--- Testing Integrated Checkpointing ---")
    async with local_session() as db:
        from sqlalchemy import delete
        await db.execute(delete(ChainCheckpoint))
        await db.execute(delete(Receipt))
        await db.commit()
        
        from app.services.integrity_service import IntegrityService
        
        print(f"Simulating {IntegrityService.CHECKPOINT_INTERVAL} records...")
        for i in range(1, IntegrityService.CHECKPOINT_INTERVAL + 1):
            r = Receipt(
                machine_id="M1", local_id=1000+i, date_time=datetime.now(),
                gross_weight=10, tare_weight=5, custom_data={},
                share_token=f"SEC_TOKEN_{i}", whatsapp_status="pending",
                current_hash=f"H_{i}", previous_hash="xxx", hash_version=1
            )
            db.add(r)
            if i % IntegrityService.CHECKPOINT_INTERVAL == 0:
                await db.flush()
                await IntegrityService.create_checkpoint_if_needed(db, r.id, r.current_hash)
        
        await db.commit()
        
        res = await db.execute(select(ChainCheckpoint))
        checkpoints = res.scalars().all()
        print(f"Checkpoints created: {len(checkpoints)}")
        
        if len(checkpoints) == 1:
            cp = checkpoints[0]
            if cp.previous_checkpoint_hash == GENESIS_HASH:
                print(f"✅ CP1 created correctly with Genesis link.")
            else:
                print(f"❌ CP1 has wrong link: {cp.previous_checkpoint_hash}")
                sys.exit(1)
        else:
            print(f"❌ Expected 1 checkpoint, got {len(checkpoints)}")
            sys.exit(1)

async def main():
    print(f"Using Database: {local_engine.url}")
    
    if os.path.exists("test_run_integrity.db"):
        os.remove("test_run_integrity.db")
        
    async with local_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    await test_deterministic_hashing()
    await test_effective_records()
    await test_checkpoint_meta_chain()
    await test_integrated_checkpointing()
    print("\n🎉 ALL HARDENING TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
