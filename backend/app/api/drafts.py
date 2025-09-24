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

@router.post("", status_code=201)
@router.post("/", status_code=201)
async def save_draft(
    draft_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """保存日報暫存，使用前端傳入的doc_date"""
    try:
        logger.info(f"🔥 DRAFTS API - 收到暫存數據: {draft_data}")
        
        # 提取數據
        daily_no = draft_data.get("daily_no")
        empno = draft_data.get("empno")
        cocode = draft_data.get("cocode", "001")
        draft_type = draft_data.get("draft_type", "TEMP")
        draft_content = draft_data.get("draft_content", {})
        doc_date = draft_data.get("doc_date")  # 從前端傳入的doc_date
        
        logger.info(f"🔥 DRAFTS API - 解析參數: daily_no={daily_no}, empno={empno}, cocode={cocode}, draft_type={draft_type}, doc_date={doc_date}")
        logger.info(f"🔥 DRAFTS API - draft_content: {draft_content}")
        
        if not all([daily_no, empno, doc_date]):
            raise HTTPException(status_code=400, detail="缺少必要欄位: daily_no, empno, doc_date")
        
        # 保存暫存
        logger.info(f"🔥 DRAFTS API - 開始調用 LegacyReportServiceV2.save_draft")
        result_daily_no = LegacyReportServiceV2.save_draft(
            db=db,
            empno=empno,
            cocode=cocode,
            doc_date=doc_date,  # 使用前端傳入的doc_date
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

@router.put("/by-daily-planno-sopno/{daily_no}/{planno}/{sopno}")
async def update_draft_by_daily_planno_sopno(
    daily_no: str,
    planno: str,
    sopno: str,
    update_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """根據 daily_no、planno 和 sopno 更新特定的暫存記錄"""
    try:
        # 處理空的 planno - 前端傳入 "NULL" 表示空值
        if planno == "NULL":
            planno = ""

        logger.info(f"🔥 UPDATE DRAFT API - 收到更新數據: daily_no={daily_no}, planno='{planno}', sopno={sopno}, data={update_data}")

        # 檢查記錄是否存在 - 使用 planno + sopno 組合
        check_sql = text("""
            SELECT RECORD_ID, CONTENT, FILES, ATT_FILE1, ATT_FILE2
            FROM jps.tdr_draft
            WHERE DAILY_NO = :daily_no AND COALESCE(PLANNO, '') = COALESCE(:planno, '') AND SOPNO = :sopno
        """)
        
        existing_record = db.execute(check_sql, {
            "daily_no": daily_no,
            "planno": planno,
            "sopno": sopno
        }).fetchone()
        
        if not existing_record:
            raise HTTPException(status_code=404, detail="找不到指定的暫存記錄")
        
        # 準備更新數據
        content = update_data.get('content', '')
        files = update_data.get('files', [])
        
        # 處理檔案
        att_file1_list = []
        att_file2_list = []
        files_json_list = []
        
        for file_info in files:
            if isinstance(file_info, dict):
                file_name = file_info.get('name', '')
                file_url = file_info.get('url', '')
                if file_name:
                    att_file1_list.append(file_name)
                if file_url:
                    att_file2_list.append(file_url)
                files_json_list.append(file_info)
        
        att_file1 = ','.join(att_file1_list) if att_file1_list else ""
        att_file2 = ','.join(att_file2_list) if att_file2_list else ""
        files_json = json.dumps(files_json_list, ensure_ascii=False) if files_json_list else "[]"
        
        # 計算字數
        word_count = len(content) if content else 0
        
        # 更新記錄
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime('%Y%m%d')
        current_time = now.strftime('%H:%M:%S')
        
        update_sql = text("""
            UPDATE jps.tdr_draft 
            SET CONTENT = :content,
                WORD_COUNT = :word_count,
                ATT_FILE1 = :att_file1,
                ATT_FILE2 = :att_file2,
                FILES = :files,
                UPDATED_DATE = :updated_date,
                UPDATED_TIME = :updated_time
            WHERE DAILY_NO = :daily_no AND COALESCE(PLANNO, '') = COALESCE(:planno, '') AND SOPNO = :sopno
        """)
        
        db.execute(update_sql, {
            "content": content,
            "word_count": word_count,
            "att_file1": att_file1,
            "att_file2": att_file2,
            "files": files_json,
            "updated_date": current_date,
            "updated_time": current_time,
            "daily_no": daily_no,
            "planno": planno,
            "sopno": sopno
        })
        
        db.commit()
        logger.info(f"🔥 UPDATE DRAFT API - 更新完成: daily_no={daily_no}, planno={planno}, sopno={sopno}")
        
        return {
            "message": "暫存記錄更新成功",
            "daily_no": daily_no,
            "planno": planno,
            "sopno": sopno
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
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
        logger.info(f"取得員工 {empno} 在 {doc_date} 的暫存資料")
        
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