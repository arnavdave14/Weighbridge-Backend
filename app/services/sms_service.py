import os
import requests
import logging
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY")
BASE_URL = os.getenv("BASE_URL")

async def send_sms_fast2sms(
    receipt_id: int, 
    phone: str, 
    vehicle: str, 
    weight: float, 
    token: str
) -> Dict[str, Any]:
    """
    Sends SMS using Fast2SMS Bulk V2 API.
    Format: 🚛 Vehicle: {vehicle} ⚖️ Net Weight: {weight} kg 👉 Bill: {BASE_URL}/r/{share_token}
    """
    if not FAST2SMS_API_KEY or FAST2SMS_API_KEY == "your_fast2sms_api_key_here":
        logger.error(f"[RT-{receipt_id}] SMS Failed: FAST2SMS_API_KEY not configured.")
        return {"status": "failed", "reason": "API Key missing"}

    if not phone:
        logger.warning(f"[RT-{receipt_id}] SMS Skipped: Phone is empty.")
        return {"status": "skipped"}

    # Fast2SMS prefers 10-digit numbers for domestic India
    clean_phone = "".join(filter(str.isdigit, phone))
    if len(clean_phone) > 10:
        clean_phone = clean_phone[-10:]

    # Fast2SMS often rejects some emojis; simplified message if needed
    message = (
        f"Vehicle: {vehicle}\n"
        f"Weight: {weight:.2f} kg\n"
        f"Bill: {BASE_URL}/r/{token}"
    )

    url = "https://www.fast2sms.com/dev/bulkV2"
    
    # Fast2SMS standard parameters
    payload = {
        "route": "q", # 'q' is for Quick SMS route
        "message": message,
        "language": "english",
        "flash": 0,
        "numbers": clean_phone,
    }
    
    headers = {
        "authorization": FAST2SMS_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            response = await asyncio.to_thread(
                requests.post, url, data=payload, headers=headers, timeout=10
            )
            
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("return"):
                    logger.info(f"[RT-{receipt_id}] ✅ Fast2SMS success on attempt {attempt}")
                    return {"status": "success", "data": res_json}
                else:
                    logger.error(f"[RT-{receipt_id}] Fast2SMS error response: {res_json}")
            else:
                logger.error(f"[RT-{receipt_id}] Fast2SMS HTTP Error {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"[RT-{receipt_id}] Fast2SMS exception on attempt {attempt}: {str(e)}")
            
        if attempt < max_retries:
            await asyncio.sleep(2)

    return {"status": "failed"}
