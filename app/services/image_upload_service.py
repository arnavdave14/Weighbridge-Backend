"""
image_upload_service.py
-----------------------
Handles uploading raw image bytes to cloud storage and returning a public URL.

PHASE 1 (Current):  Mock implementation — saves to /tmp/ and returns a local URL.
PHASE 2 (Upgrade):  Replace `upload_image_to_cloud()` with a real S3/Cloudinary/Firebase call.
                    No other file needs to change.
"""

import os
import uuid
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

# -- Configuration -----------------------------------------------------------
# To switch to a real provider, set CLOUD_STORAGE_PROVIDER in .env to "s3" or "cloudinary".
# Leave empty to use the mock (Phase 1).
CLOUD_STORAGE_PROVIDER = os.getenv("CLOUD_STORAGE_PROVIDER", "mock")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

# Temp storage dir for mock uploads
MOCK_UPLOAD_DIR = "/tmp/weighbridge_uploads"


# -- Core Upload Function -----------------------------------------------------

async def upload_image_to_cloud(image_bytes: bytes, filename: str) -> Optional[str]:
    """
    Upload raw image bytes to cloud storage and return the public URL.

    Args:
        image_bytes: Raw bytes of the image (never Base64).
        filename:    Suggested filename (e.g. "RST_1001_img_0.jpg")

    Returns:
        Public URL string on success, None on failure.
    """
    if CLOUD_STORAGE_PROVIDER == "mock":
        return await _mock_upload(image_bytes, filename)
    
    # Future: add elif for "s3", "cloudinary", "firebase" etc.
    logger.error(f"Unknown CLOUD_STORAGE_PROVIDER: '{CLOUD_STORAGE_PROVIDER}'")
    return None


# -- Mock Implementation (Phase 1) -------------------------------------------

async def _mock_upload(image_bytes: bytes, filename: str) -> Optional[str]:
    """
    Saves the image to /tmp/ and returns a localhost URL.
    This simulates cloud behaviour without an external dependency.
    Replace this function with a real provider in Phase 2.
    """
    try:
        def _write():
            os.makedirs(MOCK_UPLOAD_DIR, exist_ok=True)
            # Use a unique name to avoid collisions on retry
            unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
            filepath = os.path.join(MOCK_UPLOAD_DIR, unique_name)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            return unique_name

        unique_name = await asyncio.to_thread(_write)
        url = f"{BASE_URL}/uploads/{unique_name}"
        logger.info(f"[MOCK UPLOAD] Saved {len(image_bytes)} bytes → {url}")
        return url

    except Exception as e:
        logger.error(f"[MOCK UPLOAD] Failed to save image '{filename}': {e}")
        return None
