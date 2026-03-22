from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.schemas import ReceiptSync, SyncResponse
from app.services.sync_service import SyncService
from app.services.whatsapp_service import send_whatsapp_message
from app.core import security

router = APIRouter()

@router.post("/sync/receipts", response_model=SyncResponse, tags=["Sync"])
async def sync_receipts(
    sync_data: ReceiptSync,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(security.get_current_user)
):
    """
    Saves batch receipts and queues WhatsApp notifications with status tracking.
    """
    # 1. Persist receipts and get list of newly created objects
    sync_result, new_receipts = await SyncService.process_batch_sync(db, sync_data)
    
    # 2. Queue WhatsApp tasks for each new receipt record
    for receipt in new_receipts:
        # Extract vehicle and phone from JSONB custom_data
        # We check both common keys (user may use vehicle_number or Vehicle No)
        vehicle = receipt.custom_data.get("vehicle_number") or receipt.custom_data.get("Vehicle No", "N/A")
        phone = receipt.custom_data.get("phone") or receipt.custom_data.get("mobile_number")
        
        # We pass the real ID and share_token from the newly created DB row
        if phone:
            net_weight = float(receipt.gross_weight - receipt.tare_weight)
            
            # The background task now handles retries and database status updates internally
            background_tasks.add_task(
                send_whatsapp_message,
                receipt_id=receipt.id,
                phone=str(phone),
                vehicle=str(vehicle),
                weight=net_weight,
                token=receipt.share_token
            )
            
    return sync_result
