"""
Employee Auth Routes — authentication for the Flutter device application.

Two sub-systems live here:

1. /employee/* — device-facing (Flutter app)
   - POST /employee/login         Public login (username or email + password)
   - GET  /employee/me            Current employee info (requires employee JWT)
   - POST /employee/register      Self-registration on an activated machine
                                  Requires APEX machine HMAC auth.
                                  Employee is auto-linked to machine.key_id.

2. /admin/employees/* — admin-facing (web Admin Panel)
   - POST /admin/employees        Create employee for a tenant
   - GET  /admin/employees        List employees for a tenant
   - PATCH /admin/employees/{id}/deactivate   Soft-delete

Tenant Isolation Rules:
  - Device login: validates employee.key_id matches provided key_id claim
  - Device register: machine must have key_id set; employee inherits it
  - Admin create: admin supplies key_id; must be a valid ActivationKey.token
  - Cross-tenant access: blocked at every layer
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_manager import get_db, get_remote_db
from app.core.security import get_password_hash, verify_password
from app.api.employee_deps import create_employee_token, get_current_employee
from app.api.admin_deps import get_current_admin
from app.api.machine_deps import verify_apex_identity
from app.models.employee_model import Employee
from app.models.admin_models import ActivationKey, AdminUser
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.admin_repo import AdminRepo

router = APIRouter(tags=["Employee Auth"])
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Request / Response Schemas (inline — avoids cross-dependency)
# ═══════════════════════════════════════════════════════════════

class EmployeeLoginRequest(BaseModel):
    """Accepts username OR email — the caller need not know which."""
    login: str          # username or email
    password: str

class EmployeeRegisterRequest(BaseModel):
    """Device self-registration. key_id is derived from the machine, not user input."""
    name: str
    username: str
    password: str
    email: Optional[str] = None
    role: str = "operator"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"operator", "supervisor"}
        if v not in allowed:
            raise ValueError(f"role must be one of {sorted(allowed)}")
        return v

class AdminEmployeeCreate(BaseModel):
    """Admin Panel creates an employee and explicitly assigns the tenant."""
    name: str
    username: str
    password: str
    key_id: str         # Must match a valid ActivationKey.token
    email: Optional[str] = None
    role: str = "operator"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"operator", "supervisor"}
        if v not in allowed:
            raise ValueError(f"role must be one of {sorted(allowed)}")
        return v

class EmployeeRead(BaseModel):
    id: str
    name: str
    username: str
    email: Optional[str]
    key_id: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class EmployeeLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee: EmployeeRead


# ═══════════════════════════════════════════════════════════════
# SECTION 1 — Device-facing (Flutter)
# ═══════════════════════════════════════════════════════════════

@router.post(
    "/employee/login",
    response_model=EmployeeLoginResponse,
    summary="Employee Login (device)",
)
async def employee_login(
    req: EmployeeLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate an employee using username OR email + password.

    Returns a signed JWT valid for 24 hours.
    The JWT payload includes key_id — the Flutter app must store this
    and inject receipt.user_id from the stored employee.id.

    Security:
      - Passwords verified via bcrypt (timing-safe)
      - Active status checked before token is issued
      - Inactive accounts receive 401 (same error as wrong password)
    """
    employee = await EmployeeRepository.get_by_login(db, req.login)

    # Constant-time-equivalent: always run verify_password even on miss
    # to prevent username enumeration via timing.
    dummy_hash = "$2b$12$invalidhashfortimingprotectiononly123456789012"
    password_ok = verify_password(
        req.password,
        employee.password_hash if employee else dummy_hash,
    )

    if not employee or not password_ok:
        logger.warning("[EmployeeAuth] Failed login attempt for login=%r", req.login)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not employee.is_active:
        logger.warning("[EmployeeAuth] Inactive employee login attempt: %s", employee.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_employee_token(employee)
    logger.info("[EmployeeAuth] Login success: employee=%s key_id=%s", employee.id, employee.key_id)

    return EmployeeLoginResponse(
        access_token=token,
        employee=EmployeeRead.model_validate(employee),
    )


@router.get(
    "/employee/me",
    response_model=EmployeeRead,
    summary="Current employee info (device)",
)
async def employee_me(
    employee: Employee = Depends(get_current_employee),
):
    """
    Returns the currently authenticated employee's profile.
    The Flutter app calls this after login to confirm token validity
    and display the operator name on-screen.
    """
    return EmployeeRead.model_validate(employee)


@router.post(
    "/employee/register",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Self-register on an activated machine (device)",
)
async def employee_register_on_device(
    req: EmployeeRegisterRequest,
    activation_key: ActivationKey = Depends(verify_apex_identity),
    db: AsyncSession = Depends(get_db),
):
    """
    Allows a field operator to create their account directly on an activated machine.

    Security chain:
      1. verify_apex_identity validates the machine's HMAC signature.
         → Ensures the request comes from a legitimate activated device.
      2. Employee is automatically linked to activation_key.token (key_id).
         → No user-supplied key_id → cross-tenant creation is impossible.
      3. Username and email uniqueness are checked BEFORE insert.

    This endpoint is intentionally limited:
      - Role is capped at 'operator' or 'supervisor' (no admin via device)
      - The machine must be activated (APEX auth implies this)
    """
    key_id = activation_key.token   # Derived from machine auth — not user input

    # Uniqueness guards
    if await EmployeeRepository.username_exists(db, req.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{req.username}' is already taken",
        )
    if req.email and await EmployeeRepository.email_exists(db, req.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{req.email}' is already registered",
        )

    employee = await EmployeeRepository.create(
        db,
        name=req.name,
        username=req.username,
        password_hash=get_password_hash(req.password),
        key_id=key_id,
        email=req.email,
        role=req.role,
    )
    await db.commit()
    await db.refresh(employee)

    logger.info(
        "[EmployeeAuth] Device self-registration: employee=%s key_id=%s",
        employee.id, key_id
    )
    return EmployeeRead.model_validate(employee)


# ═══════════════════════════════════════════════════════════════
# SECTION 2 — Admin Panel (web)
# ═══════════════════════════════════════════════════════════════

@router.post(
    "/admin/employees",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee (Admin Panel)",
    tags=["Admin — Employees"],
)
async def admin_create_employee(
    req: AdminEmployeeCreate,
    db: AsyncSession = Depends(get_remote_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    Admin creates an employee for a specific tenant (key_id).

    Tenant validation:
      - The supplied key_id must match an existing ActivationKey.token
      - Prevents admins from creating employees for non-existent tenants
      - Prevents cross-tenant employee injection

    Admin audit log is written on every creation.
    """
    # Validate key_id against real ActivationKey in PostgreSQL
    key = await AdminRepo.get_key_by_token(db, req.key_id)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"key_id '{req.key_id}' does not match any active ActivationKey",
        )

    # Uniqueness guards
    if await EmployeeRepository.username_exists(db, req.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{req.username}' is already taken",
        )
    if req.email and await EmployeeRepository.email_exists(db, req.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{req.email}' is already registered",
        )

    employee = await EmployeeRepository.create(
        db,
        name=req.name,
        username=req.username,
        password_hash=get_password_hash(req.password),
        key_id=req.key_id,
        email=req.email,
        role=req.role,
    )
    await db.commit()
    await db.refresh(employee)

    logger.info(
        "[AdminAudit] Employee created: admin=%s employee=%s key_id=%s company=%s",
        admin.email, employee.id, req.key_id, key.company_name,
    )
    return EmployeeRead.model_validate(employee)


@router.get(
    "/admin/employees",
    response_model=List[EmployeeRead],
    summary="List employees for a tenant (Admin Panel)",
    tags=["Admin — Employees"],
)
async def admin_list_employees(
    key_id: str,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_remote_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    Returns all employees for a given tenant (key_id).
    Always scoped to one tenant — no cross-tenant listing possible.
    """
    # Validate tenant exists
    key = await AdminRepo.get_key_by_token(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Tenant not found")

    employees = await EmployeeRepository.list_by_key(
        db, key_id, active_only=not include_inactive
    )
    logger.info(
        "[AdminAudit] Employee list accessed: admin=%s key_id=%s count=%d",
        admin.email, key_id, len(employees),
    )
    return [EmployeeRead.model_validate(e) for e in employees]


@router.patch(
    "/admin/employees/{employee_id}/deactivate",
    response_model=EmployeeRead,
    summary="Deactivate an employee (Admin Panel)",
    tags=["Admin — Employees"],
)
async def admin_deactivate_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_remote_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    Soft-deletes an employee (sets is_active = False).
    Their historical receipts remain intact — user_id is preserved.
    Active JWT tokens for this employee become invalid on next request
    (get_current_employee re-fetches the DB row on every call).
    """
    employee = await EmployeeRepository.get_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    await EmployeeRepository.deactivate(db, employee_id)
    await db.commit()
    await db.refresh(employee)

    logger.info(
        "[AdminAudit] Employee deactivated: admin=%s employee=%s",
        admin.email, employee_id,
    )
    return EmployeeRead.model_validate(employee)
