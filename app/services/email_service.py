import logging
import asyncio
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.services.email_provider import SMTPProvider

logger = logging.getLogger(__name__)

# Single instance for system-wide emails (fallback)
def get_system_provider() -> SMTPProvider:
    return SMTPProvider(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        user=settings.SMTP_USER,
        password=settings.SMTP_PASS
    )

async def send_otp_email(email: str, otp: str) -> Dict[str, Any]:
    """Sends a 6-digit OTP to the admin email for login verification."""
    if not email or not settings.SMTP_USER:
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

    provider = get_system_provider()
    return await provider.send_email(
        to_email=email,
        subject=subject,
        body=body,
        from_email=settings.EMAILS_FROM_EMAIL,
        from_name=settings.EMAILS_FROM_NAME
    )

async def send_email_receipt(
    receipt_id: int, 
    email: str, 
    vehicle: str, 
    weight: float, 
    token: str
) -> Dict[str, Any]:
    """Sends email containing the receipt link."""
    if not email or not settings.SMTP_USER:
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

    provider = get_system_provider()
    res = await provider.send_email(
        to_email=email,
        subject=subject,
        body=body,
        from_email=settings.EMAILS_FROM_EMAIL,
        from_name=settings.EMAILS_FROM_NAME
    )
    if res["status"] == "success":
        logger.info(f"[RT-{receipt_id}] ✅ Email sent successfully to {email}")
    else:
        logger.error(f"[RT-{receipt_id}] Email failed: {res.get('reason')}")
    return res

async def send_license_email(
    email: str, 
    key_data: Dict[str, Any], 
    app_name: str, 
    sender_name: str = None,
    providerOverride: Optional[Any] = None # For multi-tenant injection
) -> Dict[str, Any]:
    """Sends a license email with raw subject and body provided by the frontend."""
    if not email or not key_data:
        return {"status": "skipped"}

    subject = key_data.get('subject')
    body = key_data.get('body')

    if not subject or not body:
        logger.error(f"License Email to {email} skipped: Missing subject or body.")
        return {"status": "failed", "reason": "missing_content"}

    # Determine provider: Override (Company) or System
    provider = providerOverride or get_system_provider()
    from_name = sender_name or settings.EMAILS_FROM_NAME
    from_email = settings.EMAILS_FROM_EMAIL
    
    # If using an override provider, we might want to check its specific from_email/name,
    # but the provider.send_email handles that if we pass None.
    
    return await provider.send_email(
        to_email=email,
        subject=subject,
        body=body,
        from_email=from_email,
        from_name=from_name
    )
