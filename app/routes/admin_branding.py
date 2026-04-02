from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.config.settings import settings
import os
import uuid
from typing import Dict

router = APIRouter(prefix="/admin/upload", tags=["Admin Branding"])

async def _handle_upload(file: UploadFile, subfolder: str) -> str:
    """Helper to validate, save and return the public URL for an uploaded image."""
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WEBP, and GIF images are allowed.")

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    
    # Save to dynamic subfolder
    save_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    file_path = os.path.join(save_dir, unique_filename)

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    return f"{settings.BASE_URL}/static/uploads/{subfolder}/{unique_filename}"

@router.post("/logo")
async def upload_logo(file: UploadFile = File(...)) -> Dict[str, str]:
    """Upload a company logo."""
    url = await _handle_upload(file, "logos")
    return {"url": url}

@router.post("/signup")
async def upload_signup_image(file: UploadFile = File(...)) -> Dict[str, str]:
    """Upload a sign-up illustration image."""
    url = await _handle_upload(file, "signups")
    return {"url": url}
