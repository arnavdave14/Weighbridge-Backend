"""
Employee model — registered in Base (SQLite + PostgreSQL).

Design decisions:
  - Lives in `Base`, NOT `AdminBase`, so it syncs to both databases and
    is available for offline device authentication.
  - `id` is a UUID stored as a plain String — SQLite has no native UUID column.
  - `username` and `email` are both UNIQUE + indexed to support login by either.
  - `key_id` mirrors Machine.key_id (ActivationKey.token) as a plain String —
    the same cross-DB-safe pattern used across this codebase.
  - `role` is a low-cost future hook for RBAC (operator / supervisor / admin).
  - No cross-database foreign keys — fully SQLite compatible.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.sql import func
from app.database.base import Base


class Employee(Base):
    __tablename__ = "employees"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    name = Column(String, nullable=False)

    # Both username and email support login — both are unique and indexed.
    # Email is nullable for field operators who may not have a corporate email.
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True, index=True)

    # ── Security ──────────────────────────────────────────────
    # Password is ALWAYS stored hashed via bcrypt. Never plain text.
    password_hash = Column(String, nullable=False)

    # ── Tenant linkage ────────────────────────────────────────
    # Mirrors Machine.key_id — stores ActivationKey.token as a plain String.
    # No FK constraint → SQLite compatible.
    # Every employee belongs to exactly one tenant.
    key_id = Column(String, nullable=False, index=True)

    # ── Role / Status ──────────────────────────────────────────
    role = Column(String, default="operator", nullable=False)
    # Supported roles: operator, supervisor
    # Extend freely — no schema migration needed (String column).

    is_active = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Composite index for fast tenant-scoped listing ────────
    __table_args__ = (
        Index("ix_employee_key_id_active", "key_id", "is_active"),
    )

    def __repr__(self):
        return f"<Employee username={self.username!r} key_id={self.key_id!r} role={self.role!r}>"
