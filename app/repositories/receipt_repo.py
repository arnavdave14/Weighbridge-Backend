from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models.models import Receipt
from typing import List, Optional

class ReceiptRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, receipt_id: int) -> Optional[Receipt]:
        return await db.get(Receipt, receipt_id)

    @staticmethod
    async def get_by_machine_and_local_id(db: AsyncSession, machine_id: str, local_id: int) -> Optional[Receipt]:
        stmt = select(Receipt).where(
            and_(Receipt.machine_id == machine_id, Receipt.local_id == local_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_share_token(db: AsyncSession, share_token: str) -> Optional[Receipt]:
        result = await db.execute(select(Receipt).where(Receipt.share_token == share_token))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Receipt]:
        result = await db.execute(select(Receipt).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create(db: AsyncSession, receipt: Receipt) -> Receipt:
        db.add(receipt)
        return receipt

    @staticmethod
    async def update_status(db: AsyncSession, receipt_id: int, status: str) -> Optional[Receipt]:
        receipt = await db.get(Receipt, receipt_id)
        if receipt:
            receipt.whatsapp_status = status
        return receipt
