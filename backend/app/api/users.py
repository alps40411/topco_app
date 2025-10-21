# backend/app/api/users.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import logging

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..schemas.user import User

router = APIRouter(tags=["Users"])
logger = logging.getLogger(__name__)

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """取得用戶個人資料"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        return {
            "success": True,
            "data": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email,
                "is_supervisor": current_user.is_supervisor,
                "employee": {
                    "empno": current_user.employee.empno,
                    "empnamec": current_user.employee.empnamec,
                    "cocode": current_user.employee.cocode,
                    "dutyscript": current_user.employee.dutyscript,
                    "deptabbv": current_user.employee.deptabbv
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="取得用戶資料失敗")

