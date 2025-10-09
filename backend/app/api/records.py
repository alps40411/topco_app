# backend/app/api/records.py
"""
記錄管理 API
職責：日報填寫過程的所有操作，包括上傳檔案、提交日報等
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import json

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..models.user import User
from ..services.record_service import RecordService
from ..services.draft_service import DraftService
from ..services.legacy_service_v2 import LegacyReportServiceV2

router = APIRouter(prefix="/records", tags=["Records"])
logger = logging.getLogger(__name__)


@router.get("/today")
async def get_today_records(
    doc_date: Optional[str] = Query(None, description="日期 (YYYYMMDD)，不提供則使用今日"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得今日記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        # TODO: 實作取得今日記錄的邏輯
        # 這裡應該從 tdr_draft 或 tdr_master 查詢

        return {
            "success": True,
            "data": [],
            "message": "取得今日記錄成功"
        }

    except Exception as e:
        logger.error(f"Error getting today records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得今日記錄失敗: {str(e)}")


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


@router.get("/consolidated/{project_id}")
async def get_consolidated_by_project(
    project_id: str,
    db: Session = Depends(get_legacy_db)
):
    """取得特定項目的合併記錄"""
    try:
        # 查詢特定項目的記錄
        sql = text("""
            SELECT DAILY_NO, DRAFT_CONTENT
            FROM jps.tdr_draft
            WHERE DAILY_NO = :daily_no
        """)

        result = db.execute(sql, {"daily_no": project_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="找不到指定的記錄")

        draft_content = json.loads(result[1]) if result[1] else {}

        return {
            "daily_no": result[0],
            "consolidated_content": draft_content
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting consolidated by project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得項目記錄失敗: {str(e)}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    doc_date: str = Query(..., description="日報日期 (YYYYMMDD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """檔案上傳端點"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        result = await RecordService.upload_file(db, file, doc_date, empno)
        return result

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {str(e)}")


@router.delete("/files/{year_month}/{filename}")
async def delete_file(
    year_month: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    從伺服器上刪除一個已上傳的檔案。
    路徑格式: /files/YYYYMM/filename
    """
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        empno = current_user.employee.empno
        result = RecordService.delete_upload(db, year_month, filename, empno)
        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="檔案不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除檔案時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"刪除檔案時發生內部錯誤: {str(e)}")


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


# === 標準 RESTful API 端點 ===
# 所有兼容性端點已移除，請使用標準 API：
# - POST /api/drafts - 保存草稿
# - POST /api/records/submit - 提交日報
# - DELETE /api/records/files/{year_month}/{filename} - 刪除檔案
