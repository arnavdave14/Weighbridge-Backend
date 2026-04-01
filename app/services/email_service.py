import os
import smtplib
import logging
import asyncio
from typing import Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# SMTP Config
SMTP_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("EMAIL_PORT", "587"))
SMTP_USER = os.getenv("EMAIL_USER", "")
SMTP_PASS = os.getenv("EMAIL_PASS", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)

async def send_email_receipt(
    receipt_id: int, 
    email: str, 
    vehicle: str, 
    weight: float, 
    token: str
) -> Dict[str, Any]:
    """
    Sends email containing the receipt link.
    """
    if not email or not SMTP_USER or not SMTP_PASS:
        logger.warning(f"[RT-{receipt_id}] Email skipped: Config or Target missing.")
        return {"status": "skipped"}

    subject = f"Receipt for Vehicle {vehicle}"
    body = (
        f"Hello,\n\n"
        f"Your weighment receipt is ready:\n"
        f"Vehicle: {vehicle}\n"
        f"Net Weight: {weight:.2f} kg\n\n"
        f"View Bill: {os.getenv('BASE_URL')}/r/{token}\n\n"
        f"Regards,\n"
        f"Weighbridge Team"
    )

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Running sync smtplib in a thread
        await asyncio.to_thread(_send_sync, msg, email)
        logger.info(f"[RT-{receipt_id}] ✅ Email sent successfully to {email}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"[RT-{receipt_id}] Email failed: {str(e)}")
        return {"status": "failed", "reason": str(e)}

def _send_sync(msg, email):
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
