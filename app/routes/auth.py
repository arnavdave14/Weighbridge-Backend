from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import timedelta

from app.database.postgres import remote_session
from app.database.db_manager import get_db
from app.repositories.user_repo import UserRepository
from app.core import security

router = APIRouter()

class ActivationRequest(BaseModel):
    activation_key: str

class ActivationResponse(BaseModel):
    success: bool
    tenant_name: str
    version_name: str
    features: dict

@router.post("/activate", response_model=ActivationResponse, tags=["Auth"])
async def activate_software(
    req: ActivationRequest
):
    """
    Verifies an activation key and maps it distinctly to a Tenant + Version, 
    loading their respective contexts.
    """
    if not remote_session:
        raise HTTPException(status_code=503, detail="Remote Database not configured.")
        
    async with remote_session() as session:
        # Extract Tenant and Version using the key map via repository
        row = await UserRepository.get_activation_by_key(session, req.activation_key)
        
        if not row:
            raise HTTPException(status_code=401, detail="Invalid or inactive activation key.")
            
        activation, version, tenant = row
        
        return ActivationResponse(
            success=True,
            tenant_name=tenant.name,
            version_name=version.name,
            features=version.features
        )

@router.post("/token", tags=["Auth"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Standard OAuth2 password flow. Requires username and password.
    """
    user = await UserRepository.get_by_email(db, form_data.username)
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        # Note: mapping 'email' to 'sub' as typical in this codebase
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

