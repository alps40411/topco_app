# backend/app/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.employee import Employee
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

async def get_user_by_email(db: AsyncSession, *, email: str) -> Optional[User]:
    query = select(User).where(User.email == email).options(selectinload(User.employee))
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, *, obj_in: UserCreate) -> User:
    hashed_password = get_password_hash(obj_in.password)
    
    db_user = User(
        email=obj_in.email,
        name=obj_in.name,
        hashed_password=hashed_password,
        is_supervisor=obj_in.is_supervisor
    )
    
    db_employee = Employee(
        name=obj_in.name,
        department=obj_in.department,
        user=db_user
    )
    
    db.add(db_user)
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_user)
    return db_user