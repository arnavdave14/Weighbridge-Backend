from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Receipt

class ReceiptService:
    @staticmethod
    async def get_by_share_token(db: AsyncSession, share_token: str) -> Receipt:
        """
        Publicly accessible receipt retrieval via random share_token.
        """
        result = await db.execute(select(Receipt).where(Receipt.share_token == share_token))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_receipts(db: AsyncSession, skip: int = 0, limit: int = 100):
        result = await db.execute(select(Receipt).offset(skip).limit(limit))
        return result.scalars().all()
