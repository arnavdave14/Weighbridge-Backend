from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Machine
from typing import Optional
from datetime import datetime, timezone

class MachineRepository:
    @staticmethod
    async def get_by_machine_id(db: AsyncSession, machine_id: str) -> Optional[Machine]:
        stmt = select(Machine).where(Machine.machine_id == machine_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, machine: Machine) -> Machine:
        db.add(machine)
        return machine

    @staticmethod
    async def update_sync_time(db: AsyncSession, machine_id: str):
        machine = await MachineRepository.get_by_machine_id(db, machine_id)
        if machine:
            machine.last_sync_at = datetime.now(timezone.utc)
        return machine
