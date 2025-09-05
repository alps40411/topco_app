# backend/app/services/user_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from typing import Optional

from app.models.user import User
from app.core.security import verify_password


async def authenticate_user(
    db: AsyncSession, 
    username: str, 
    password: Optional[str] = None,
    skip_password_check: bool = False
) -> Optional[User]:
    """
    認證用戶
    Args:
        db: 資料庫 session
        username: 用戶名（可能是 email 或 empno）
        password: 密碼
        skip_password_check: 是否跳過密碼檢查（用於暫時的無密碼登入）
    """
    # 嘗試用 email 查找
    result = await db.execute(
        select(User).where(User.email == username).options(selectinload(User.employee))
    )
    user = result.scalar_one_or_none()
    
    # 如果用 email 找不到，嘗試用 empno 查找
    if not user:
        result = await db.execute(
            select(User).where(User.employee.has(empno=username)).options(selectinload(User.employee))
        )
        user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    # 如果跳過密碼檢查，直接返回用戶
    if skip_password_check:
        return user
    
    # 正常的密碼驗證
    if password and verify_password(password, user.hashed_password):
        return user
    
    return None


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """根據用戶 ID 獲取用戶"""
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.employee))
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """根據 email 獲取用戶"""
    result = await db.execute(
        select(User).where(User.email == email).options(selectinload(User.employee))
    )
    return result.scalar_one_or_none()


async def get_user_by_empno(db: AsyncSession, empno: str) -> Optional[User]:
    """根據員工編號獲取用戶"""
    result = await db.execute(
        select(User).where(User.employee.has(empno=empno)).options(selectinload(User.employee))
    )
    return result.scalar_one_or_none()

