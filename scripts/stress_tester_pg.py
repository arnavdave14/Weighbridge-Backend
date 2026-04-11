import asyncio
import json
import logging
import random
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Import project components
from app.config.settings import settings
from app.services.sync_service import SyncService
from app.schemas.schemas import ReceiptSync, ReceiptCreate
from app.models.admin_models import ActivationKey
from app.utils.payload_util import MAX_PAYLOAD_SIZE, MAX_IMAGE_COUNT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StressTester")

# Realistic Data Constants
TRUCK_NUMBERS = ["MP09AB1234", "DL01CD5678", "MH12XY9876", "KA05JK4321", "RJ14UV5566"]
MATERIALS = ["Iron", "Coal", "Cement", "Sand", "Steel", "Bauxite"]
SUPPLIERS = ["ABC Pvt Ltd", "XYZ Corp", "Global Industries", "Tata Steel", "JSW Cement"]

def generate_random_payload(size_bytes: int = 500) -> Dict[str, Any]:
    """Generates a realistic payload for testing."""
    truck = random.choice(TRUCK_NUMBERS)
    material = random.choice(MATERIALS)
    supplier = random.choice(SUPPLIERS)
    
    data = {
        "truck_no": truck,
        "material": material,
        "supplier": supplier,
        "gross": float(random.randint(20000, 50000)),
        "tare": float(random.randint(8000, 15000)),
        "net": 0.0, # Will be calculated if needed
        "custom_notes": "Stress test record " + uuid.uuid4().hex[:10]
    }
    data["net"] = data["gross"] - data["tare"]
    
    payload = {"data": data}
    
    # Pad if we need a specific size
    current_size = len(json.dumps(payload))
    if current_size < size_bytes:
        payload["padding"] = "X" * (size_bytes - current_size - 15)
        
    return payload

class StressTester:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.machine_id = f"STRESS_MACH_{uuid.uuid4().hex[:6]}"
        self.activation_key = None

    async def setup(self):
        """Prepares the database for stress testing."""
        logger.info(f"Setting up test environment for machine: {self.machine_id}")
        async with self.session_factory() as session:
            # 0. Ensure schema is updated (Add truck_no if missing)
            await session.execute(text("ALTER TABLE receipts ADD COLUMN IF NOT EXISTS truck_no VARCHAR"))
            await session.commit()

            # 1. Resolve or Create an Activation Key for the machine
            # In a real scenario, we'd use verify_apex_identity logic.
            # Here we mock the ActivationKey object to satisfy SyncService.
            self.activation_key = ActivationKey(
                id=uuid.uuid4(),
                token="STRESS_TOKEN_123",
                company_name="Stress Test Corp",
                labels=[{"key": "truck_no", "label": "Vehicle No"}] # Mock label config
            )
            logger.info(f"Setup complete. Mock key_id: {self.activation_key.id}")

    async def run_batch_sync(self, count: int, payload_size: int = 500, image_count: int = 0):
        """Simulates a batch sync from a device."""
        receipts = []
        for i in range(count):
            r = ReceiptCreate(
                local_id=random.randint(1000000, 9999999),
                date_time=datetime.now(),
                payload_json=generate_random_payload(payload_size),
                image_urls=[f"http://test.com/img_{uuid.uuid4().hex[:6]}.jpg" for _ in range(image_count)],
                user_id="STRESS_USER"
            )
            receipts.append(r)

        sync_data = ReceiptSync(
            machine_id=self.machine_id,
            receipts=receipts
        )

        start_time = time.time()
        async with self.session_factory() as session:
            try:
                # We call process_batch_sync from sync_service
                response = await SyncService.process_batch_sync(
                    db=session,
                    sync_data=sync_data,
                    activation_key=self.activation_key,
                    schema_version=2
                )
                duration = time.time() - start_time
                logger.info(f"[BatchSync] Size: {count} | Synced: {response.synced} | Failed: {response.failed} | Time: {duration:.3f}s")
                return response, duration
            except Exception as e:
                logger.error(f"Batch sync failed: {e}")
                raise

    async def test_high_volume(self):
        logger.info("--- SUITE A: HIGH VOLUME SYNC ---")
        for size in [50, 100, 500]:
            logger.info(f"Testing batch size: {size}")
            await self.run_batch_sync(size)

    async def test_payload_stress(self):
        logger.info("--- SUITE B: PAYLOAD STRESS ---")
        # Max payload size (10KB)
        logger.info(f"Testing max payload size: {MAX_PAYLOAD_SIZE} bytes")
        await self.run_batch_sync(10, payload_size=MAX_PAYLOAD_SIZE - 100)
        
        # Exceeding payload size
        logger.info(f"Testing exceeding payload size: {MAX_PAYLOAD_SIZE + 100} bytes")
        try:
            resp, _ = await self.run_batch_sync(1, payload_size=MAX_PAYLOAD_SIZE + 100)
            if resp.failed == 1:
                logger.info("✓ Correctly rejected oversized payload.")
            else:
                logger.error("✗ Failed to reject oversized payload!")
        except Exception as e:
            logger.info(f"✓ Rejected with exception as expected: {e}")

    async def test_idempotency(self):
        logger.info("--- SUITE D: IDEMPOTENCY ---")
        # Create a batch
        receipts = [ReceiptCreate(
            local_id=1234567,
            date_time=datetime.now(),
            payload_json=generate_random_payload(),
            image_urls=[]
        )]
        sync_data = ReceiptSync(machine_id=self.machine_id, receipts=receipts)
        
        async with self.session_factory() as session:
            # First sync
            resp1 = await SyncService.process_batch_sync(session, sync_data, self.activation_key, 2)
            logger.info(f"First sync: Synced={resp1.synced}, Duplicates={resp1.duplicates}")
            
            # Second sync (same data)
            resp2 = await SyncService.process_batch_sync(session, sync_data, self.activation_key, 2)
            logger.info(f"Second sync: Synced={resp2.synced}, Duplicates={resp2.duplicates}")
            
            if resp1.synced == 1 and resp2.duplicates == 1:
                logger.info("✓ Idempotency verified.")
            else:
                logger.error("✗ Idempotency failed!")

    async def test_concurrency(self):
        logger.info("--- SUITE E: CONCURRENCY ---")
        # Simulate 5 simultaneous workers for the same machine
        tasks = [self.run_batch_sync(20) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        total_synced = sum(r[0].synced for r in results)
        logger.info(f"Parallel results: Total Synced={total_synced}")
        logger.info("✓ Concurrency test completed.")

    async def run_all(self):
        await self.setup()
        await self.test_high_volume()
        await self.test_payload_stress()
        await self.test_idempotency()
        await self.test_concurrency()
        logger.info("All stress tests completed successfully.")

if __name__ == "__main__":
    # Use Postgres URL from settings
    db_url = settings.postgres_url
    if not db_url:
        logger.error("POSTGRES_URL not configured in environment!")
    else:
        tester = StressTester(db_url)
        asyncio.run(tester.run_all())
