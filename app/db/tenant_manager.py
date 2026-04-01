from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from dataclasses import dataclass

from app.database.sqlite import local_session
from app.database.postgres import remote_session
from app.models.core import UserActivation

@dataclass
class AuthContext:
    session: AsyncSession
    tenant_id: int
    version_id: int
    user_id: int

async def get_tenant_remote_context(x_activation_key: Optional[str] = Header(None)) -> AuthContext:
    """
    FastAPI dependency that returns an AuthContext strictly enforcing Single DB Multi-Tenancy.
    It reads the 'X-Activation-Key' header, authenticates the activation, and provides the 
    tenant_id and version_id required to filter all subsequent ORM queries.
    """
    if not remote_session:
        raise HTTPException(status_code=503, detail="Remote Database not configured.")
    
    if not x_activation_key:
        raise HTTPException(status_code=401, detail="X-Activation-Key header missing.")

    async with remote_session() as session:
        # Lookup activation key safely to extract IDs
        stmt = (
            select(UserActivation)
            .where(UserActivation.activation_key == x_activation_key)
            .where(UserActivation.is_active == True)
        )
        result = await session.execute(stmt)
        activation = result.scalar_one_or_none()
        
        if not activation:
            raise HTTPException(status_code=401, detail="Invalid or inactive activation key.")
            
        yield AuthContext(
            session=session,
            tenant_id=activation.tenant_id,
            version_id=activation.version_id,
            user_id=activation.user_id
        )
