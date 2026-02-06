# backend/app/api/records.py
"""
記錄管理 API
職責：日報填寫過程的所有操作，包括上傳檔案、提交日報等
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime
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

    except HTTPException:
        raise
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


@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    刪除日報
    - 只有作者本人可以刪除
    - 如果已有留言則不能刪除
    - 刪除時會刪除 detail1、detail2、master
    - 並插入 del_inbox 到 eai_source 通知系統
    """
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        # 查詢日報基本資訊
        master_sql = text("""
            SELECT daily_no, empno, empnamec, doc_date, cocode
            FROM jps.tdr_master
            WHERE daily_no = :daily_no
        """)

        master_result = db.execute(master_sql, {"daily_no": report_id}).fetchone()
        if not master_result:
            raise HTTPException(status_code=404, detail="找不到指定的日報")

        daily_no, report_empno, empnamec, doc_date, cocode = master_result

        # 權限檢查：只有作者本人可以刪除
        if report_empno != current_user.employee.empno:
            raise HTTPException(status_code=403, detail="只有作者本人可以刪除日報")

        # 檢查是否有留言
        reply_count_sql = text("""
            SELECT COUNT(*) FROM jps.tdr_reply WHERE daily_no = :daily_no
        """)
        reply_count = db.execute(reply_count_sql, {"daily_no": report_id}).scalar()

        if reply_count > 0:
            raise HTTPException(status_code=400, detail="此日報已有留言，無法刪除")

        # 開始刪除流程
        now = datetime.now()
        current_date = now.strftime('%Y/%m/%d')
        current_time = now.strftime('%H:%M:%S')

        # 1. 刪除 tdr_detail2
        delete_detail2_sql = text("DELETE FROM jps.tdr_detail2 WHERE daily_no = :daily_no")
        detail2_deleted = db.execute(delete_detail2_sql, {"daily_no": report_id}).rowcount
        logger.info(f"刪除 {detail2_deleted} 筆 tdr_detail2 記錄")

        # 2. 刪除 tdr_detail1
        delete_detail1_sql = text("DELETE FROM jps.tdr_detail1 WHERE daily_no = :daily_no")
        detail1_deleted = db.execute(delete_detail1_sql, {"daily_no": report_id}).rowcount
        logger.info(f"刪除 {detail1_deleted} 筆 tdr_detail1 記錄")

        # 3. 刪除 tdr_master
        delete_master_sql = text("DELETE FROM jps.tdr_master WHERE daily_no = :daily_no")
        master_deleted = db.execute(delete_master_sql, {"daily_no": report_id}).rowcount
        logger.info(f"刪除 {master_deleted} 筆 tdr_master 記錄")

        # 4. 插入 del_inbox 到 eai_source
        eai_seq = db.execute(text("SELECT jps.seq_eai_source.nextval FROM dual")).scalar_one()

        doc_bady = (
            f"Source=JpsReportDailyDelete^|Action=Del_inbox^|cocode=Del_inbox^|xuser={report_empno}^|"
            f"doc_date={current_date}^|doc_time={current_time}^|Key={daily_no}^|Subject=Daily_Dele_Report"
        )

        insert_eai_sql = text("""
            INSERT INTO jps.eai_source
            (eai_seq, source, subject, cocode, xuser, touser, doc_date, doc_time, key, action, doc_bady, status, planno)
            VALUES (:eai_seq, 'JpsReportDailyDelete', 'Daily_Dele_Report', :cocode, :xuser, '', :doc_date, :doc_time, :key, 'Del_inbox', :doc_bady, 'N', NULL)
        """)

        db.execute(insert_eai_sql, {
            "eai_seq": eai_seq,
            "cocode": cocode,
            "xuser": report_empno,
            "doc_date": current_date,
            "doc_time": current_time,
            "key": daily_no,
            "doc_bady": doc_bady
        })

        logger.info(f"成功插入 del_inbox 記錄到 eai_source, eai_seq: {eai_seq}")

        db.commit()

        return {
            "success": True,
            "message": "日報刪除成功",
            "deleted_items": {
                "detail1": detail1_deleted,
                "detail2": detail2_deleted,
                "master": master_deleted
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除日報失敗: {str(e)}")
