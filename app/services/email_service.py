import smtplib
import logging
import asyncio
from typing import Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.settings import settings

logger = logging.getLogger(__name__)

async def send_otp_email(email: str, otp: str) -> Dict[str, Any]:
    """
    Sends a 6-digit OTP to the admin email for login verification.
    """
    if not email or not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning(f"OTP Email skipped for {email}: SMTP Config or Target missing.")
        return {"status": "skipped"}

    subject = f"{otp} is your Admin Panel verification code"
    body = (
        f"Hello,\n\n"
        f"You are attempting to log in to the Weighbridge Admin Panel.\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code will expire in 5 minutes. If you did not request this, please ignore this email.\n\n"
        f"Regards,\n"
        f"{settings.EMAILS_FROM_NAME}"
    )

    msg = MIMEMultipart()
    msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        await asyncio.to_thread(_send_sync, msg)
        logger.info(f"✅ OTP Email sent successfully to {email}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"OTP Email failed for {email}: {str(e)}")
        return {"status": "failed", "reason": str(e)}

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
    if not email or not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning(f"[RT-{receipt_id}] Email skipped: Config or Target missing.")
        return {"status": "skipped"}

    subject = f"Receipt for Vehicle {vehicle}"
    body = (
        f"Hello,\n\n"
        f"Your weighment receipt is ready:\n"
        f"Vehicle: {vehicle}\n"
        f"Net Weight: {weight:.2f} kg\n\n"
        f"View Bill: {settings.BASE_URL}/r/{token}\n\n"
        f"Regards,\n"
        f"Weighbridge Team"
    )

    msg = MIMEMultipart()
    msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg['To'] = email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Running sync smtplib in a thread
        await asyncio.to_thread(_send_sync, msg)
        logger.info(f"[RT-{receipt_id}] ✅ Email sent successfully to {email}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"[RT-{receipt_id}] Email failed: {str(e)}")
        return {"status": "failed", "reason": str(e)}

def _send_sync(msg):
    # Added 15 second timeout for production safety
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.send_message(msg)

async def send_license_email(email: str, key_data: Dict[str, Any], app_name: str) -> Dict[str, Any]:
    """
    Sends a license email with raw subject and body provided by the frontend.
    """
    if not email or not key_data:
        logger.warning(f"License Email skipped: Config or Target missing.")
        return {}

    subject = key_data.get('subject')
    body = key_data.get('body')

    if not subject or not body:
        logger.error(f"License Email to {email} skipped: Missing subject or body.")
        return {}

    msg = MIMEMultipart()
    msg['From'] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg['To'] = email
    msg['Subject'] = subject
    msg['Reply-To'] = settings.EMAILS_FROM_EMAIL
    msg['X-Mailer'] = "Weighbridge-Production-Mailer"
    
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Running sync smtplib in a thread
        await asyncio.to_thread(_send_sync, msg)
        logger.info(f"✅ License Email sent successfully to {email}")
        return {}
    except Exception as e:
        logger.error(f"License Email failed for {email}: {str(e)}")
        return {"status": "failed", "reason": str(e)}
