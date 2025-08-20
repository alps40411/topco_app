# backend/app/api/users.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import User, UserCreate
from app.services import user_service

router = APIRouter(tags=["Users"])

@router.post("/", response_model=User, status_code=201)
async def create_user_endpoint(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
):
    user = await user_service.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists.",
        )
    new_user = await user_service.create_user(db, obj_in=user_in)
    return new_user


@router.post("/", response_model=User, status_code=201)
async def create_user_endpoint(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
):
    user = await user_service.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists.",
        )
    new_user = await user_service.create_user(db, obj_in=user_in)
    return new_user