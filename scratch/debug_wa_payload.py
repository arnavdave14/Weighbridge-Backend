import asyncio
import os
import sys
import logging

# Ensure 'app' is in path
sys.path.append(os.getcwd())

from app.services.whatsapp_service import send_whatsapp

# Set logging to DEBUG to see full payload and response body
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_whatsapp_media():
    sender_channel = "919407184405:30"
    target_number = "8962380001"
    
    print(f"🚀 [DEBUG] Testing Strict WhatsApp Media Delivery...")
    print(f"   Mandatory Channel: {sender_channel}")
    print(f"   Target Number:     {target_number}")
    print("-" * 60)
    
    # Send ONLY a PDF (no text) to verify media flow independently
    dummy_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"
    
    print("Action: Sending Single PDF Campaign...")
    result = await send_whatsapp(
        phone=target_number,
        message="Debug: Strict Media Delivery Check",
        pdf_content=dummy_pdf_content,
        filename="debug_receipt.pdf",
        sender_channel=sender_channel
    )
    
    print("-" * 60)
    print(f"Final Result: {result}")
    
    if result.get("status") == "success":
        print("\n✅ Verification SUCCESS: Provider confirmed campaign creation.")
        print("💡 Please check the WhatsApp device and portal dashboard now.")
    else:
        print("\n❌ Verification FAILED: See logs above for provider error.")

if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("❌ Error: .env file missing.")
        sys.exit(1)
        
    asyncio.run(debug_whatsapp_media())
