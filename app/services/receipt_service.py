from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Receipt
from app.services.sync_service import SyncService
from app.repositories.receipt_repo import ReceiptRepository

class ReceiptService:
    @staticmethod
    async def get_by_share_token(db: AsyncSession, share_token: str) -> Receipt:
        """
        Publicly accessible receipt retrieval via random share_token.
        """
        return await ReceiptRepository.get_by_share_token(db, share_token)

    @staticmethod
    async def get_all_receipts(db: AsyncSession, skip: int = 0, limit: int = 100):
        return await ReceiptRepository.get_all(db, skip, limit)

    @staticmethod
    async def update_whatsapp_status(db: AsyncSession, receipt_id: int, status: str):
        """
        Updates the WhatsApp status in SQLite and enqueues an 'update' task for Postgres.
        """
        if receipt_id == 0:
            return
            
        receipt = await ReceiptRepository.update_status(db, receipt_id, status)
        if receipt:
            # Enqueue sync task so PostgreSQL is eventually updated
            await SyncService.enqueue_task(db, "receipt", receipt_id, action="update")
            await db.commit()

    @staticmethod
    async def prepare_whatsapp_payload(db: AsyncSession, receipt_id: int, caption_override: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetches receipt from SQLite, generates PDF, and prepares final payload for WhatsApp.
        Strictly reads from the provided SQLite session.
        """
        from app.services.pdf_service import PDFService
        
        receipt = await ReceiptRepository.get_by_id(db, receipt_id)
        if not receipt:
            return None

        vehicle = receipt.custom_data.get("vehicle_number", "N/A")
        net_weight = receipt.gross_weight - receipt.tare_weight
        
        caption = caption_override or (
            f"👉 *View/Download PDF*\n\n"
            f"Slip No.: {receipt.local_id}\n"
            f"Vehicle No.: {vehicle}\n"
            f"Gross Weight: {receipt.gross_weight:,.2f} kg\n"
            f"Tare Weight: {receipt.tare_weight:,.2f} kg\n"
            f"Net Weight: {net_weight:,.2f} kg\n"
            f"Date: {receipt.date_time.strftime('%I:%M %p | %d/%m/%Y')}\n\n"
            f"👉 *View PDF :-*"
        )

        pdf_content = PDFService.generate_receipt_pdf(receipt)
        filename = f"RST_{receipt.local_id}.pdf"

        return {
            "receipt_id": receipt_id,
            "message": caption,
            "pdf_content": pdf_content,
            "filename": filename
        }

    @staticmethod
    async def prepare_test_whatsapp_payload(
        slip_no: int, 
        vehicle: str, 
        gross_weight: float, 
        tare_weight: float
    ) -> Dict[str, Any]:
        """
        Prepares a test payload with dummy data and generated PDF.
        """
        from app.services.pdf_service import PDFService
        from app.models.models import Receipt
        from datetime import datetime
        
        net_weight = gross_weight - tare_weight
        caption = (
            f"👉 *View/Download PDF*\n\n"
            f"Slip No.: {slip_no}\n"
            f"Vehicle No.: {vehicle}\n"
            f"Gross Weight: {gross_weight:,.2f} kg\n"
            f"Tare Weight: {tare_weight:,.2f} kg\n"
            f"Net Weight: {net_weight:,.2f} kg\n"
            f"Date: {datetime.now().strftime('%I:%M %p | %d/%m/%Y')}\n\n"
            f"👉 *View PDF :-*"
        )
        
        dummy_receipt = Receipt(
            local_id=slip_no,
            date_time=datetime.now(),
            gross_weight=gross_weight,
            tare_weight=tare_weight,
            rate=0,
            custom_data={"vehicle_number": vehicle},
            share_token="test-token"
        )
        pdf_content = PDFService.generate_receipt_pdf(dummy_receipt)
        filename = f"RST_{slip_no}.pdf"

        return {
            "receipt_id": 0,
            "message": caption,
            "pdf_content": pdf_content,
            "filename": filename
        }
