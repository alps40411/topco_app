# backend/app/api/drafts.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from ..core.legacy_database import get_legacy_db
from ..services.draft_service import DraftService

router = APIRouter(tags=["Drafts"])
logger = logging.getLogger(__name__)

@router.post("", status_code=201)
@router.post("/", status_code=201)
async def save_draft(
    draft_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """
    保存日報暫存
    - daily_no: 可選，如果不提供則自動生成或使用當天現有的編號
    - empno: 必填
    - doc_date: 必填 (YYYYMMDD)
    """
    try:
        logger.info(f"🔥 DRAFTS API - 收到暫存數據: {draft_data}")

        daily_no = draft_data.get("daily_no")  # 可選，可以是 None
        empno = draft_data.get("empno")
        doc_date = draft_data.get("doc_date")

        # 只檢查必填欄位 empno 和 doc_date
        if not empno or not doc_date:
            raise HTTPException(status_code=400, detail="缺少必要欄位: empno, doc_date")

        # Refactored to use DraftService
        # daily_no 可以是 None，DraftService 會自動處理
        result_daily_no = DraftService.save_draft(
            db=db,
            empno=empno,
            cocode=draft_data.get("cocode", "001"),
            doc_date=doc_date,
            draft_type=draft_data.get("draft_type", "TEMP"),
            draft_content=draft_data.get("draft_content", {}),
            daily_no=daily_no  # 傳入 None 時會自動生成
        )

        logger.info(f"🔥 DRAFTS API - save_draft 成功，返回 daily_no: {result_daily_no}")

        return {
            "draft_id": result_daily_no,
            "daily_no": result_daily_no,
            "message": "暫存保存成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"暫存保存失敗: {str(e)}")

@router.put("/by-daily-planno-sopno/{daily_no}/{planno}/{sopno}")
async def update_draft_by_daily_planno_sopno(
    daily_no: str,
    planno: str,
    sopno: str,
    update_data: Dict[str, Any],
    service_cocode: str = "",
    service_empno: str = "",
    db: Session = Depends(get_legacy_db)
):
    """根據 daily_no、planno、sopno、service_cocode 和 service_empno 更新特定的暫存記錄"""
    try:
        logger.info(f"🔥 UPDATE DRAFT API - 收到更新數據: daily_no={daily_no}, planno='{planno}', sopno={sopno}, service_cocode='{service_cocode}', service_empno='{service_empno}'")
        
        # Refactored to use DraftService
        DraftService.update_draft(
            db=db,
            daily_no=daily_no,
            planno=planno,
            sopno=sopno,
            update_data=update_data,
            service_cocode=service_cocode,
            service_empno=service_empno
        )

        logger.info(f"🔥 UPDATE DRAFT API - 更新完成: daily_no={daily_no}, planno={planno}, sopno={sopno}, service=({service_cocode},{service_empno})")
        
        return {
            "message": "暫存記錄更新成功",
            "daily_no": daily_no,
            "planno": planno,
            "sopno": sopno
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新暫存記錄失敗: {str(e)}")

@router.get("/{empno}")
async def get_drafts(
    empno: str,
    doc_date: str = Query(..., description="日報日期 (YYYYMMDD)"),
    draft_type: Optional[str] = Query(None, description="暫存類型: TEMP 或 AI"),
    db: Session = Depends(get_legacy_db)
):
    """取得員工的暫存資料，使用前端傳入的doc_date"""
    try:
        # Refactored to use DraftService
        drafts = DraftService.get_drafts(
            db=db,
            empno=empno,
            doc_date=doc_date,
            draft_type=draft_type
        )
        return drafts
    except Exception as e:
        logger.error(f"Error getting drafts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得暫存資料失敗: {str(e)}")

@router.delete("/{daily_no}/{planno}/{sopno}")
async def delete_draft_record(
    daily_no: str,
    planno: str,
    sopno: str,
    db: Session = Depends(get_legacy_db)
):
    """刪除指定的單筆草稿記錄及其相關檔案"""
    try:
        logger.info(f"🔥 DELETE DRAFT API - 開始刪除草稿記錄: daily_no={daily_no}, planno={planno}, sopno={sopno}")

        # Refactored to use DraftService
        DraftService.delete_draft_record(
            db=db,
            daily_no=daily_no,
            planno=planno,
            sopno=sopno
        )

        logger.info(f"🔥 DELETE DRAFT API - 刪除完成: daily_no={daily_no}, planno={planno}, sopno={sopno}")

        return {
            "message": "草稿記錄刪除成功",
            "daily_no": daily_no,
            "planno": planno,
            "sopno": sopno
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting draft record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除草稿記錄失敗: {str(e)}")
