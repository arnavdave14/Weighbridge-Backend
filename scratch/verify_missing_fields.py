import asyncio
import os
import sys
import requests
import json
import time

sys.path.append(os.getcwd())
from app.config.settings import settings

API_KEY = settings.DIGITALSMS_API_KEY
PORTAL_USER = settings.DIGITALSMS_PORTAL_USER
PORTAL_PASS = settings.DIGITALSMS_PORTAL_PASS
BASE_URL = "https://api.digitalsms.net"
TARGET_MOBILE = "918962380001"
SENDER_CHANNEL = "919407184405:30"
PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF"

def test_fresh_upload_and_post():
    session = requests.Session()
    # 1. Login
    session.post(f"{BASE_URL}/login", data={"username": PORTAL_USER, "password": PORTAL_PASS})
    
    # 2. Upload
    fname = f"debug_{int(time.time())}.pdf"
    upl_resp = session.post(f"{BASE_URL}/wapp/upload/media", files={"file": (fname, PDF_CONTENT, "application/pdf")})
    path = upl_resp.text.strip()
    print(f"[*] Fresh upload path: {path}")
    
    if "uploads/" not in path:
        print("Upload failed.")
        return
        
    # 3. Post Campaign exactly like Dashboard
    # Key insight: the dashboard includes ALL media keys, even if empty.
    # Omitting them likely caused the 400 Bad Request because their backend tries to read them unconditionally.
    data = {
        "campname": f"Validation_{int(time.time())}",
        "mobile": TARGET_MOBILE,
        "msg": "Testing with missing empty fields fix",
        "imgs": [], # sending empty array
        "video": "",
        "pdf": path,
        "audio": "",
        "channel": SENDER_CHANNEL
    }
    
    url = f"{BASE_URL}/wapp/campaign/save?apikey={API_KEY}"
    print(f"[*] Posting to Campaign Save...")
    resp = session.post(url, data=data) # sending as application/x-www-form-urlencoded
    
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text}")

if __name__ == "__main__":
    test_fresh_upload_and_post()
