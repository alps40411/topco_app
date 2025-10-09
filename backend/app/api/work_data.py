# backend/app/api/work_data.py
"""
工作資料 API - 提供填寫日報所需的所有工作資料
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import logging

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..models.user import User
from ..services.work_data_service import WorkDataService

router = APIRouter(prefix="/work-data", tags=["Work Data"])
logger = logging.getLogger(__name__)


@router.get("")
async def get_work_data(
    sopno: Optional[str] = Query(None, description="執行工作編號（選填，用於查詢工作項目）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    獲取填寫日報所需的所有工作資料

    返回：
    - projects: 專案列表
    - execution_works: 執行工作列表
    - service_companies: 服務公司列表
    - service_targets: 服務對象列表
    - work_items: 工作項目列表（如果提供 sopno）
    """
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or 'A'

        # 使用 Service 獲取所有工作資料
        result = WorkDataService.get_all_work_data(
            db=db,
            empno=empno,
            cocode=cocode
        )

        # 如果提供 sopno，額外查詢工作項目
        if sopno:
            result["work_items"] = WorkDataService.get_work_items_by_sopno(
                db=db,
                sopno=sopno
            )
        else:
            result["work_items"] = []

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error getting work data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得工作資料失敗: {str(e)}")
