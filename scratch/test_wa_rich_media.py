import asyncio
import os
import sys

# Ensure 'app' is in path
sys.path.append(os.getcwd())

from app.services.whatsapp_service import send_whatsapp

async def test_rich_connectivity():
    sender_channel = "919407184405:30"
    target_number = "8962380001"
    
    # Path to the generated receipt image
    image_path = "/Users/apple/.gemini/antigravity/brain/e11af8e0-1a94-4c62-9301-fd2a16fa7911/weighbridge_receipt_preview_1776351555705.png"
    
    print(f"🚀 Testing RICH MEDIA WhatsApp Connectivity (Message + Image + PDF)...")
    print(f"   Sender Channel: {sender_channel}")
    print(f"   Target Number:  {target_number}")
    print("-" * 40)
    
    try:
        if not os.path.exists(image_path):
            print(f"Error: Image not found at {image_path}")
            return
            
        with open(image_path, "rb") as f:
            image_content = f.read()
            
        dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
        
        print("[*] Dispatching rich media campaign...")
        result = await send_whatsapp(
            phone=target_number,
            receipt_id=999,
            message="✅ RICH MEDIA TEST: This message contains both an IMAGE preview and a PDF document in one dispatch.",
            pdf_content=dummy_pdf_content,
            image_content=image_content,
            filename="Receipt_999.pdf",
            image_filename="Preview_999.png",
            sender_channel=sender_channel
        )
        
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Rich Media Test Failed: {e}")
        
    print("=" * 40)

if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("Error: .env file not found.")
        sys.exit(1)
        
    asyncio.run(test_rich_connectivity())
