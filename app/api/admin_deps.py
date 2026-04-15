from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SECRET_KEY, ALGORITHM
from app.database.db_manager import get_remote_db
from app.repositories.admin_repo import AdminRepo

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# This uses a simple Bearer Token field in Swagger - much easier for manual testing
admin_http_bearer = HTTPBearer()

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(admin_http_bearer),
    db: AsyncSession = Depends(get_remote_db)
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    session_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or logged in from another device",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        is_admin: bool = payload.get("root_admin")
        token_session_id: str = payload.get("session_id")
        
        if email is None or not is_admin or not token_session_id:
            raise credentials_exception
            
        # Verify session_id against DB
        admin = await AdminRepo.get_admin_by_email(db, email)
        if not admin or admin.session_id != token_session_id:
            raise session_exception
            
        return admin
    except JWTError:
        raise credentials_exception
