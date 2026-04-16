from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Form, Header
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from app.database.db_manager import get_db
from app.models.models import Receipt, Machine
from app.database.sqlite import local_session
from app.database.postgres import remote_session
from app.schemas.schemas import ReceiptSync, SyncResponse
from app.services.sync_service import SyncService
from app.services.receipt_service import ReceiptService
from app.services.config_service import ConfigService
from app.api.machine_deps import verify_apex_identity
from app.models.admin_models import ActivationKey
from app.core import security
from app.api.security_deps import verify_integrity_block
import os

router = APIRouter()

# Setup templates for public previews
templates = Jinja2Templates(directory="app/templates")

@router.post("/sync/receipts", response_model=SyncResponse, tags=["Sync"])
async def sync_receipts(
    sync_data: ReceiptSync,
    x_schema_version: int = Header(..., alias="X-Schema-Version"),
    activation_key: ActivationKey = Depends(verify_apex_identity),
    db: AsyncSession = Depends(get_db),
    _integrity: None = Depends(verify_integrity_block)
):
    """
    APEX-TIER SECURE SYNC:
    - Validates HMAC-SHA256 signature of the batch.
    - Enforced by verify_apex_identity (Nonce/Timestamp/Signature).
    - Performs atomic batch validation against specific schema version.
    """
    return await SyncService.process_batch_sync(
        db=db, 
        sync_data=sync_data, 
        activation_key=activation_key,
        schema_version=x_schema_version
    )

@router.get("/sync/config", tags=["Sync"])
async def get_machine_config(
    request: Request,
    response: Response,
    activation_key: ActivationKey = Depends(verify_apex_identity),
    db: AsyncSession = Depends(get_db)
):
    """
    Pulls latest branding and label configuration.
    Supports ETags for bandwidth efficiency.
    """
    config = await ConfigService.get_machine_config(db, activation_key)
    
    # ETag Support
    etag = config.get("etag")
    if_none_match = request.headers.get("If-None-Match")
    
    if if_none_match == etag:
        return Response(status_code=304)
        
    response.headers["ETag"] = etag
    return config

@router.get("/r/{share_token}", response_class=HTMLResponse, tags=["Public"])
async def public_preview(
    request: Request,
    share_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns HTML Preview of a receipt.
    Public and accessible via share_token.
    """
    receipt = await ReceiptService.get_by_share_token(db, share_token)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Extract vehicle number from dynamic JSONB customData
    # Receipt.custom_data is a dict in SQLAlchemy because of JSONB
    vehicle_number = receipt.custom_data.get("vehicle_number", "N/A")
    
    return templates.TemplateResponse(
        "preview.html", 
        {
            "request": request, 
            "receipt": receipt,
            "vehicle_number": vehicle_number
        }
    )

@router.get("/r/{share_token}/pdf", tags=["Public"])
async def get_receipt_pdf(share_token: str, db: AsyncSession = Depends(get_db)):
    """
    Generates and returns PDF of a receipt.
    Public and accessible via share_token.
    """
    from app.services.pdf_service import PDFService
    from sqlalchemy.future import select
    from app.models.models import Machine

    receipt = await ReceiptService.get_by_share_token(db, share_token)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    # Get machine for settings (headers/footers)
    stmt = select(Machine).where(Machine.machine_id == receipt.machine_id)
    result = await db.execute(stmt)
    machine = result.scalar_one_or_none()
        
    pdf_bytes = PDFService.generate_receipt_pdf(receipt, machine)
    
    filename = f"RST-{str(receipt.local_id).zfill(5)}.pdf"
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/whatsapp/send", tags=["WhatsApp"])
async def whatsapp_send_direct(
    phone: str = Form(...),
    receipt_id: int = Form(0),
    caption: Optional[str] = Form(None),
    pdf_file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Primary endpoint to send WhatsApp messages.
    Uses ReceiptService to prepare data from SQLite.
    """
    from app.services.whatsapp_service import send_whatsapp
    
    # 1. Prepare Payload via Service (Isolates DB logic)
    payload = await ReceiptService.prepare_whatsapp_payload(db, receipt_id, caption)
    if not payload:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # 2. Overwrite PDF if uploaded manually
    if pdf_file:
        payload["pdf_content"] = await pdf_file.read()
        payload["filename"] = pdf_file.filename

    # 3. Resolve Sender Channel from Machine/Key
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    sender_channel = None
    if receipt:
        # Machine ID in Receipt relates to the Token in ActivationKey
        key_stmt = select(ActivationKey).where(ActivationKey.token == receipt.machine_id)
        key_res = await db.execute(key_stmt)
        key = key_res.scalar_one_or_none()
        if key:
            sender_channel = key.whatsapp_sender_channel

    # 4. Send via Stateless Service
    result = await send_whatsapp(
        phone=phone,
        sender_channel=sender_channel,
        **payload
    )
    
    # 4. Update SQLite status and enqueue for Postgres
    if receipt_id != 0:
        status = "sent" if result.get("status") == "success" else "failed"
        await ReceiptService.update_whatsapp_status(db, receipt_id, status)
        
    return result


@router.post("/whatsapp/send-test", tags=["WhatsApp"])
async def whatsapp_send_test(
    phone: str = Form(...),
    slip_no: int = Form(1001),
    vehicle: str = Form("MP09XL1726"),
    gross_weight: float = Form(35000.00),
    tare_weight: float = Form(12000.00),
    pdf_file: Optional[UploadFile] = File(None)
):
    """
    Test WhatsApp delivery with auto-generated PDF from service layer.
    """
    from app.services.whatsapp_service import send_whatsapp
    
    # 1. Prepare Dummy Payload via Service
    payload = await ReceiptService.prepare_test_whatsapp_payload(
        slip_no=slip_no,
        vehicle=vehicle,
        gross_weight=gross_weight,
        tare_weight=tare_weight
    )

    # 2. Overwrite PDF if uploaded manually
    if pdf_file:
        payload["pdf_content"] = await pdf_file.read()
        payload["filename"] = pdf_file.filename

    # 3. Resolve Sender Channel (Optional form field or default from testing)
    # In a full multi-tenant test, we'd pull this from the session or a passed parameter
    sender_channel = "919407184405:30" # Default testing channel
    
    # 4. Send via Stateless Service
    return await send_whatsapp(
        phone=phone,
        sender_channel=sender_channel,
        **payload
    )
