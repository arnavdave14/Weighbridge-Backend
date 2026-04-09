"""
EmployeeRepository — all database operations for the Employee model.

Read from: SQLite (device context) or PostgreSQL (admin context).
The repo is DB-agnostic — the caller passes the correct session.

Tenant isolation is enforced at the service layer, not here.
The repo is pure data access — no business logic, no auth decisions.
"""
import uuid
from typing import Optional, List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee_model import Employee


class EmployeeRepository:

    # ──────────────────────────────────────────────────────────
    # Lookups
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_by_id(db: AsyncSession, employee_id: str) -> Optional[Employee]:
        """Fetch by primary key (UUID string)."""
        result = await db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[Employee]:
        """Fetch by exact username (case-sensitive)."""
        result = await db.execute(
            select(Employee).where(Employee.username == username)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[Employee]:
        """Fetch by email address (case-sensitive)."""
        result = await db.execute(
            select(Employee).where(Employee.email == email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_login(
        db: AsyncSession, login: str
    ) -> Optional[Employee]:
        """
        Lookup by username OR email — supports either login style.
        Returns the first active match.
        This is the method used during authentication.
        """
        result = await db.execute(
            select(Employee).where(
                and_(
                    or_(Employee.username == login, Employee.email == login),
                    Employee.is_active == True,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_key(
        db: AsyncSession,
        key_id: str,
        active_only: bool = True,
    ) -> List[Employee]:
        """
        List all employees belonging to a tenant (key_id).
        Used by admin panel and device-side employee listing.
        """
        stmt = select(Employee).where(Employee.key_id == key_id)
        if active_only:
            stmt = stmt.where(Employee.is_active == True)
        stmt = stmt.order_by(Employee.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    # ──────────────────────────────────────────────────────────
    # Uniqueness guards (used before create)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def username_exists(db: AsyncSession, username: str) -> bool:
        result = await db.execute(
            select(Employee.id).where(Employee.username == username)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def email_exists(db: AsyncSession, email: str) -> bool:
        result = await db.execute(
            select(Employee.id).where(Employee.email == email)
        )
        return result.scalar_one_or_none() is not None

    # ──────────────────────────────────────────────────────────
    # Write operations
    # ──────────────────────────────────────────────────────────

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        name: str,
        username: str,
        password_hash: str,
        key_id: str,
        email: Optional[str] = None,
        role: str = "operator",
    ) -> Employee:
        """
        Create and persist a new employee.
        Caller is responsible for:
          - Hashing the password BEFORE calling this method
          - Verifying username/email uniqueness BEFORE calling this method
          - Ensuring key_id belongs to a valid ActivationKey
        """
        emp = Employee(
            id=str(uuid.uuid4()),
            name=name,
            username=username,
            email=email,
            password_hash=password_hash,
            key_id=key_id,
            role=role,
            is_active=True,
        )
        db.add(emp)
        return emp

    @staticmethod
    async def deactivate(db: AsyncSession, employee_id: str) -> Optional[Employee]:
        """Soft-delete: set is_active = False."""
        emp = await EmployeeRepository.get_by_id(db, employee_id)
        if emp:
            emp.is_active = False
        return emp
