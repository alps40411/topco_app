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

@router.get("/has-subordinates")
async def check_has_subordinates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """檢查當前用戶是否有下屬 - 從 supervisor.py 遷移過來"""
    try:
        if not current_user.employee:
            return {"has_subordinates": False}

        # 從 JPS 查詢是否有下屬
        subordinates_sql = text("""
            SELECT COUNT(*) as subordinate_count
            FROM jps.groupfoodchn
            WHERE supervisor = :empno AND cocode = 'A'
        """)

        result = db.execute(subordinates_sql, {"empno": current_user.employee.empno})
        row = result.fetchone()

        has_subordinates = row[0] > 0 if row else False
        return {"has_subordinates": has_subordinates}

    except Exception as e:
        logger.error(f"Error checking subordinates: {str(e)}")
        return {"has_subordinates": False}


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

@router.get("/subordinates")
async def get_subordinates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得下屬列表"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 查詢下屬列表
        subordinates_sql = text("""
            SELECT g.empno, e.empnamec, e.cocode, e.deptno, d.deptnamec
            FROM jps.groupfoodchn g
            LEFT JOIN jps.dcd003$master e ON g.empno = e.empno AND g.cocode = e.cocode
            LEFT JOIN jps.dcd002$master d ON e.cocode = d.cocode AND e.deptno = d.deptno
            WHERE g.supervisor = :empno AND g.cocode = 'A'
            ORDER BY e.empno
        """)
        
        result = db.execute(subordinates_sql, {"empno": current_user.employee.empno})
        
        subordinates = []
        for row in result.fetchall():
            subordinates.append({
                "empno": row[0],
                "empnamec": row[1] or "",
                "cocode": row[2] or "",
                "deptno": row[3] or "",
                "deptnamec": row[4] or ""
            })
        
        return {
            "success": True,
            "data": subordinates,
            "total": len(subordinates)
        }
        
    except Exception as e:
        logger.error(f"Error getting subordinates: {str(e)}")
        raise HTTPException(status_code=500, detail="取得下屬列表失敗")

@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得用戶權限"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 檢查是否為主管
        has_subordinates = current_user.is_supervisor
        
        # 檢查編輯權限（暫時返回允許的狀態）
        permissions = {
            "can_view_reports": True,
            "can_create_reports": True,
            "can_edit_reports": True,
            "can_delete_reports": True,
            "can_submit_reports": True,
            "can_review_reports": has_subordinates,
            "can_view_subordinate_reports": has_subordinates,
            "is_supervisor": has_subordinates
        }
        
        return {
            "success": True,
            "data": permissions
        }
        
    except Exception as e:
        logger.error(f"Error getting user permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="取得用戶權限失敗")