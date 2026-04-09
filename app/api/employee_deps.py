"""
Employee JWT dependency — FastAPI dependency for device-facing endpoints.

This is SEPARATE from the admin JWT system (admin_deps.py).
  - Admin JWT: issued by /admin/auth/login, for the web Admin Panel
  - Employee JWT: issued by /employee/login, for the Flutter device app

JWT payload structure:
  {
    "sub":      "<employee-uuid>",
    "username": "john",
    "key_id":   "WB-XXXX-XXXX-XXXX",
    "role":     "operator",
    "exp":      <unix timestamp>
  }

Security guarantees:
  1. Token is validated cryptographically (HS256, shared SECRET_KEY)
  2. Employee row is fetched live → deactivated users are blocked immediately
  3. Tenant key_id is embedded in the token for fast cross-tenant checks
"""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SECRET_KEY, ALGORITHM
from app.database.db_manager import get_db
from app.models.employee_model import Employee
from app.repositories.employee_repo import EmployeeRepository

logger = logging.getLogger(__name__)

# ── Token settings ─────────────────────────────────────────────
EMPLOYEE_TOKEN_EXPIRE_HOURS = 24

# Using HTTPBearer (not OAuth2PasswordBearer) so Swagger shows a clean
# "Authorize" button distinct from the admin token flow.
employee_bearer = HTTPBearer(auto_error=False)


def create_employee_token(employee: Employee) -> str:
    """
    Mint a signed JWT for an authenticated employee.
    Called exclusively by the /employee/login endpoint.
    """
    from datetime import datetime, timezone
    from jose import jwt as jose_jwt

    expire = datetime.now(timezone.utc) + timedelta(hours=EMPLOYEE_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub":      employee.id,
        "username": employee.username,
        "key_id":   employee.key_id,
        "role":     employee.role,
        "exp":      expire,
    }
    return jose_jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_employee(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(employee_bearer),
    db: AsyncSession = Depends(get_db),
) -> Employee:
    """
    FastAPI dependency — validates employee Bearer token.

    Usage:
        @router.post("/receipts")
        async def create_receipt(
            employee: Employee = Depends(get_current_employee),
            ...
        ):

    Raises 401 for:
      - Missing / malformed / expired token
      - Employee no longer active (deactivated after token issue)
    """
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired employee token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        employee_id: str = payload.get("sub")
        if not employee_id:
            raise auth_error
    except JWTError as exc:
        logger.warning("[EmployeeAuth] JWT decode failed: %s", exc)
        raise auth_error

    # Live DB check — ensures deactivated employees are blocked immediately
    employee = await EmployeeRepository.get_by_id(db, employee_id)
    if not employee or not employee.is_active:
        logger.warning("[EmployeeAuth] Employee %s not found or inactive", employee_id)
        raise auth_error

    return employee


async def get_current_employee_strict(
    employee: Employee = Depends(get_current_employee),
) -> Employee:
    """
    Same as get_current_employee but additionally enforces active status
    at the dependency level (double guard for high-security routes).
    """
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your supervisor.",
        )
    return employee
