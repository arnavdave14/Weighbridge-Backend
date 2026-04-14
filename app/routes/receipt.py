from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Machine
from app.database.db_manager import get_db
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
    
    # Get the machine for settings (contains the owner's mobile number)
    from app.services.document_delivery_service import DocumentDeliveryService

    stmt = select(Machine).where(Machine.machine_id == sync_data.machine_id)
    res = await db.execute(stmt)
    machine = res.scalar_one_or_none()
    
    # Target values from CompanySettings (owner's preference)
    owner_phone = machine.settings.get("mobile") if machine and machine.settings else None
    owner_email = machine.settings.get("email") if machine and machine.settings else None
    
    # 2. Queue notifications for each new receipt record
    for receipt in new_receipts:
        # Resolve vehicle label
        vehicle = receipt.custom_data.get("vehicle_number") or \
                  receipt.custom_data.get("Vehicle No") or \
                  receipt.custom_data.get("Vehicle Number") or "N/A"
                  
        net_weight = float(receipt.gross_weight - receipt.tare_weight)
        
        # Also check if the receipt itself carries a customer phone/email
        customer_phone = receipt.custom_data.get("phone") or receipt.custom_data.get("mobile")
        customer_email = receipt.custom_data.get("email") or receipt.custom_data.get("Email")

        # Combine owner and customer (if unique)
        targets_phone = set(filter(None, [owner_phone, customer_phone]))
        targets_email = set(filter(None, [owner_email, customer_email]))

        # We trigger Document Delivery for each distinct combination of targets
        # To avoid sending the same document 4 times, we'll just send once per target list.
        # Simple loop: pick one primary target if multiple, but our new service is built for one-to-one.
        # We will dispatch a background delivery job for each target pair.
        # In a real business scenario you'd group them or loop.
        
        metadata = receipt.custom_data or {}
        metadata["share_token"] = receipt.share_token
        metadata["truck_no"] = vehicle
        metadata["weight"] = net_weight

        for p in targets_phone:
            background_tasks.add_task(
                DocumentDeliveryService.process_and_deliver_document,
                key_id=machine.key_id if machine else None,
                document_type="receipt",
                document_name=f"receipt_{receipt.local_id}.html",
                document_bytes=None,
                metadata_json=metadata,
                target_email=None,
                target_whatsapp=str(p)
            )

        for e in targets_email:
            background_tasks.add_task(
                DocumentDeliveryService.process_and_deliver_document,
                key_id=machine.key_id if machine else None,
                document_type="receipt",
                document_name=f"receipt_{receipt.local_id}.html",
                document_bytes=None,
                metadata_json=metadata,
                target_email=str(e),
                target_whatsapp=None
            )
            
    return sync_result
