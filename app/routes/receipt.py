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
    from app.services.whatsapp_service import send_whatsapp_message
    from app.services.sms_service import send_sms_fast2sms
    from app.services.email_service import send_email_receipt

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

        # Send WhatsApp (Gupshup) to all targets
        for p in targets_phone:
            background_tasks.add_task(
                send_whatsapp_message,
                receipt_id=receipt.id,
                phone=str(p),
                vehicle=str(vehicle),
                weight=net_weight,
                token=receipt.share_token
            )

        # Send Text SMS (Fast2SMS) to all targets
        for p in targets_phone:
            background_tasks.add_task(
                send_sms_fast2sms,
                receipt_id=receipt.id,
                phone=str(p),
                vehicle=str(vehicle),
                weight=net_weight,
                token=receipt.share_token
            )
            
        # Send Email to all targets
        for e in targets_email:
            background_tasks.add_task(
                send_email_receipt,
                receipt_id=receipt.id,
                email=str(e),
                vehicle=str(vehicle),
                weight=net_weight,
                token=receipt.share_token
            )
            
    return sync_result
