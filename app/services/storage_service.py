import os
import uuid
import logging
import asyncio
from typing import Optional
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)

# To switch to a real provider, set CLOUD_STORAGE_PROVIDER in .env to "s3".
CLOUD_STORAGE_PROVIDER = os.getenv("CLOUD_STORAGE_PROVIDER", "mock")

class StorageService:
    """
    Unified storage service for business documents.
    Phase 1: Local file system logic.
    Phase 2: S3 integration (with Boto3).
    """

    @staticmethod
    async def upload_document(file_bytes: bytes, filename: str, company_id: str, doc_type: str = "receipt") -> Optional[str]:
        """
        Uploads a document (PDF, PNG) and returns a URL.
        """
        # Limit to 5MB for documents
        if len(file_bytes) > 5 * 1024 * 1024:
            logger.error(f"Document '{filename}' exceeds 5MB limit ({len(file_bytes)} bytes)")
            return None

        if CLOUD_STORAGE_PROVIDER == "mock":
            return await StorageService._mock_upload(file_bytes, filename, company_id, doc_type)
        else:
            logger.warning(f"Storage provider '{CLOUD_STORAGE_PROVIDER}' not fully implemented. Falling back to mock.")
            return await StorageService._mock_upload(file_bytes, filename, company_id, doc_type)

    @staticmethod
    async def _mock_upload(file_bytes: bytes, filename: str, company_id: str, doc_type: str) -> Optional[str]:
        """
        Saves the file to local static uploads directory structure.
        """
        try:
            def _write():
                # Directory structure: static/uploads/documents/{company_id}/{doc_type}/
                base_dir = Path(settings.UPLOAD_DIR) / "documents" / company_id / doc_type
                base_dir.mkdir(parents=True, exist_ok=True)
                
                unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
                filepath = base_dir / unique_name
                
                with open(filepath, "wb") as f:
                    f.write(file_bytes)
                
                return unique_name

            unique_name = await asyncio.to_thread(_write)
            
            # Generate the local URL
            url = f"{settings.BASE_URL}/uploads/documents/{company_id}/{doc_type}/{unique_name}"
            logger.info(f"[StorageService] Saved document {unique_name} for company {company_id}")
            return url

        except Exception as e:
            logger.error(f"[StorageService] Failed to save document '{filename}': {e}")
            return None
