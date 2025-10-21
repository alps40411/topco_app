# backend/app/api/records.py
"""
記錄管理 API
職責：日報填寫過程的所有操作，包括上傳檔案、提交日報等
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import logging

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..models.user import User
from ..services.record_service import RecordService

router = APIRouter(prefix="/records", tags=["Records"])
logger = logging.getLogger(__name__)


@router.get("/consolidated/today")
async def get_consolidated_today(
    doc_date: Optional[str] = Query(None, description="日期 (YYYYMMDD)，不提供則使用今日"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得指定日期的合併記錄（兼容今日查詢）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        consolidated_records = RecordService.get_consolidated_today(db, empno, doc_date)
        return consolidated_records

    except Exception as e:
        logger.error(f"Error getting consolidated today: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得今日合併記錄失敗: {str(e)}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    doc_date: str = Query(..., description="日報日期 (YYYYMMDD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """檔案上傳端點 - 使用 CommonAPI"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or 'A'
        result = await RecordService.upload_file(db, file, doc_date, empno, cocode)
        return result

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {str(e)}")




@router.post("/submit")
async def submit_report(
    doc_date: str = Query(..., description="日報日期 (YYYYMMDD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    提交日報到正式表

    將暫存的日報資料提交到正式表，並觸發簽核流程。
    支援多次提交（重新提交會更新現有記錄）。
    """
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or 'A'

        logger.info(f"提交日報，empno={empno}, cocode={cocode}, doc_date={doc_date}")

        # 使用 RecordService 處理提交邏輯
        result = RecordService.submit_daily_report(db, empno, cocode, doc_date)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交日報失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交日報失敗: {str(e)}")



