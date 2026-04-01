from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from app.schemas.bhel_api import BHELRequest, BHELResponse
from app.services.bhel_service import BHELService

router = APIRouter()

@router.post("/bhel/sync-dev", response_model=BHELResponse)
async def sync_to_bhel_dev(data: BHELRequest):
    """
    Test BHEL sync on Dev environment.
    """
    result = await BHELService.post_to_bhel(data, environment="dev")
    if not result:
        raise HTTPException(status_code=500, detail="BHEL Dev Sync failed")
    return result

@router.post("/bhel/sync-prod", response_model=BHELResponse)
async def sync_to_bhel_prod(data: BHELRequest):
    """
    Test BHEL sync on Prod environment.
    """
    result = await BHELService.post_to_bhel(data, environment="prod")
    if not result:
        raise HTTPException(status_code=500, detail="BHEL Prod Sync failed")
    return result
