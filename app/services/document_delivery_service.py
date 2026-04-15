import logging
import uuid
import time
from typing import Dict, Any, Optional

from app.database.postgres import remote_session
from app.models.admin_models import DocumentDeliveryLog, ActivationKey
from app.services.notification_service import NotificationService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

class DocumentDeliveryService:
    @staticmethod
    async def process_and_deliver_document(
        key_id: str,
        document_type: str,
        document_name: str,
        document_bytes: Optional[bytes],
        metadata_json: Dict[str, Any],
        target_email: Optional[str] = None,
        target_whatsapp: Optional[str] = None,
        app_name: str = "Weighbridge Admin"
    ) -> bool:
        """
        Orchestrates storage, delivery, and logging of a business document.
        Does NOT expose sensitive data.
        """
        
        # 1. Gather Key/Tenant Details
        company_name = "Unknown"
        whatsapp_sender_channel = None
        email_sender_name = None
        provider_type = "none" # Default until matched
        delivery_channel = "none"

        if target_email and target_whatsapp: delivery_channel = "both"
        elif target_email: delivery_channel = "email"
        elif target_whatsapp: delivery_channel = "whatsapp"
        
        async with remote_session() as db:
            if key_id:
                from sqlalchemy import select
                stmt = select(ActivationKey).where(ActivationKey.id == uuid.UUID(key_id))
                result = await db.execute(stmt)
                key = result.scalars().first()
                if key:
                    company_name = key.company_name
                    whatsapp_sender_channel = key.whatsapp_sender_channel
                    email_sender_name = key.email_sender or key.company_name
                    # Basic heuristic to check if key SMTP is likely to be used
                    if key.smtp_enabled and key.smtp_status == "VALID":
                        provider_type = "key"

        # 2. Upload Document (if bytes provided)
        file_url = None
        attachments = []
        if document_bytes:
            file_url = await StorageService.upload_document(
                file_bytes=document_bytes, 
                filename=document_name, 
                company_id=str(key_id), 
                doc_type=document_type
            )
            if file_url:
                attachments.append({
                    "file_name": document_name,
                    "file_url": file_url,
                    "file_type": document_name.split(".")[-1] if "." in document_name else "unknown"
                })
        
        # In case we didn't upload bytes but we want a link to act as the primary document
        view_link = file_url
        if not file_url and metadata_json.get("share_token"):
            from app.config.settings import settings
            view_link = f"{settings.BASE_URL}/r/{metadata_json.get('share_token')}"
            attachments.append({
                "file_name": "Receipt Link",
                "file_url": view_link,
                "file_type": "link"
            })

        # 3. Create initial LOG entry
        async with remote_session() as db:
            log_entry = DocumentDeliveryLog(
                key_id=uuid.UUID(key_id) if key_id else None,
                company_name=company_name,
                document_type=document_type,
                document_name=document_name,
                delivery_channel=delivery_channel,
                email_used=target_email,
                whatsapp_channel=whatsapp_sender_channel,
                sender_name=email_sender_name,
                provider_type=provider_type,
                status="PENDING",
                metadata_json=metadata_json,
                attachments=attachments
            )
            db.add(log_entry)
            await db.commit()
            await db.refresh(log_entry)
            log_id = log_entry.id

        # 4. Trigger Delivery via NotificationService
        # Prepare key_data for NotificationService
        key_data = {
            "id": key_id,
            "company_name": company_name,
            "email": target_email,
            "whatsapp_number": target_whatsapp,
            "subject": f"New {document_type} from {company_name}",
            # Use view_link in body
            "body": f"Please find the attached {document_type} '{document_name}'.\n\nView Document: {view_link or 'N/A'}",
            "message": f"New {document_type} received from *{company_name}*.\nView it here: {view_link or 'N/A'}"
        }
        
        start_time = time.time()
        final_status = "SUCCESS"
        error_msg = None
        
        skip_channels = []
        if not target_email: skip_channels.append("email")
        if not target_whatsapp: skip_channels.append("whatsapp")

        try:
            # We call the async orchestrator. Since sync workers might call this, we must ensure loop is handled.
            # Assuming caller is in async context (process_sync_queue is async)
            delivery_res = await NotificationService._notify_license_generation_async_orchestrated(
                key_data=key_data,
                app_name=app_name,
                skip_channels=skip_channels
            )
            
            # evaluate overall success: SUCCESS if all active channels succeeded
            # If any active channel failed -> FAILED
            # If all were skipped -> SKIPPED
            if len(delivery_res["failed"]) > 0:
                final_status = "FAILED"
                error_msg = str(delivery_res["failed"])
            elif len(delivery_res["success"]) == 0 and len(delivery_res["skipped"]) > 0:
                final_status = "SKIPPED"
                error_msg = "No tenant configuration available for requested channels."
            elif len(delivery_res["success"]) == 0:
                # Should not happen if a channel was requested and not skipped by input
                final_status = "SKIPPED"
        except Exception as e:
            final_status = "FAILED"
            error_msg = str(e)
            
        latency = time.time() - start_time

        # 5. Update LOG entry
        async with remote_session() as db:
            from sqlalchemy import select
            log_entry = (await db.execute(select(DocumentDeliveryLog).where(DocumentDeliveryLog.id == log_id))).scalars().first()
            if log_entry:
                log_entry.status = final_status
                log_entry.error_message = error_msg
                log_entry.latency = latency
                db.add(log_entry)
                await db.commit()
                
        return final_status == "SUCCESS"
