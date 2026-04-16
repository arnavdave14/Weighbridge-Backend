from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import asyncio
import logging

logger = logging.getLogger(__name__)

class BaseEmailProvider(ABC):
    """
    Abstract interface for email delivery.
    Allows swapping SMTP for AWS SES or other providers.
    """
    @abstractmethod
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        html_body: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> Dict[str, Any]:
        pass

class SMTPProvider(BaseEmailProvider):
    """
    Concrete implementation for SMTP delivery.
    Supports per-company credentials.
    """
    def __init__(
        self, 
        host: str, 
        port: int, 
        user: str, 
        password: str,
        timeout: int = 15
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.timeout = timeout

    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        html_body: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> Dict[str, Any]:
        # Top-level container
        msg = MIMEMultipart('mixed')
        
        # Use provided from_email/name or fallback to the SMTP user
        display_from = f"{from_name} <{from_email}>" if from_name and from_email else from_email or self.user
        
        msg['From'] = display_from
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # --- 1. Body Part (Alternative: Plain vs HTML) ---
        body_part = MIMEMultipart('alternative')
        body_part.attach(MIMEText(body, 'plain'))
        if html_body:
            body_part.attach(MIMEText(html_body, 'html'))
        msg.attach(body_part)
        
        # --- 2. Attachments Part ---
        if attachments:
            total_size = sum(len(a.get("content", b"")) for a in attachments)
            if total_size > 5 * 1024 * 1024: # 5MB limit
                logger.error(f"Email to {to_email} aborted: Attachments exceed 5MB ({total_size} bytes)")
                return {"status": "failed", "reason": "attachment_limit_exceeded"}

            for att in attachments:
                filename = att.get("filename", "attachment")
                content = att.get("content")
                if not content: continue
                
                # Dynamic MIME Type Detection
                mime_type = att.get("mime_type")
                if not mime_type:
                    mime_type, _ = mimetypes.guess_type(filename)
                if not mime_type:
                    mime_type = "application/octet-stream"
                
                maintype, subtype = mime_type.split("/", 1)
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                msg.attach(part)

        try:
            # Running synchronous smtplib in a thread pool to avoid blocking the event loop
            await asyncio.to_thread(self._send_sync, msg)
            return {"status": "success"}
        except smtplib.SMTPAuthenticationError:
            return {"status": "failed", "reason": "authentication_failed"}
        except smtplib.SMTPConnectError:
            return {"status": "failed", "reason": "connection_failed"}
        except Exception as e:
            logger.error(f"SMTP generic failure: {str(e)}")
            return {"status": "failed", "reason": str(e)}

    def _send_sync(self, msg: MIMEMultipart):
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
