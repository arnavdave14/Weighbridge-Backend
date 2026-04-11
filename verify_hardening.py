import asyncio
import uuid
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.schemas import ReceiptSync, ReceiptItem
from app.services.sync_service import SyncService
from app.models.admin_models import ActivationKey

async def test_limits_and_performance():
    print("--- Starting Hardening Verification ---")
    
    # 1. Mock DB and Dependencies
    db = AsyncMock(spec=AsyncSession)
    
    # Mock ReceiptRepository.get_existing_local_ids to return empty (all new)
    with patch("app.services.sync_service.ReceiptRepository.get_existing_local_ids", new_callable=AsyncMock) as mock_batch_check:
        mock_batch_check.return_value = set()
        
        # Mock last hash
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_res
        
        # Activation Key (v2 Flow)
        key = ActivationKey(id=1, token="test-key", labels=[])
        
        # Case A: Receipt with 11 images (should fail image count check)
        sync_data_too_many_images = ReceiptSync(
            machine_id="MAC_001",
            receipts=[
                ReceiptItem(
                    local_id=101,
                    date_time=datetime.now(),
                    payload_json={"data": {"truck_no": "MP09AB1234", "gross": 500}},
                    image_urls=["http://img.com"] * 11
                )
            ]
        )
        
        print("\nTesting Image Count Limit (Max 10)...")
        result = await SyncService.process_batch_sync(db, sync_data_too_many_images, key, schema_version=2)
        print(f"Result: {result.dict()}")
        assert result.failed == 1
        assert "Image count exceeds limit of 10" in result.error_map["101"]
        print("✅ Image count limit enforced.")

        # Case B: Batch Performance (Reduced N+1)
        # 10 receipts in one batch
        sync_data_batch = ReceiptSync(
            machine_id="MAC_001",
            receipts=[
                ReceiptItem(
                    local_id=i,
                    date_time=datetime.now(),
                    payload_json={"data": {"truck_no": "MP09AB1234", "gross": 500}},
                    image_urls=[]
                ) for i in range(200, 210)
            ]
        )
        
        print("\nTesting Batch Idempotency Optimization...")
        await SyncService.process_batch_sync(db, sync_data_batch, key, schema_version=2)
        
        # Check how many times get_existing_local_ids was called
        # It should be exactly 1 call for the entire batch of 10.
        print(f"get_existing_local_ids call count: {mock_batch_check.call_count}")
        assert mock_batch_check.call_count == 2 # One from Case A, one from Case B
        print("✅ Performance optimized: 1 query per batch instead of N queries.")

        # Case C: Image Size Limit (1MB)
        from app.services.image_upload_service import upload_image_to_cloud
        print("\nTesting Image Size Limit (1MB)...")
        large_bytes = b"0" * (1 * 1024 * 1024 + 100) # 1MB + 100 bytes
        url = await upload_image_to_cloud(large_bytes, "too_large.jpg")
        print(f"URL for large image: {url}")
        assert url is None
        print("✅ Image size limit enforced.")

    print("\n--- Hardening Verification Complete: ALL PASSED ---")

if __name__ == "__main__":
    asyncio.run(test_limits_and_performance())
