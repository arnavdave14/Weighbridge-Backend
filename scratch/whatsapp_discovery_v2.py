import asyncio
import os
import sys
import logging
import requests
import json
import time

# Ensure 'app' is in path
sys.path.append(os.getcwd())

from app.config.settings import settings

# Configure verbose logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
logger = logging.getLogger("wa_discovery_v2")

API_KEY = settings.DIGITALSMS_API_KEY
PORTAL_USER = settings.DIGITALSMS_PORTAL_USER
PORTAL_PASS = settings.DIGITALSMS_PORTAL_PASS
BASE_URL = "https://api.digitalsms.net"
TARGET_MOBILE = "918962380001"
SENDER_CHANNEL = "919407184405:30"

async def run_discovery_v2():
    print(f"\n🚀 PHASE 2 DISCOVERY: ISOLATING DEVICE KEY & SESSION AUTH")
    print("=" * 60)

    # login to get session for attempts that might need it
    session = requests.Session()
    login_resp = session.post(f"{BASE_URL}/login", data={"username": PORTAL_USER, "password": PORTAL_PASS}, allow_redirects=False)
    print(f"[*] Login Status: {login_resp.status_code} | Cookies: {'JSESSIONID' in session.cookies}")

    # --- Variation D: Isolation of Device Identifier Key ---
    # We try different possible parameter names for the :30 channel
    device_keys = ["vid", "instance", "device", "deviceId", "channel"]
    for key in device_keys:
        await attempt_variation(
            name=f"Var D: GET with '{key}' key",
            url=f"{BASE_URL}/wapp/api/send",
            params={
                "apikey": API_KEY,
                "mobile": TARGET_MOBILE,
                "msg": f"Testing Device Key: {key}",
                key: SENDER_CHANNEL
            },
            method="GET"
        )
        await asyncio.sleep(2)

    # --- Variation E: Session-based Campaign POST (No apikey in body) ---
    # Some dashboard APIs explicitly forbid apikey if session is logged in
    await attempt_variation(
        name="Var E: Session POST (Dashboard Imitation)",
        url=f"{BASE_URL}/wapp/campaign/save",
        data={
            "campname": f"Disc_E_{int(time.time())}",
            "mobile": TARGET_MOBILE,
            "msg": "Discovery Attempt E: Session POST",
            "pdf": "uploads/20260416/24225/17testreceipt1776345050.pdf", # use a known valid path
            "channel": SENDER_CHANNEL
        },
        session=session,
        method="POST"
    )

    # --- Variation F: GET with FULL Media URL ---
    # Verifying if the GET endpoint supports media via full URL
    await attempt_variation(
        name="Var F: GET with Full mediaurl",
        url=f"{BASE_URL}/wapp/api/send",
        params={
            "apikey": API_KEY,
            "mobile": TARGET_MOBILE,
            "msg": "Discovery Attempt F: Full Media URL",
            "mediaurl": f"{BASE_URL}/uploads/20260416/24225/17testreceipt1776345050.pdf",
            "channel": SENDER_CHANNEL
        },
        method="GET"
    )

    print("\n🏁 PHASE 2 COMPLETE.")

async def attempt_variation(name: str, url: str, params: dict = None, data: dict = None, files: dict = None, session=None, method="GET"):
    print(f"\n👉 {name}")
    req_lib = session if session else requests
    
    try:
        if method == "GET":
            resp = req_lib.get(url, params=params, timeout=15)
        else:
            resp = req_lib.post(url, data=data, files=files, timeout=15)
            
        print(f"   Status: {resp.status_code}")
        print(f"   Body:   {resp.text[:200]}...") # truncate for brevity
        
        if resp.status_code == 200 and '"status":"success"' in resp.text.lower():
            print(f"   🌟 SUCCESS Body returned.")
    except Exception as e:
        print(f"   Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_discovery_v2())
