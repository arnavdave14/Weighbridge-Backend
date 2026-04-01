from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.core import User, UserActivation, SoftwareVersion, Tenant
from typing import Optional, Tuple

class UserRepository:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_activation_by_key(db: AsyncSession, key: str) -> Optional[Tuple[UserActivation, SoftwareVersion, Tenant]]:
        stmt = (
            select(UserActivation, SoftwareVersion, Tenant)
            .join(SoftwareVersion, UserActivation.version_id == SoftwareVersion.id)
            .join(Tenant, UserActivation.tenant_id == Tenant.id)
            .where(UserActivation.activation_key == key)
            .where(UserActivation.is_active == True)
        )
        result = await db.execute(stmt)
        return result.first()
