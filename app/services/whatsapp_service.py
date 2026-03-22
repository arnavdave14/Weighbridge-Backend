import os
import requests
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.future import select
from app.db.session import async_session
from app.models.models import Receipt

load_dotenv()

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_service")

GUPSHUP_API_KEY = os.getenv("GUPSHUP_API_KEY")
GUPSHUP_SOURCE = os.getenv("GUPSHUP_SOURCE")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

async def send_whatsapp_message(
    receipt_id: int, 
    phone: str, 
    vehicle: str, 
    weight: float, 
    token: str
) -> Dict[str, Any]:
    """
    Upgraded WhatsApp notification service with retries, status tracking, and logging.
    """
    
    # Validation: Phone must not be empty and must include country code (e.g., 91)
    if not phone:
        logger.warning(f"[RT-{receipt_id}] Skipping send: Mobile number is empty.")
        await _update_receipt_status(receipt_id, "failed")
        return {"status": "skipped", "reason": "Empty phone"}

    clean_phone = "".join(filter(str.isdigit, phone))
    
    # Requirement: Must start with country code (industry standard e.g., 91)
    # We check if length is sufficient and it starts with 91 (or other specified country code)
    if not (clean_phone.startswith("91") and len(clean_phone) >= 12):
        logger.warning(f"[RT-{receipt_id}] Invalid phone format: {phone}. Missing or incorrect country code (91).")
        await _update_receipt_status(receipt_id, "failed")
        return {"status": "failed", "reason": "Invalid phone format (must start with 91)"}

    message = (
        f"🚛 Vehicle: {vehicle or 'N/A'}\n"
        f"⚖️ Net Weight: {weight:.2f} kg\n\n"
        f"👉 View Bill:\n"
        f"{BASE_URL}/r/{token}"
    )

    url = "https://api.gupshup.io/wa/api/v1/msg"
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/x-www-form-urlencoded",
        "apikey": GUPSHUP_API_KEY,
    }
    payload = {
        "channel": "whatsapp",
        "source": GUPSHUP_SOURCE,
        "destination": clean_phone,
        "message": message,
        "src.name": GUPSHUP_SOURCE,
    }

    # Retry mechanism: 3 attempts with 2s delay
    max_retries = 3
    retry_delay = 2
    
    logger.info(f"[RT-{receipt_id}] Starting WhatsApp process for {clean_phone} (Token: {token})")

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"[RT-{receipt_id}] Attempt {attempt} for {clean_phone}")
            # Running sync requests in a thread to keep async friendly
            response = await asyncio.to_thread(
                requests.post, url, headers=headers, data=payload, timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"[RT-{receipt_id}] ✅ Success on attempt {attempt}")
                await _update_receipt_status(receipt_id, "sent")
                return response.json()
            
            logger.error(f"[RT-{receipt_id}] Attempt {attempt} failed: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"[RT-{receipt_id}] Attempt {attempt} error: {str(e)}")
        
        if attempt < max_retries:
            await asyncio.sleep(retry_delay)

    # Final Failure
    logger.critical(f"[RT-{receipt_id}] ❌ All attempts failed for {clean_phone}")
    await _update_receipt_status(receipt_id, "failed")
    return {"status": "failed", "reason": "Max retries reached or connection error"}

async def _update_receipt_status(receipt_id: int, status: str):
    """
    Internal helper to update the database status using a fresh async session.
    """
    try:
        async with async_session() as session:
            stmt = select(Receipt).where(Receipt.id == receipt_id)
            result = await session.execute(stmt)
            receipt = result.scalar_one_or_none()
            if receipt:
                receipt.whatsapp_status = status
                await session.commit()
                logger.debug(f"[RT-{receipt_id}] Database status updated to: {status}")
    except Exception as db_err:
        logger.error(f"Failed to update database status for Receipt {receipt_id}: {db_err}")
