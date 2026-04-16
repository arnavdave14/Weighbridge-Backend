import asyncio
import os
import sys

# Ensure 'app' is in path
sys.path.append(os.getcwd())

from app.services.whatsapp_service import send_whatsapp

async def test_connectivity():
    sender_channel = "919407184405:30"
    target_number = "8962380001"
    
    print(f"🚀 Testing FINAL FIX WhatsApp Connectivity...")
    print(f"   Sender Channel: {sender_channel}")
    print(f"   Target Number:  {target_number}")
    print("-" * 40)
    
    try:
        # Test 1: Plain Text
        print("Test 1: Sending plain text message...")
        result_text = await send_whatsapp(
            phone=target_number,
            receipt_id=0,
            message="Hello! This is a test message from the new Payload fix. If you see this, connectivity is WORKING.",
            sender_channel=sender_channel
        )
        print(f"Result (Text): {result_text}")
        
    except Exception as e:
        print(f"Text Test Failed: {e}")
        
    print("-" * 40)
    
    try:
        # Test 2: PDF
        print("Test 2: Sending dummy PDF...")
        dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
        
        result_pdf = await send_whatsapp(
            phone=target_number,
            receipt_id=0,
            message="Here is your true 2MB-limit validated Weighbridge Receipt PDF.",
            pdf_content=dummy_pdf_content,
            filename="test_receipt.pdf",
            sender_channel=sender_channel
        )
        print(f"Result (PDF): {result_pdf}")
        
    except Exception as e:
        print(f"PDF Test Failed: {e}")
        
    print("=" * 40)

if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("Error: .env file not found. Ensure you are running from the backend root.")
        sys.exit(1)
        
    asyncio.run(test_connectivity())
