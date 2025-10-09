# backend/app/api/dates.py
"""
日期管理 API - 處理日期範圍和日報編號
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..models.user import User
from ..services.date_service import DateService

router = APIRouter(prefix="/dates", tags=["Dates"])
logger = logging.getLogger(__name__)


@router.get("/range")
async def get_date_range(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    取得用戶可填寫日報的日期範圍
    整合了日期查詢和寫入狀態檢查（取代了 writing-status）

    返回：
    - data: 日期列表（包含可寫狀態）
    - current_report_date: 當前預設日期
    - allowed: 全局是否允許編輯
    - message: 全局提示訊息
    - has_other_writable_dates: 是否還有其他可填寫日期
    """
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        cocode = current_user.employee.cocode

        if not cocode:
            raise HTTPException(status_code=400, detail="用戶沒有公司別資訊")

        # 使用 DateService 獲取日期範圍和狀態
        result = DateService.get_date_range_with_status(
            db=db,
            empno=empno,
            cocode=cocode
        )

        return result

    except Exception as e:
        logger.error(f"Error getting date range: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得日期範圍失敗: {str(e)}")


@router.get("/next-daily-no")
async def get_next_daily_no(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得下一個可用的日報編號"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or 'A'

        # 使用 DateService 獲取下一個編號
        next_daily_no = DateService.get_next_daily_no(
            db=db,
            empno=empno,
            cocode=cocode
        )

        return {
            "success": True,
            "next_daily_no": next_daily_no,
            "empno": empno,
            "cocode": cocode
        }

    except Exception as e:
        logger.error(f"Error getting next daily no: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得下一個日報編號失敗: {str(e)}")
