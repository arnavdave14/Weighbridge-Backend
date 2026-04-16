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
    image_content: Optional[bytes] = None,
    filename: Optional[str] = None,
    image_filename: Optional[str] = None,
    sender_channel: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Unified WhatsApp sending function for Digitalsms API.
    Pure communication layer — NO database logic.
    """
    if not phone:
        logger.warning(f"[RT-{receipt_id}] Skipping WA: Mobile number is empty.")
        return {"status": "skipped", "message": "Phone number is empty"}

    # --- GAP-7 FIX: Strict Channel Enforcement ---
    if not sender_channel:
        logger.error(f"[RT-{receipt_id}] ❌ CRITICAL: Attempted to send WhatsApp without mandatory sender_channel. Aborting.")
        return {"status": "failed", "message": "Missing mandatory sender_channel ID."}
    
    logger.info(f"Sending WhatsApp via channel: {sender_channel}")

    clean_phone = "".join(filter(str.isdigit, phone))
    if not clean_phone.startswith("91") and len(clean_phone) == 10:
        clean_phone = "91" + clean_phone

    params = {
        "apikey": DIGITALSMS_API_KEY,
        "mobile": clean_phone,
        "msg": message or (f"Receipt {filename}" if filename else "Weighbridge Receipt"),
        "channel": sender_channel # Always propagate channel
    }

    if pdf_content and len(pdf_content) > 2 * 1024 * 1024:
        logger.error(f"[RT-{receipt_id}] PDF size too large: {len(pdf_content)} bytes (max 2MB)")
        return {"status": "failed", "message": "PDF size exceeds 2MB limit"}

    max_retries = 3
    retry_delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            if pdf_content or image_content:
                import time
                logged_in = await asyncio.to_thread(_login_digitalsms)
                if not logged_in:
                    continue
                
                session = _get_digitalsms_session()
                uploaded_pdf_path = ""
                uploaded_img_paths = []

                # 1a. Upload PDF if present
                if pdf_content:
                    base_fname = filename or f"Receipt_{receipt_id}.pdf"
                    name_part, ext_part = (base_fname.rsplit(".", 1) if "." in base_fname else (base_fname, "pdf"))
                    fname = f"{name_part}_{int(time.time())}.{ext_part}"
                    
                    upload_resp = await asyncio.to_thread(
                        session.post,
                        f"{DIGITALSMS_BASE}/wapp/upload/media",
                        files={"file": (fname, pdf_content, "application/pdf")},
                        timeout=30
                    )
                    if upload_resp.status_code == 200 and upload_resp.text.strip().startswith("uploads/"):
                        uploaded_pdf_path = upload_resp.text.strip()
                        logger.debug(f"[WA] PDF uploaded: {uploaded_pdf_path}")
                    else:
                        logger.error(f"[WA] PDF upload failed: {upload_resp.text}")
                        continue

                # 1b. Upload Image if present
                if image_content:
                    img_fname = image_filename or f"Preview_{receipt_id}.png"
                    img_name, img_ext = (img_fname.rsplit(".", 1) if "." in img_fname else (img_fname, "png"))
                    if_name = f"{img_name}_{int(time.time())}.{img_ext}"
                    
                    img_resp = await asyncio.to_thread(
                        session.post,
                        f"{DIGITALSMS_BASE}/wapp/upload/media",
                        files={"file": (if_name, image_content, "image/png")},
                        timeout=30
                    )
                    if img_resp.status_code == 200 and img_resp.text.strip().startswith("uploads/"):
                        uploaded_img_paths.append(img_resp.text.strip())
                        logger.debug(f"[WA] Image uploaded: {uploaded_img_paths[-1]}")
                    else:
                        logger.error(f"[WA] Image upload failed: {img_resp.text}")
                        continue
                
                # 2. Submit via campaign with ALL keys
                campaign_url = f"{DIGITALSMS_BASE}/wapp/campaign/save"
                
                campaign_data = {
                    "apikey": DIGITALSMS_API_KEY,
                    "campname": f"Receipt_{receipt_id}_{int(time.time())}",
                    "mobile": clean_phone,
                    "msg": message or "Weighbridge Receipt",
                    "pdf": uploaded_pdf_path,
                    "imgs": uploaded_img_paths, # List handled as multiple 'imgs' keys by requests
                    "video": "",
                    "audio": "",
                    "channel": sender_channel
                }
                
                logger.info(f"[WA] Executing Rich Campaign POST to {campaign_url} | Channel: {sender_channel} | Media: PDF={bool(pdf_content)} IMG={bool(image_content)}")
                
                response = await asyncio.to_thread(
                    session.post,
                    campaign_url,
                    data=campaign_data,
                    timeout=30
                )
            else:
                # Text-only flow uses simple GET
                logger.info(f"[WA] Executing Text GET to {DIGITALSMS_ENDPOINT} | Channel: {sender_channel}")
                response = await asyncio.to_thread(
                    requests.get,
                    DIGITALSMS_ENDPOINT,
                    params=params,
                    timeout=15
                )

            # Verbose Diagnostic Audit
            resp_body = response.text
            req_headers = response.request.headers
            
            logger.info(f"[WA] Request Content-Type: {req_headers.get('Content-Type')}")
            logger.info(f"[WA] Response Status: {response.status_code}")
            logger.debug(f"[WA] Full Response Body: {resp_body}")

            if response.status_code == 200:
                # Provider might return 200 but include error in JSON
                if '"status":"success"' in resp_body.lower():
                    logger.info(f"[RT-{receipt_id}] ✅ WhatsApp confirmed SUCCESS by provider.")
                    return {"status": "success", "response": resp_body}
                else:
                    logger.error(f"[RT-{receipt_id}] ❌ WhatsApp rejected by provider logic: {resp_body}")
            else:
                logger.error(f"[RT-{receipt_id}] ❌ WhatsApp HTTP Failure: {response.status_code} | {resp_body}")
        except Exception as e:
            logger.error(f"[RT-{receipt_id}] WhatsApp Error: {str(e)}")
        
        if attempt < max_retries:
            await asyncio.sleep(retry_delay)

    return {"status": "failed", "message": "Failed after retries"}

async def send_whatsapp_message(receipt_id: int, phone: str, sender_channel: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    msg = kwargs.get('message')
    if not msg:
        logger.error(f"[RT-{receipt_id}] Message missing from frontend")
        return {}
    
    return await send_whatsapp(phone=phone, receipt_id=receipt_id, message=msg, sender_channel=sender_channel)

async def send_whatsapp_pdf(phone: str, pdf_content: bytes, filename: str, receipt_id: int = 0, caption: Optional[str] = None, sender_channel: Optional[str] = None) -> Dict[str, Any]:
    return await send_whatsapp(
        phone=phone, 
        receipt_id=receipt_id, 
        message=caption, 
        pdf_content=pdf_content, 
        filename=filename,
        sender_channel=sender_channel
    )

async def send_license_whatsapp(phone: str, key_data: Dict[str, Any], app_name: str, sender_channel: Optional[str] = None) -> Dict[str, Any]:
    """
    Sends a WhatsApp message containing the content provided in key_data['message'].
    """
    msg = key_data.get('message')
    if not msg:
        logger.error(f"License WhatsApp skipped: No message content provided.")
        return {}

    return await send_whatsapp(phone=phone, message=msg, sender_channel=sender_channel)
