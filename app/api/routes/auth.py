from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from app.db.session import get_db
from app.models.models import User
from app.core import security
from app.schemas.schemas import Token

router = APIRouter()

@router.post("/token", response_model=Token, tags=["Auth"])
async def login_for_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Standard OAuth2 password flow.
    In real app, we check hashed password.
    For this demo, we can just allow it or keep it as placeholder.
    """
    # Simple hardcoded user for initialization or search in DB
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    # If no user exists, create a default one for first-time setup (Demo purpose)
    if not user and form_data.username == "admin@weighbridge.com" and form_data.password == "admin123":
        user = User(
            email="admin@weighbridge.com",
            hashed_password=security.get_password_hash("admin123"),
            is_superuser=True
        )
        db.add(user)
        await db.commit()
    elif not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
