import asyncio
import os
import sys
import requests
import json
import time

sys.path.append(os.getcwd())
from app.config.settings import settings

API_KEY = settings.DIGITALSMS_API_KEY
BASE_URL = "https://api.digitalsms.net"
TARGET_MOBILE = "918962380001"
SENDER_CHANNEL = "919407184405:30"
PDF_PATH = "uploads/20260416/24225/17testreceipt1776345050.pdf" 

def test_ajax_replica():
    # 1. URL encoded payload explicitly matching the jQuery ajax logic
    data = {
        "apikey": API_KEY, # add apikey since we don't use session here
        "campname": f"Ajax_Test_{int(time.time())}",
        "mobile": TARGET_MOBILE,
        "msg": "Testing exact AJAX payload replication",
        "imgs": [], # sending empty array, often ignored or serialized as imgs[]
        "video": "",
        "pdf": PDF_PATH,
        "audio": "",
        "channel": SENDER_CHANNEL # adding this just in case backend expects it
    }
    
    url = f"{BASE_URL}/wapp/campaign/save"
    print(f"[*] Posting URL Encoded to {url}")
    resp = requests.post(url, data=data)
    print(f"Status: {resp.status_code} | Body: {resp.text}")
    print("-" * 40)
    
    # 2. Try again passing apikey in query string, and data in body
    print(f"[*] Posting URL Encoded with API key in query params")
    resp2 = requests.post(f"{url}?apikey={API_KEY}", data=data)
    print(f"Status: {resp2.status_code} | Body: {resp2.text}")
    print("-" * 40)

if __name__ == "__main__":
    test_ajax_replica()
