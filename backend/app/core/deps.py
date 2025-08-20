# backend/app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from jose import jwt, JWTError

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import TokenData
from app.services import user_service
from app.core.security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None: raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.email == token_data.email).options(selectinload(User.employee))
    )
    user = result.scalar_one_or_none()
    
    if user is None: raise credentials_exception
    return user

async def get_current_user_with_employee(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user ensuring they have an employee relationship"""
    if not current_user.employee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with an employee profile"
        )
    return current_user