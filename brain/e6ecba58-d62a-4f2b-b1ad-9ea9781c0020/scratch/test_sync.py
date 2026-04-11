
import asyncio
from datetime import datetime
from app.database.sqlite import local_session
from app.services.sync_service import SyncService
from app.schemas.schemas import ReceiptSync, ReceiptCreate
from app.models.admin_models import ActivationKey

async def test_sync():
    print("--- Testing Sync with Flexible Schema ---")
    async with local_session() as db:
        # Create a mock ActivationKey
        mock_key = ActivationKey(id="123e4567-e89b-12d3-a456-426614174000", token="TEST-TOKEN", labels=[])
        
        # Define a flexible payload
        payload = {
            "data": {
                "gross": 50000,
                "tare": 15000,
                "net": 35000,
                "truck_no": "MP09 AB 1234",
                "material": "Coal",
                "customer": "Adani Power",
                "nested": {"foo": "bar"}
            }
        }
        
        sync_data = ReceiptSync(
            machine_id="MCH-001",
            receipts=[
                ReceiptCreate(
                    local_id=101,
                    date_time=datetime.now(),
                    payload_json=payload,
                    image_urls=["https://example.com/img1.jpg"],
                    user_id="employee-uuid"
                )
            ]
        )
        
        response = await SyncService.process_batch_sync(
            db=db,
            sync_data=sync_data,
            activation_key=mock_key,
            schema_version=2
        )
        
        print(f"Sync Response: {response.synced} synced, {response.failed} failed")
        
        # Verify result in DB
        from sqlalchemy import text
        res = await db.execute(text("SELECT payload_json, search_text, image_urls FROM receipts WHERE local_id = 101"))
        row = res.fetchone()
        print(f"Inserted Payload: {row[0]}")
        print(f"Inserted Search Text: {row[1]}")
        print(f"Inserted Image URLs: {row[2]}")

if __name__ == "__main__":
    asyncio.run(test_sync())
