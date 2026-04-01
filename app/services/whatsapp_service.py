import requests
import logging
import asyncio
from typing import Dict, Any, Optional
from app.config.settings import settings

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_service")

# Digitalsms API Configuration from settings
DIGITALSMS_API_KEY = settings.DIGITALSMS_API_KEY
DIGITALSMS_ENDPOINT = "https://api.digitalsms.net/wapp/api/send"
DIGITALSMS_BASE = "https://api.digitalsms.net"
DIGITALSMS_PORTAL_USER = settings.DIGITALSMS_PORTAL_USER
DIGITALSMS_PORTAL_PASS = settings.DIGITALSMS_PORTAL_PASS
BASE_URL = "http://localhost:8000" # fallback if needed, or add to settings


# Shared session object (reused across requests to maintain JSESSIONID)
_digitalsms_session: Optional[requests.Session] = None

def _get_digitalsms_session() -> requests.Session:
    """Return or create a requests.Session for Digitalsms portal."""
    global _digitalsms_session
    if _digitalsms_session is None:
        _digitalsms_session = requests.Session()
    return _digitalsms_session

def _login_digitalsms() -> bool:
    """Login to Digitalsms portal to get a JSESSIONID cookie."""
    if not DIGITALSMS_PORTAL_USER or not DIGITALSMS_PORTAL_PASS:
        logger.error("Digitalsms portal credentials not set in .env (DIGITALSMS_PORTAL_USER / DIGITALSMS_PORTAL_PASS)")
        return False
    try:
        session = _get_digitalsms_session()
        login_data = {
            "username": DIGITALSMS_PORTAL_USER,
            "password": DIGITALSMS_PORTAL_PASS,
        }
        resp = session.post(
            f"{DIGITALSMS_BASE}/login",
            data=login_data,
            timeout=15,
            allow_redirects=False
        )
        if "JSESSIONID" in session.cookies:
            logger.info(f"Digitalsms login successful.")
            return True
        else:
            logger.error(f"Digitalsms login failed. Response: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Digitalsms login exception: {e}")
        return False

async def send_whatsapp(
    phone: str, 
    receipt_id: int = 0,
    message: Optional[str] = None,
    pdf_content: Optional[bytes] = None,
    filename: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Unified WhatsApp sending function for Digitalsms API.
    Pure communication layer — NO database logic.
    """
    if not phone:
        logger.warning(f"[RT-{receipt_id}] Skipping WA: Mobile number is empty.")
        return {"status": "skipped", "message": "Phone number is empty"}

    clean_phone = "".join(filter(str.isdigit, phone))
    if not clean_phone.startswith("91") and len(clean_phone) == 10:
        clean_phone = "91" + clean_phone

    params = {
        "apikey": DIGITALSMS_API_KEY,
        "mobile": clean_phone,
        "msg": message or (f"Receipt {filename}" if filename else "Weighbridge Receipt"),
    }

    if pdf_content and len(pdf_content) > 2 * 1024 * 1024:
        logger.error(f"[RT-{receipt_id}] PDF size too large: {len(pdf_content)} bytes (max 2MB)")
        return {"status": "failed", "message": "PDF size exceeds 2MB limit"}

    max_retries = 3
    retry_delay = 2
    
    for attempt in range(1, max_retries + 1):
        try:
            if pdf_content:
                import time
                base_fname = filename or f"Receipt_{receipt_id}.pdf"
                name_part, ext_part = (base_fname.rsplit(".", 1) if "." in base_fname else (base_fname, "pdf"))
                fname = f"{name_part}_{int(time.time())}.{ext_part}"
                
                logged_in = await asyncio.to_thread(_login_digitalsms)
                if not logged_in:
                    continue
                
                session = _get_digitalsms_session()
                upload_resp = await asyncio.to_thread(
                    session.post,
                    f"{DIGITALSMS_BASE}/wapp/upload/media",
                    files={"file": (fname, pdf_content, "application/pdf")},
                    timeout=30
                )
                
                if upload_resp.status_code != 200 or not upload_resp.text.strip().startswith("uploads/"):
                    _digitalsms_session = None
                    continue
                
                uploaded_path = upload_resp.text.strip()
                campaign_data = {
                    "campname": f"Receipt_{receipt_id}_{fname}",
                    "mobile": clean_phone,
                    "msg": message or (f"Receipt {filename}" if filename else "Weighbridge Receipt"),
                    "pdf": uploaded_path,
                }
                
                response = await asyncio.to_thread(
                    session.post,
                    f"{DIGITALSMS_BASE}/wapp/campaign/save",
                    data=campaign_data,
                    timeout=15
                )
            else:
                response = await asyncio.to_thread(
                    requests.get,
                    DIGITALSMS_ENDPOINT,
                    params=params,
                    timeout=15
                )

            if response.status_code == 200:
                logger.info(f"[RT-{receipt_id}] ✅ WhatsApp sent successfully!")
                return {"status": "success", "response": response.text}
            
            logger.error(f"[RT-{receipt_id}] WhatsApp Attempt {attempt} failed: {response.status_code}")
        except Exception as e:
            logger.error(f"[RT-{receipt_id}] WhatsApp Error: {str(e)}")
        
        if attempt < max_retries:
            await asyncio.sleep(retry_delay)

    return {"status": "failed", "message": "Failed after retries"}

async def send_whatsapp_message(receipt_id: int, phone: str, **kwargs) -> Dict[str, Any]:
    msg = kwargs.get('message')
    if not msg:
        slip_no = kwargs.get('slip_no', 'N/A')
        vehicle = kwargs.get('vehicle', 'N/A')
        gross = kwargs.get('gross_weight', 0.0)
        tare = kwargs.get('tare_weight', 0.0)
        net = kwargs.get('net_weight', gross - tare)
        date = kwargs.get('date', 'N/A')
        token = kwargs.get('token', '')
        msg = (
            f"📄 *Weighbridge Slip*\n\n"
            f"Slip No.: {slip_no}\n"
            f"Vehicle No.: {vehicle}\n"
            f"Gross Weight: {gross:.2f} kg\n"
            f"Tare Weight: {tare:.2f} kg\n"
            f"Net Weight: {net:.2f} kg\n"
            f"Date: {date}\n\n"
            f"👉 View/Download PDF: {BASE_URL}/r/{token}"
        )
    return await send_whatsapp(phone=phone, receipt_id=receipt_id, message=msg)

async def send_whatsapp_pdf(phone: str, pdf_content: bytes, filename: str, receipt_id: int = 0, caption: Optional[str] = None) -> Dict[str, Any]:
    return await send_whatsapp(phone=phone, receipt_id=receipt_id, message=caption, pdf_content=pdf_content, filename=filename)

