# backend/app/api/drafts.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime, time, timedelta
import logging
import json

from ..core.legacy_database import get_legacy_db
from ..services.legacy_service_v2 import LegacyReportServiceV2

router = APIRouter(tags=["Drafts"])
logger = logging.getLogger(__name__)

@router.post("/")
async def save_draft(
    draft_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """保存日報暫存，使用8:30-8:30邏輯重新計算doc_date"""
    try:
        logger.info(f"🔥 DRAFTS API - 收到暫存數據: {draft_data}")
        
        # 提取數據
        daily_no = draft_data.get("daily_no")
        empno = draft_data.get("empno")
        cocode = draft_data.get("cocode", "001")
        draft_type = draft_data.get("draft_type", "TEMP")
        draft_content = draft_data.get("draft_content", {})
        
        logger.info(f"🔥 DRAFTS API - 解析參數: daily_no={daily_no}, empno={empno}, cocode={cocode}, draft_type={draft_type}")
        logger.info(f"🔥 DRAFTS API - draft_content: {draft_content}")
        
        # 重新計算正確的doc_date（8:30-8:30邏輯）
        now = datetime.now()
        current_time = now.time()
        cutoff_time = time(8, 30)  # 8:30 AM
        
        # 如果現在時間早於8:30，則使用昨天的日期
        if current_time < cutoff_time:
            doc_date = (now - timedelta(days=1)).strftime('%Y%m%d')
        else:
            doc_date = now.strftime('%Y%m%d')
        
        logger.info(f"根據8:30邏輯重新計算doc_date: {doc_date}, 當前時間: {now}")
        
        if not all([daily_no, empno]):
            raise HTTPException(status_code=400, detail="缺少必要欄位: daily_no, empno")
        
        # 保存暫存
        logger.info(f"🔥 DRAFTS API - 開始調用 LegacyReportServiceV2.save_draft")
        result_daily_no = LegacyReportServiceV2.save_draft(
            db=db,
            empno=empno,
            cocode=cocode,
            doc_date=doc_date,  # 使用重新計算的doc_date
            draft_type=draft_type,
            draft_content=draft_content,
            daily_no=daily_no
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

@router.get("/{empno}")
async def get_drafts(
    empno: str,
    draft_type: Optional[str] = Query(None, description="暫存類型: TEMP 或 AI"),
    db: Session = Depends(get_legacy_db)
):
    """取得員工的暫存資料，根據8:30-8:30邏輯計算今天的DOC_DATE"""
    try:
        # 計算當前日報的日期（8:30-8:30邏輯）
        now = datetime.now()
        current_time = now.time()
        cutoff_time = time(8, 30)  # 8:30 AM
        
        # 如果現在時間早於8:30，則使用昨天的日期
        if current_time < cutoff_time:
            doc_date = (now - timedelta(days=1)).strftime('%Y%m%d')
        else:
            doc_date = now.strftime('%Y%m%d')
        
        logger.info(f"根據8:30邏輯，當前日報日期為: {doc_date}, 當前時間: {now}")
        
        # 構建查詢條件，不使用STATUS
        where_clause = "WHERE EMPNO = :empno AND DOC_DATE = :doc_date"
        params = {"empno": empno, "doc_date": doc_date}
        
        if draft_type:
            where_clause += " AND DRAFT_TYPE = :draft_type"
            params["draft_type"] = draft_type
        
        sql = text(f"""
            SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE, 
                   PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C, WORK_ITEM_SEQ,
                   SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC, SERVICE_DEPTNO,
                   CONTENT, EXECUTION_TIME_MINUTES, WORD_COUNT,
                   ATT_FILE1, ATT_FILE2, FILES,
                   CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME
            FROM jps.tdr_draft
            {where_clause}
            ORDER BY UPDATED_DATE DESC, UPDATED_TIME DESC
        """)
        
        result = db.execute(sql, params)
        
        drafts = []
        for row in result.fetchall():
            # 解析檔案清單
            files = []
            if row[19]:  # FILES 欄位
                try:
                    files = json.loads(row[19])
                except:
                    files = []
            
            draft = {
                "daily_no": row[0],
                "empno": row[1],
                "cocode": row[2],
                "doc_date": row[3],
                "draft_type": row[4],
                "planno": row[5],
                "plan_subj_c": row[6],
                "sopno": row[7],
                "sop_desc_c": row[8],
                "work_item_seq": row[9],
                "service_cocode": row[10],
                "service_empno": row[11],
                "service_empnamec": row[12],
                "service_deptno": row[13],
                "content": row[14],
                "execution_time_minutes": row[15],
                "word_count": row[16],
                "att_file1": row[17],
                "att_file2": row[18],
                "files": files,
                "created_date": row[20],
                "created_time": row[21],
                "updated_date": row[22],
                "updated_time": row[23]
            }
            drafts.append(draft)
        
        logger.info(f"找到 {len(drafts)} 筆今日暫存記錄")
        return drafts
    except Exception as e:
        logger.error(f"Error getting drafts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得暫存資料失敗: {str(e)}")