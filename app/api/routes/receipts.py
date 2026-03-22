from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.session import get_db
from app.schemas.schemas import ReceiptSync, SyncResponse
from app.services.sync_service import SyncService
from app.services.receipt_service import ReceiptService
from app.core import security
import os

router = APIRouter()

# Setup templates for public previews
templates = Jinja2Templates(directory="app/templates")

@router.post("/sync/receipts", response_model=SyncResponse, tags=["Sync"])
async def sync_receipts(
    sync_data: ReceiptSync,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(security.get_current_user)
):
    """
    Offline-first sync endpoint for Flutter app.
    Batch receipts for a given machine_id.
    Prevents duplicates based on (machine_id, local_id).
    """
    return await SyncService.process_batch_sync(db, sync_data)

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

@router.get("/receipts/{share_token}/pdf", tags=["Public"])
async def get_receipt_pdf(share_token: str, db: AsyncSession = Depends(get_db)):
    """
    Placeholder for PDF generation.
    Returns a simple message or dummy PDF content.
    """
    receipt = await ReceiptService.get_by_share_token(db, share_token)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
        
    return Response(content="PDF content would be generated here from receipt data.", media_type="application/pdf")
