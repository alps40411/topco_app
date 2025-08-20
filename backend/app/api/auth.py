# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.core.database import get_db
from app.schemas.user import LoginResponse, User as UserSchema
from app.services import user_service
from app.core.security import create_access_token, verify_password

router = APIRouter(tags=["Authentication"])

@router.post("/token", response_model=LoginResponse)
async def login_for_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = await user_service.get_user_by_empno(db, empno=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee ID or password",
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {
        "token": {"access_token": access_token, "token_type": "bearer"},
        "user": UserSchema.from_orm(user)
    }