import asyncio
import os
import sys
import logging
import requests
import json
import time

# Ensure 'app' is in path to load settings/modules
sys.path.append(os.getcwd())

from app.config.settings import settings

# Configure verbose logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wa_discovery")

# Credentials
API_KEY = settings.DIGITALSMS_API_KEY
BASE_URL = "https://api.digitalsms.net"
TARGET_MOBILE = "918962380001"
SENDER_CHANNEL = "919407184405:30"

# Dummy PDF Content
PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"

async def run_discovery():
    print(f"\n🚀 STARTING CONTROLLED DISCOVERY: WHATSAPP MEDIA API")
    print(f"   Target:  {TARGET_MOBILE}")
    print(f"   Channel: {SENDER_CHANNEL}")
    print("=" * 60)

    # --- Attempt A: POST /wapp/campaign/save (Legacy Format) ---
    await attempt_variation(
        name="Attempt A: Legacy Campaign Save",
        url=f"{BASE_URL}/wapp/campaign/save",
        data={
            "apikey": API_KEY,
            "campname": f"Disc_A_{int(time.time())}",
            "mobile": TARGET_MOBILE,
            "msg": "Discovery Attempt A: Legacy Format",
            "channel": SENDER_CHANNEL
        },
        files={"pdf": ("test.pdf", PDF_CONTENT, "application/pdf")}
    )

    # --- Attempt B: POST /wapp/api/send (Transactional Multipart) ---
    await attempt_variation(
        name="Attempt B: Transactional Multipart",
        url=f"{BASE_URL}/wapp/api/send",
        data={
            "apikey": API_KEY,
            "mobile": TARGET_MOBILE,
            "msg": "Discovery Attempt B: Transactional Multipart",
            "channel": SENDER_CHANNEL
        },
        files={"pdf": ("test.pdf", PDF_CONTENT, "application/pdf")}
    )

    # --- Attempt C: Alternate Field Naming (Newer Format) ---
    await attempt_variation(
        name="Attempt C: Alternate Field Naming (Dashboard-Style)",
        url=f"{BASE_URL}/wapp/campaign/save",
        data={
            "apiKey": API_KEY,
            "campaignName": f"Disc_C_{int(time.time())}",
            "mobileNumbers": TARGET_MOBILE,
            "message": "Discovery Attempt C: Alternate Naming",
            "deviceId": SENDER_CHANNEL,
            "type": "MEDIA"
        },
        files={"mediaFile": ("test.pdf", PDF_CONTENT, "application/pdf")}
    )

    print("\n🏁 DISCOVERY COMPLETE.")

async def attempt_variation(name: str, url: str, data: dict, files: dict):
    print(f"\n👉 {name}")
    print(f"   URL:   {url}")
    
    # Mask API key for logging
    log_data = data.copy()
    if "apikey" in log_data: log_data["apikey"] = "MASKED"
    if "apiKey" in log_data: log_data["apiKey"] = "MASKED"
    
    print(f"   Data:  {json.dumps(log_data)}")
    print(f"   Files: Keys present {list(files.keys())}")
    
    try:
        # We use a direct requests call to avoid any wrapper logic
        resp = requests.post(url, data=data, files=files, timeout=20)
        
        print(f"   Status: {resp.status_code}")
        print(f"   Headers: {resp.request.headers.get('Content-Type')}")
        print(f"   Body:   {resp.text}")
        
        if resp.status_code == 200 and '"status":"success"' in resp.text.lower():
            print(f"\n🌟 [POTENTIAL SUCCESS] Provider accepted {name}!")
            # In a real discovery, we'd stop here if user wants "First Valid Success"
            # But for log completeness we will run all 3 unless specified.
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(run_discovery())
