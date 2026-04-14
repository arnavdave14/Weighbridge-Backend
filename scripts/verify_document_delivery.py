import asyncio
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.postgres import remote_session
from app.services.document_delivery_service import DocumentDeliveryService
from app.models.admin_models import DocumentDeliveryLog
from sqlalchemy import select

async def main():
    print("Testing Document Delivery Service Flow...")
    
    # Generate some fake test PDF bytes
    mock_pdf_bytes = b"%PDF-1.4 mock pdf content test flow"
    
    try:
        # Step 1: Call process_and_deliver_document
        print("1. Submitting test document delivery...")
        success = await DocumentDeliveryService.process_and_deliver_document(
            key_id=None,
            document_type="invoice",
            document_name="test_invoice_001.pdf",
            document_bytes=mock_pdf_bytes,
            metadata_json={"amount": 1500, "customer": "TestCorp"},
            target_email="test12345@example.com",
            target_whatsapp="919999999999"
        )
        
        print(f"   -> Service returned success: {success}")
        
        # Step 2: Verify Log Entry in DB
        print("2. Verifying DocumentDeliveryLog in DB...")
        async with remote_session() as db:
            stmt = select(DocumentDeliveryLog).where(DocumentDeliveryLog.document_name == "test_invoice_001.pdf").order_by(DocumentDeliveryLog.created_at.desc())
            result = await db.execute(stmt)
            log = result.scalars().first()
            
            if log:
                print(f"   ✅ Log Found! ID: {log.id}")
                print(f"   - Status: {log.status}")
                print(f"   - Email Used: {log.email_used}")
                print(f"   - WhatsApp Channel: {log.whatsapp_channel}")
                print(f"   - Attachments: {log.attachments}")
                print(f"   - Latency: {log.latency}s")
            else:
                print("   ❌ Log NOT Found in DB!")
                
    except Exception as e:
        print(f"Error during flow test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
