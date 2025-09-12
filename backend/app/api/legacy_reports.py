# backend/app/api/legacy_reports.py
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..core.config import settings
from ..models.user import User
from ..services.legacy_service_v2 import LegacyReportServiceV2
from ..schemas.legacy_schemas import (
    DailyReportListItem, DailyReportContent, WorkPlan,
    DraftSaveRequest, AttachmentSaveRequest,
    ReportSubmitRequest, DraftResponse, SubmitResponse
)
import logging
import json
import os
import uuid
import aiofiles
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timedelta

router = APIRouter(prefix="/legacy", tags=["legacy-reports"])
records_router = APIRouter(prefix="/records", tags=["records"])
logger = logging.getLogger(__name__)

# 簡單的內存緩存
_work_data_cache = {}
_cache_timeout = timedelta(minutes=10)  # 緩存 10 分鐘

@router.get("/reports", response_model=List[Dict[str, Any]])
async def get_daily_reports(
    empno: str = Query(..., description="員工編號"),
    doc_date: str = Query(..., description="日報日期 (YYYYMMDD)"),
    cocode: Optional[str] = Query(None, description="公司別"),
    deptno: Optional[str] = Query(None, description="部門代碼"),
    db: Session = Depends(get_legacy_db)
):
    """
    取得日報列表 BY 工號（主管）
    
    - **empno**: 員工編號（主管）
    - **doc_date**: 日報日期，格式 YYYYMMDD (如: 20241225)
    - **cocode**: 公司別 (可選)
    - **deptno**: 部門代碼 (可選)
    """
    try:
        reports = LegacyReportServiceV2.get_daily_reports_by_supervisor(
            db=db,
            empno=empno,
            doc_date=doc_date,
            cocode=cocode,
            deptno=deptno
        )
        return reports
    except Exception as e:
        logger.error(f"Error getting daily reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得日報列表失敗: {str(e)}")

@router.get("/reports/{daily_no}/content", response_model=List[Dict[str, Any]])
async def get_daily_report_content(
    daily_no: str,
    db: Session = Depends(get_legacy_db)
):
    """
    取得日報內容詳細
    
    - **daily_no**: 日報編號
    """
    try:
        content = LegacyReportServiceV2.get_daily_report_content(
            db=db,
            daily_no=daily_no
        )
        
        if not content:
            raise HTTPException(status_code=404, detail="找不到指定的日報內容")
        
        return content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily report content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得日報內容失敗: {str(e)}")

@router.get("/work-plans", response_model=List[Dict[str, Any]])
async def get_work_plans(
    empno: str = Query(..., description="員工編號"),
    db: Session = Depends(get_legacy_db)
):
    """
    取得工作計畫
    
    - **empno**: 員工編號
    """
    try:
        plans = LegacyReportServiceV2.get_work_plans(
            db=db,
            empno=empno
        )
        return plans
    except Exception as e:
        logger.error(f"Error getting work plans: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得工作計畫失敗: {str(e)}")

@router.get("/companies")
async def get_companies(db: Session = Depends(get_legacy_db)):
    """取得服務公司列表"""
    try:
        from sqlalchemy import text
        sql = text("SELECT cocode, coabbv FROM jps.dcd001$master WHERE eip_active = 'Y'")
        result = db.execute(sql)
        
        companies = []
        for row in result.fetchall():
            companies.append({
                "id": row[0],  # cocode as id
                "cocode": row[0],
                "coabbv": row[1]
            })
        
        return companies
    except Exception as e:
        logger.error(f"Error getting companies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得公司列表失敗: {str(e)}")

@router.get("/next-daily-no")
async def get_next_daily_no(db: Session = Depends(get_legacy_db)):
    """取得新的日報編號"""
    try:
        from sqlalchemy import text
        # Oracle sequence syntax
        sql = text("SELECT seq_tdr_master.nextval FROM dual")
        result = db.execute(sql)
        daily_no = result.scalar()
        
        return {"daily_no": str(daily_no)}
    except Exception as e:
        logger.error(f"Error getting next daily no: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得日報編號失敗: {str(e)}")

# === 暫存和提交相關 API ===

@router.post("/drafts", response_model=DraftResponse)
async def save_draft(
    draft_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """保存日報暫存，使用8:30-8:30邏輯重新計算doc_date"""
    try:
        logger.info(f"收到暫存數據: {draft_data}")
        
        # 提取數據
        daily_no = draft_data.get("daily_no")
        empno = draft_data.get("empno")
        cocode = draft_data.get("cocode", "001")
        draft_type = draft_data.get("draft_type", "TEMP")
        draft_content = draft_data.get("draft_content", {})
        
        # 重新計算正確的doc_date（8:30-8:30邏輯）
        from datetime import datetime, time, timedelta
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
        result_daily_no = LegacyReportServiceV2.save_draft(
            db=db,
            empno=empno,
            cocode=cocode,
            doc_date=doc_date,  # 使用重新計算的doc_date
            draft_type=draft_type,
            draft_content=draft_content,
            daily_no=daily_no
        )
        
        return DraftResponse(
            draft_id=result_daily_no,
            daily_no=result_daily_no,
            message="暫存保存成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"暫存保存失敗: {str(e)}")


@router.post("/attachments")
async def save_attachment(
    attachment_data: AttachmentSaveRequest,
    db: Session = Depends(get_legacy_db)
):
    """保存附件"""
    try:
        att_id = LegacyReportServiceV2.save_attachment(
            db=db,
            draft_id=attachment_data.draft_id,
            file_name=attachment_data.file_name,
            file_path=attachment_data.file_path,
            file_size=attachment_data.file_size,
            file_type=attachment_data.file_type,
            is_selected_for_ai=attachment_data.is_selected_for_ai
        )
        
        return {"att_id": att_id, "message": "附件保存成功"}
    except Exception as e:
        logger.error(f"Error saving attachment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"附件保存失敗: {str(e)}")

# 舊的提交端點已移除，請使用 /upload-daily-report 端點

# === 查詢相關 API ===

@router.get("/drafts/{empno}")
async def get_drafts(
    empno: str,
    draft_type: Optional[str] = Query(None, description="暫存類型: TEMP 或 AI"),
    db: Session = Depends(get_legacy_db)
):
    """取得員工的暫存資料，根據8:30-8:30邏輯計算今天的DOC_DATE"""
    try:
        from sqlalchemy import text
        from datetime import datetime, time, timedelta
        
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


@router.delete("/drafts/{draft_id}")
async def delete_draft(
    draft_id: str,
    db: Session = Depends(get_legacy_db)
):
    """刪除暫存資料（軟刪除）"""
    try:
        from sqlalchemy import text
        
        sql = text("""
            UPDATE tdr_draft 
            SET STATUS = 'D', UPDATED_DATE = :updated_date, UPDATED_TIME = :updated_time
            WHERE DRAFT_ID = :draft_id
        """)
        
        from datetime import datetime
        now = datetime.now()
        
        result = db.execute(sql, {
            "draft_id": draft_id,
            "updated_date": now.strftime('%Y%m%d'),
            "updated_time": now.strftime('%H:%M:%S')
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="找不到指定的暫存資料")
        
        db.commit()
        return {"message": "暫存資料刪除成功"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除暫存資料失敗: {str(e)}")

# === 工作計畫相關 API ===

@router.get("/api-status")
async def get_api_status():
    """獲取API配置狀態，幫助前端了解後端邏輯"""
    return {
        "message": "Legacy Reports API Status",
        "work_plan_config": {
            "is_required": False,
            "description": "工作計畫為非必填項目",
            "default_option": "請選擇工作計畫"
        },
        "execution_work_config": {
            "is_required": True,
            "description": "執行工作為必填項目",
            "depends_on_work_plan": False,
            "note": "不管是否選擇工作計畫，都可以選擇執行工作"
        },
        "work_item_config": {
            "is_required": True,
            "description": "工作項目為必填項目",
            "depends_on_execution_work": True
        },
        "service_target_config": {
            "is_required": False,
            "description": "服務對象為非必填項目"
        }
    }

@router.get("/work-items")
async def get_work_items(
    sopno: str = Query(..., description="執行工作編號"),
    db: Session = Depends(get_legacy_db)
):
    """取得工作項目列表 (基於執行工作)"""
    try:
        from sqlalchemy import text
        
        sql = text("""
            SELECT seq, name
            FROM jps.tpm_sop_detail
            WHERE sopno = :sopno
            ORDER BY seq
        """)
        
        result = db.execute(sql, {"sopno": sopno})
        
        work_items = []
        for row in result.fetchall():
            work_items.append({
                "id": f"{sopno}_{row[0]}",  # sopno_seq
                "name": row[1] or f"工作項目 {row[0]}",  # name
                "seq": row[0],
                "sopno": sopno
            })
        
        return work_items
    except Exception as e:
        logger.error(f"Error getting work items: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得工作項目失敗: {str(e)}")

@router.get("/service-companies")
async def get_service_companies(db: Session = Depends(get_legacy_db)):
    """取得服務公司列表 (重用現有的公司API)"""
    return await get_companies(db)


@router.get("/test-tables")
async def test_tables(db: Session = Depends(get_legacy_db)):
    """測試資料庫連接並查看可用的表格"""
    try:
        from sqlalchemy import text
        
        # 查看所有 schema
        sql = text("""
            SELECT DISTINCT table_schema
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE'
            ORDER BY table_schema
        """)
        
        result = db.execute(sql)
        
        schemas = []
        for row in result.fetchall():
            schemas.append(row[0])
        
        # 查看所有表格
        sql2 = text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name
            LIMIT 100
        """)
        
        result2 = db.execute(sql2)
        
        tables = []
        for row in result2.fetchall():
            tables.append({
                "schema": row[0],
                "table": row[1],
                "full_name": f"{row[0]}.{row[1]}"
            })
        
        return {
            "message": "資料庫連接成功",
            "schemas": schemas,
            "table_count": len(tables),
            "tables": tables
        }
    except Exception as e:
        logger.error(f"Error testing database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"資料庫測試失敗: {str(e)}")

@router.get("/service-targets")
async def get_service_targets(db: Session = Depends(get_legacy_db)):
    """取得服務對象列表"""
    try:
        from sqlalchemy import text
        sql = text("""
            SELECT a.cocode, a.coabbv, b.deptno, b.deptabbv, c.empno, c.empnamec
            FROM jps.dcd001$master a
            JOIN jps.dcd002$master b ON b.cocode = a.cocode
            JOIN jps.dcd003$master c ON c.cocode = b.cocode
            AND c.deptno = b.deptno
            AND c.estatus <> '3'
            AND a.cocode NOT IN ('001')
            WHERE c.quitdate IS NULL
            ORDER BY a.cocode, b.deptno, c.empno
        """)
        result = db.execute(sql)
        
        service_targets = []
        for row in result.fetchall():
            service_targets.append({
                "cocode": row[0],
                "coabbv": row[1],
                "deptno": row[2],
                "deptabbv": row[3],
                "empno": row[4],
                "empnamec": row[5],
                "display_name": f"{row[1]} - {row[3]} - {row[5]}({row[4]})"
            })
        
        return service_targets
    except Exception as e:
        logger.error(f"Error getting service targets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得服務對象失敗: {str(e)}")

@router.get("/work-data")
async def get_all_work_data(
    empno: str = Query(..., description="員工編號"),
    db: Session = Depends(get_legacy_db)
):
    """取得所有工作相關資料：工作計畫、執行工作和工作項目"""
    try:
        # 檢查緩存
        cache_key = f"work_data_{empno}"
        now = datetime.now()
        
        if cache_key in _work_data_cache:
            cached_data, cached_time = _work_data_cache[cache_key]
            if now - cached_time < _cache_timeout:
                logger.info(f"使用緩存數據: {empno}")
                return cached_data
        
        from sqlalchemy import text
        
        # 1. 取得工作計畫
        work_plans_sql = text("""
            SELECT DISTINCT A.planno, A.plan_subj_c
            FROM jps.tjp_master A
            LEFT JOIN jps.tjp_partner E ON A.planno = E.planno
            WHERE (A.empno = :empno or A.pm_empno = :empno or E.part_empno = :empno)
            and (A.plan_date2 is null or A.plan_date2 >= TO_CHAR(CURRENT_DATE,'YYYYMMDD'))
            ORDER BY A.planno DESC
        """)
        
        work_plans_result = db.execute(work_plans_sql, {"empno": empno})
        work_plans = []
        for row in work_plans_result.fetchall():
            work_plans.append({
                "planno": row[0],
                "plan_subj_c": row[1] or f"工作計畫 {row[0]}"
            })
        
        # 2. 取得基本執行工作（沒有工作計畫時的執行工作）
        basic_execution_works_sql = text("""
            SELECT A.sopno, A.sop_desc_c, B.seq, B.name
            FROM (
                SELECT sopno, sop_desc_c
                FROM jps.tpm_sop
                WHERE cocode IN ('A','E','H','M','K','P','L','R','G','J07','J09','J10','J11','S','J15','J16','J17','J18','J19')
                AND xstatus = '1'
                AND (deptno IS NULL OR deptno = '00253')
                AND (sop_role IS NULL OR sop_role = '技術同仁')
                UNION
                SELECT sopno, sop_desc_c
                FROM jps.tpm_sop
                WHERE sopno IN (
                    SELECT sopno FROM jps.TJP_MASTER WHERE empno = :empno
                    UNION ALL
                    SELECT b.sopno FROM jps.tjp_partner a, jps.TJP_MASTER b
                    WHERE A.PLANNO = b.planno AND a.part_empno = :empno
                )
            ) A
            LEFT JOIN jps.tpm_sop_detail B ON A.sopno = B.sopno
            ORDER BY A.sopno, B.seq
        """)
        
        basic_result = db.execute(basic_execution_works_sql, {"empno": empno})
        basic_execution_works = []
        current_sop = None
        
        for row in basic_result.fetchall():
            sopno = row[0]
            sop_desc_c = row[1]
            seq = row[2] if len(row) > 2 else None
            work_item_name = row[3] if len(row) > 3 else None
            
            if current_sop != sopno:
                basic_execution_works.append({
                    "sopno": str(sopno),  # 確保 sopno 是字符串
                    "sop_desc_c": sop_desc_c or f"執行工作 {sopno}",
                    "work_items": []
                })
                current_sop = sopno
            
            if seq is not None and work_item_name:
                basic_execution_works[-1]["work_items"].append({
                    "seq": str(seq),  # 確保 seq 是字符串
                    "name": work_item_name,
                    "unique_id": f"{sopno}_{seq}"  # 創建唯一 ID
                })
        
        # 3. 取得所有工作計畫的執行工作（優化：使用單一查詢）
        project_execution_works = {}
        if work_plans:
            # 構建 planno 列表
            planno_list = [str(plan["planno"]) for plan in work_plans]
            planno_params = ", ".join([f":planno_{i}" for i in range(len(planno_list))])
            
            project_sql = text(f"""
                SELECT t.planno, t.sopno, s.sop_desc_c, d.seq, d.name
                FROM jps.tjp_master t
                LEFT JOIN jps.tpm_sop s ON t.sopno = s.sopno
                LEFT JOIN jps.tpm_sop_detail d ON s.sopno = d.sopno
                WHERE t.planno IN ({planno_params})
                ORDER BY t.planno, t.sopno, d.seq
            """)
            
            # 準備參數
            params = {f"planno_{i}": planno for i, planno in enumerate(planno_list)}
            project_result = db.execute(project_sql, params)
            
            # 組織結果
            for row in project_result.fetchall():
                planno = str(row[0])
                sopno = row[1]
                sop_desc_c = row[2]
                seq = row[3] if len(row) > 3 else None
                work_item_name = row[4] if len(row) > 4 else None
                
                # 初始化 planno 的執行工作字典
                if planno not in project_execution_works:
                    project_execution_works[planno] = {}
                
                # 初始化 sopno 的工作項目列表
                if sopno not in project_execution_works[planno]:
                    project_execution_works[planno][sopno] = {
                        "sopno": str(sopno),
                        "sop_desc_c": sop_desc_c or f"執行工作 {sopno}",
                        "work_items": []
                    }
                
                # 添加工作項目
                if seq is not None and work_item_name:
                    project_execution_works[planno][sopno]["work_items"].append({
                        "seq": str(seq),
                        "name": work_item_name,
                        "unique_id": f"{sopno}_{seq}"
                    })
            
            # 轉換為列表格式
            for planno in project_execution_works:
                project_execution_works[planno] = list(project_execution_works[planno].values())
        
        # 4. 取得服務公司列表
        service_companies_sql = text("SELECT cocode, coabbv FROM jps.dcd001$master WHERE eip_active = 'Y'")
        service_companies_result = db.execute(service_companies_sql)
        service_companies = []
        for row in service_companies_result.fetchall():
            service_companies.append({
                "id": row[0],  # cocode as id
                "cocode": row[0],
                "coabbv": row[1]
            })
        
        # 5. 取得服務對象列表
        service_targets_sql = text("""
            SELECT a.cocode, a.coabbv, b.deptno, b.deptabbv, c.empno, c.empnamec
            FROM jps.dcd001$master a
            JOIN jps.dcd002$master b ON b.cocode = a.cocode
            JOIN jps.dcd003$master c ON c.cocode = b.cocode
            AND c.deptno = b.deptno
            AND c.estatus <> '3'
            AND a.cocode NOT IN ('001')
            WHERE c.quitdate IS NULL
            ORDER BY a.cocode, b.deptno, c.empno
        """)
        
        service_targets_result = db.execute(service_targets_sql)
        service_targets = []
        for row in service_targets_result.fetchall():
            service_targets.append({
                "cocode": row[0],
                "coabbv": row[1],
                "deptno": row[2],
                "deptabbv": row[3],
                "empno": row[4],
                "empnamec": row[5]
            })
        
        result = {
            "work_plans": work_plans,
            "basic_execution_works": basic_execution_works,
            "project_execution_works": project_execution_works,
            "service_companies": service_companies,
            "service_targets": service_targets
        }
        
        # 保存到緩存
        _work_data_cache[cache_key] = (result, now)
        
        # 清理過期緩存
        expired_keys = [
            key for key, (_, cached_time) in _work_data_cache.items()
            if now - cached_time > _cache_timeout
        ]
        for key in expired_keys:
            del _work_data_cache[key]
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting all work data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得工作資料失敗: {str(e)}")

# === Records API (前端相容性) ===

@records_router.get("/consolidated/today")
async def get_consolidated_today(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得今天的合併記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
            
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        empno = current_user.employee.empno
        
        # 查詢今天的所有活躍記錄
        draft_sql = text("""
            SELECT d.DAILY_NO, d.CONTENT, d.PLANNO, d.PLAN_SUBJ_C, d.SOPNO, d.SOP_DESC_C, 
                   d.WORK_ITEM_SEQ, d.SERVICE_COCODE, d.SERVICE_EMPNO, d.SERVICE_EMPNAMEC, 
                   d.EXECUTION_TIME_MINUTES, d.FILES, d.AI_CONTENT, d.STATUS
            FROM jps.tdr_draft d
            WHERE d.EMPNO = :empno 
            AND d.DOC_DATE = :doc_date 
            ORDER BY d.CREATED_DATE DESC
        """)
        
        draft_result = db.execute(draft_sql, {
            "empno": empno,
            "doc_date": today
        })
        
        rows = draft_result.fetchall()
        logger.info(f"查詢到 {len(rows)} 條記錄 for empno={empno}, date={today}")
        
        consolidated_records = []
        for row in rows:
            daily_no = row[0]
            content = row[1] or ""
            planno = row[2] or ""
            plan_subj_c = row[3] or "基本工作項目"
            
            logger.info(f"處理記錄: daily_no={daily_no}, planno={planno}, plan_subj_c={plan_subj_c}")
            sopno = row[4] or ""
            sop_desc_c = row[5] or ""
            work_item_seq = row[6] or ""
            service_cocode = row[7] or ""
            service_empno = row[8] or ""
            service_empnamec = row[9] or ""
            execution_time_minutes = row[10] or 0
            files_json = row[11] or "[]"
            ai_content = row[12]
            status = row[13]
            
            # 解析多個工作項目序號並取得對應的中文名稱
            work_item_names = []
            if work_item_seq and sopno:
                logger.info(f"處理工作項目序列: '{work_item_seq}', sopno: '{sopno}'")
                # 分割工作項目序號（如 "1/2" → ["1", "2"]）
                seq_parts = work_item_seq.split('/')
                logger.info(f"分割後的序號: {seq_parts}")
                for seq in seq_parts:
                    if seq.strip():
                        # 查詢每個序號對應的中文名稱
                        work_item_sql = text("""
                            SELECT name FROM jps.tpm_sop_detail 
                            WHERE sopno = :sopno AND seq = :seq
                        """)
                        work_item_result = db.execute(work_item_sql, {
                            "sopno": sopno,
                            "seq": seq.strip()
                        }).fetchone()
                        
                        if work_item_result and work_item_result[0]:
                            work_item_names.append(work_item_result[0])
                            logger.info(f"找到工作項目 {seq}: '{work_item_result[0]}'")
                        else:
                            work_item_names.append(f"工作項目 {seq}")
                            logger.warning(f"未找到工作項目 sopno={sopno}, seq={seq} 的中文名稱")
            
            # 合併工作項目名稱
            work_item_name = " / ".join(work_item_names) if work_item_names else work_item_seq
            logger.info(f"最終工作項目名稱: '{work_item_name}'")
            
            # 解析檔案
            try:
                files = json.loads(files_json) if files_json else []
            except:
                files = []
            
            # 構建服務對象名稱
            service_target_name = ""
            if service_empnamec and service_empno:
                service_target_name = f"{service_empnamec}({service_empno})"
            
            consolidated_records.append({
                "daily_no": daily_no,  # 添加 daily_no 字段
                "sopno": sopno,        # 添加 sopno 字段用於精確識別記錄
                "project": {
                    "id": planno,
                    "plan_subj_c": plan_subj_c
                },
                "execution_work_name": sop_desc_c,
                "work_item_name": work_item_name,  # 使用中文工作項目名稱
                "service_company_name": service_cocode,
                "service_target_name": service_target_name,
                "content": content,
                "files": files,
                "record_count": 1,
                "ai_content": ai_content,
                "total_execution_time_minutes": execution_time_minutes
            })
        
        return consolidated_records
        
    except Exception as e:
        logger.error(f"Error getting consolidated today: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得今日合併記錄失敗: {str(e)}")

@records_router.get("/writing-status")
async def get_writing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得寫作狀態"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
            
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        empno = current_user.employee.empno
        
        # 檢查是否有暫存
        draft_sql = text("""
            SELECT COUNT(*) 
            FROM jps.tdr_draft 
            WHERE EMPNO = :empno 
            AND DOC_DATE = :doc_date 
            
        """)
        
        draft_count = db.execute(draft_sql, {
            "empno": empno,
            "doc_date": today
        }).scalar()
        
        # 檢查是否已提交
        submitted_sql = text("""
            SELECT COUNT(*) 
            FROM jps.tdr_master 
            WHERE EMPNO = :empno 
            AND DOC_DATE = :doc_date
        """)
        
        submitted_count = db.execute(submitted_sql, {
            "empno": empno,
            "doc_date": today
        }).scalar()
        
        # 檢查是否有主管已經評分或回覆（任一主管有評分就鎖定）
        review_status_sql = text("""
            SELECT 
                (SELECT COUNT(*) FROM jps.tdr_score s 
                 JOIN jps.tdr_master m ON s.daily_no = m.daily_no 
                 WHERE m.empno = :empno AND m.doc_date = :doc_date) as score_count,
                (SELECT COUNT(*) FROM jps.tdr_reply r 
                 JOIN jps.tdr_master m ON r.daily_no = m.daily_no 
                 WHERE m.empno = :empno AND m.doc_date = :doc_date) as reply_count
        """)
        
        review_result = db.execute(review_status_sql, {
            "empno": empno,
            "doc_date": today
        }).fetchone()
        
        score_count = review_result[0] if review_result else 0
        reply_count = review_result[1] if review_result else 0
        has_supervisor_review = score_count > 0 or reply_count > 0
        
        # 檢查時間範圍（8:30 - 隔天8:30）
        from datetime import datetime, time
        now = datetime.now()
        current_time = now.time()
        cutoff_time = time(8, 30)  # 8:30 AM
        
        # 如果現在時間早於8:30，則是前一天的填寫時間
        if current_time < cutoff_time:
            # 當前日期減一天作為doc_date
            from datetime import timedelta
            actual_date = (now - timedelta(days=1)).strftime('%Y%m%d')
            is_within_writing_period = True
        else:
            # 當前日期作為doc_date
            actual_date = now.strftime('%Y%m%d')
            is_within_writing_period = True
            
        # 確保查詢的是正確的日期
        if today != actual_date:
            # 重新查詢正確日期的數據
            draft_count = db.execute(draft_sql, {
                "empno": empno,
                "doc_date": actual_date
            }).scalar()
            
            submitted_count = db.execute(submitted_sql, {
                "empno": empno,
                "doc_date": actual_date
            }).scalar()
            
            review_result = db.execute(review_status_sql, {
                "empno": empno,
                "doc_date": actual_date
            }).fetchone()
            
            score_count = review_result[0] if review_result else 0
            reply_count = review_result[1] if review_result else 0
            has_supervisor_review = score_count > 0 or reply_count > 0
        
        # 決定狀態和是否允許編輯
        allowed = True
        message = "可以填寫日報"
        
        if has_supervisor_review:
            allowed = False
            message = "主管已審閱，今日無法編輯，請等待隔天8:30後填寫新的日報"
            status = "reviewed"
        elif submitted_count > 0:
            status = "submitted"
            message = "日報已提交，等待主管審閱"
        elif draft_count > 0:
            status = "draft"
            message = "有草稿，可以繼續編輯"
        else:
            status = "empty"
            message = "尚未開始填寫日報"
        
        return {
            "allowed": allowed,
            "message": message,
            "current_time": now.strftime('%Y-%m-%d %H:%M:%S'),
            "empno": empno,
            "doc_date": actual_date,
            "status": status,
            "draft_count": draft_count,
            "submitted_count": submitted_count,
            "has_supervisor_review": has_supervisor_review,
            "score_count": score_count,
            "reply_count": reply_count
        }
        
    except Exception as e:
        logger.error(f"Error getting writing status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得寫作狀態失敗: {str(e)}")

@records_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """檔案上傳端點"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 檢查檔案大小
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"檔案太大，最大允許 {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # 檢查檔案類型
        allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.gif'}
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的檔案類型: {file_ext}"
            )
        
        # 創建上傳目錄
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True)
        
        # 生成唯一檔案名
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        # 保存檔案
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 返回檔案資訊（模擬前端期待的格式）
        return {
            "id": file_id,
            "name": file.filename,
            "type": file.content_type or "application/octet-stream",
            "size": len(content),
            "url": f"/uploads/{safe_filename}",
            "path": str(file_path),
            "upload_date": datetime.now().strftime('%Y%m%d'),
            "upload_time": datetime.now().strftime('%H%M%S'),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {str(e)}")

@records_router.post("/upload-record")
async def upload_record(
    record_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """上傳記錄（兼容性端點，實際使用 drafts API）"""
    try:
        # 將上傳轉換為暫存保存
        draft_request = DraftSaveRequest(
            empno=record_data.get("empno"),
            cocode=record_data.get("cocode", "A"),
            doc_date=record_data.get("doc_date"),
            draft_type="TEMP",
            draft_content=DailyReportContent(**record_data.get("content", {}))
        )
        
        draft_id = LegacyReportServiceV2.save_draft(
            db=db,
            empno=draft_request.empno,
            cocode=draft_request.cocode,
            doc_date=draft_request.doc_date,
            draft_type=draft_request.draft_type,
            draft_content=draft_request.draft_content.dict()
        )
        
        return {
            "success": True,
            "message": "記錄上傳成功",
            "draft_id": draft_id
        }
        
    except Exception as e:
        logger.error(f"Error uploading record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"記錄上傳失敗: {str(e)}")



@records_router.get("/consolidated/{project_id}")
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

@records_router.post("/")
async def create_record(
    record_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """創建新記錄（兼容性端點）"""
    try:
        # 轉換為暫存保存
        return await upload_record(record_data, db)
        
    except Exception as e:
        logger.error(f"Error creating record: {str(e)}")
        raise HTTPException(status_code=500, detail=f"創建記錄失敗: {str(e)}")

# === Comments API removed - now handled by /api/reports/ ===

@router.post("/upload-daily-report")
async def upload_daily_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """上傳日報到正式表 - 每天五點後開放，支援多次提交"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 檢查時間限制：每天五點後才開放上傳
        now = datetime.now()
        # current_hour = now.hour
        # if current_hour < 17:  # 17:00 = 5 PM
        #     raise HTTPException(
        #         status_code=403, 
        #         detail=f"上傳功能僅在每天下午5點後開放，目前時間：{now.strftime('%H:%M')}"
        #     )
        
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or 'A'
        doc_date = now.strftime('%Y%m%d')
        
        # 查詢今日所有暫存資料
        draft_sql = text("""
            SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE,
                   PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C, WORK_ITEM_SEQ,
                   SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC, SERVICE_DEPTNO,
                   CONTENT, EXECUTION_TIME_MINUTES, WORD_COUNT,
                   ATT_FILE1, ATT_FILE2, FILES, STATUS
            FROM jps.tdr_draft 
            WHERE EMPNO = :empno AND COCODE = :cocode AND DOC_DATE = :doc_date
            ORDER BY CREATED_DATE, CREATED_TIME
        """)
        
        draft_results = db.execute(draft_sql, {
            "empno": empno, 
            "cocode": cocode, 
            "doc_date": doc_date
        }).fetchall()
        
        if not draft_results:
            raise HTTPException(status_code=400, detail="沒有可上傳的暫存資料")
        
        # 取得第一個暫存記錄的daily_no作為正式日報編號
        daily_no = draft_results[0][0]
        logger.info(f"上傳日報 daily_no: {daily_no}")
        
        # 檢查是否已被主管審閱
        review_check_sql = text("""
            SELECT STATUS FROM jps.tdr_master 
            WHERE DAILY_NO = :daily_no
        """)
        review_result = db.execute(review_check_sql, {"daily_no": daily_no}).fetchone()
        
        if review_result and review_result[0] in ['Y', 'A']:  # Y=已審閱, A=已核准
            raise HTTPException(
                status_code=403, 
                detail="此日報已被主管審閱，無法再進行修改"
            )
        
        # 查詢員工詳細資訊
        emp_sql = text("""
            SELECT e.empnamec, e.deptno, d.deptnamec, e.g_deptno, e.leader
            FROM jps.dcd003$master e
            LEFT JOIN jps.dcd002$master d ON e.deptno = d.deptno AND e.cocode = d.cocode
            WHERE e.empno = :empno AND e.cocode = :cocode
        """)
        emp_result = db.execute(emp_sql, {"empno": empno, "cocode": cocode}).fetchone()
        
        if not emp_result:
            raise HTTPException(status_code=400, detail="找不到員工資訊")
        
        empnamec, deptno, deptnamec, g_deptno, leader = emp_result
        
        # 計算總字數和合併檔案
        total_word_count = 0
        all_files = []
        all_att_file1 = None
        all_att_file2 = None
        
        for draft in draft_results:
            total_word_count += draft[16] or 0  # WORD_COUNT
            if draft[19]:  # FILES
                try:
                    files = json.loads(draft[19])
                    all_files.extend(files)
                except:
                    pass
            # 收集所有檔案名稱和路徑 - 修復：用逗號分隔所有檔案
            if draft[17]:  # ATT_FILE1 (檔案名稱)
                if all_att_file1:
                    all_att_file1 += "," + draft[17]
                else:
                    all_att_file1 = draft[17]
            if draft[18]:  # ATT_FILE2 (檔案路徑)
                if all_att_file2:
                    all_att_file2 += "," + draft[18]
                else:
                    all_att_file2 = draft[18]
        
        # 取得執行工作描述
        main_sop_desc_c = ''
        first_sopno = draft_results[0][7] if len(draft_results) > 0 and draft_results[0][7] else None
        if first_sopno:
            try:
                sop_sql = text("SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno")
                sop_result = db.execute(sop_sql, {"sopno": first_sopno}).fetchone()
                if sop_result and sop_result[0]:
                    main_sop_desc_c = sop_result[0]
                    if len(main_sop_desc_c) > 50:
                        main_sop_desc_c = main_sop_desc_c[:47] + '...'
            except Exception as e:
                logger.warning(f"無法取得 sopno {first_sopno} 的執行工作描述: {str(e)}")
                main_sop_desc_c = draft_results[0][8] if draft_results[0][8] else ''
                if len(main_sop_desc_c) > 50:
                    main_sop_desc_c = main_sop_desc_c[:47] + '...'
        
        current_date = now.strftime('%Y%m%d')
        current_time = now.strftime('%H:%M:%S')
        
        # 檢查是否為重新提交（tdr_master 已存在）
        check_master_sql = text("""
            SELECT COUNT(*) FROM jps.tdr_master 
            WHERE daily_no = :daily_no
        """)
        master_exists = db.execute(check_master_sql, {"daily_no": daily_no}).scalar() > 0
        
        if master_exists:
            logger.info(f"重新提交日報 {daily_no}，更新 master 資料")
            
            # 更新 master 資料
            update_master_sql = text("""
                UPDATE jps.tdr_master SET 
                    WORD_COUNT = :word_count,
                    XDATE = :current_date,
                    XTIME = :current_time,
                    ATT_FILE1 = :att_file1,
                    ATT_FILE2 = :att_file2,
                    SOP_DESC_C = :sop_desc_c
                WHERE daily_no = :daily_no
            """)
            
            db.execute(update_master_sql, {
                "word_count": total_word_count,
                "att_file1": all_att_file1,
                "att_file2": all_att_file2,
                "sop_desc_c": main_sop_desc_c,
                "current_date": current_date,
                "current_time": current_time,
                "daily_no": daily_no
            })
            
            # 刪除現有的 detail1、detail2 和檔案記錄
            delete_detail1_sql = text("DELETE FROM jps.tdr_detail1 WHERE daily_no = :daily_no")
            delete_detail2_sql = text("DELETE FROM jps.tdr_detail2 WHERE daily_no = :daily_no")
            # 根據 daily_no 的檔案ID模式刪除檔案（daily_no * 1000000 開頭的檔案）
            daily_no_prefix = int(daily_no) * 1000000
            delete_files_sql = text("""
                DELETE FROM jps.tdr_upload_file 
                WHERE id >= :daily_no_start AND id < :daily_no_end
            """)
            
            logger.info(f"開始刪除舊記錄：daily_no={daily_no}, empno={empno}, doc_date={doc_date}")
            
            detail1_deleted = db.execute(delete_detail1_sql, {"daily_no": daily_no}).rowcount
            detail2_deleted = db.execute(delete_detail2_sql, {"daily_no": daily_no}).rowcount
            files_deleted = db.execute(delete_files_sql, {
                "daily_no_start": daily_no_prefix,
                "daily_no_end": daily_no_prefix + 1000000
            }).rowcount
            
            logger.info(f"刪除結果：detail1={detail1_deleted}筆, detail2={detail2_deleted}筆, files={files_deleted}筆")
            
        else:
            logger.info(f"首次提交日報 {daily_no}，創建新的 master 資料")
            
            # 插入新的 tdr_master
            insert_master_sql = text("""
                INSERT INTO jps.tdr_master (
                    DAILY_NO, COCODE, EMPNO, DEPTNO, DOC_DATE, EMERGENCY, 
                    CLASSIFY, SCORE, XUSER, XDATE, XTIME, STATUS, LEADER, G_DEPTNO, EMPNAMEC, 
                    DEPTNAMEC, UPLOAD_SITE, EMPNAMEC_N, WFINBOX_STATUS, SOP_DESC_C, CUST_ENAME1, 
                    CUST_COMP_ABBV1, WORD_COUNT, ATT_FILE1, ATT_FILE2, openpath, openwebpage
                ) VALUES (
                    :daily_no, :cocode, :empno, :deptno, :doc_date, NULL, 
                    NULL, 0, :empnamec, :current_date, :current_time, 'N', :leader, :g_deptno, :empnamec, 
                    :deptnamec, 'D', :empnamec, 'N', :sop_desc_c, NULL, 
                    NULL, :word_count, :att_file1, :att_file2, '/MyReport/', 'viewed.aspx'
                )
            """)
            
            db.execute(insert_master_sql, {
                "daily_no": daily_no,
                "cocode": cocode,
                "empno": empno,
                "deptno": deptno,
                "doc_date": doc_date,
                "leader": leader,
                "g_deptno": g_deptno,
                "empnamec": empnamec,
                "deptnamec": deptnamec,
                "sop_desc_c": main_sop_desc_c,
                "word_count": total_word_count,
                "att_file1": all_att_file1,
                "att_file2": all_att_file2,
                "current_date": current_date,
                "current_time": current_time
            })
        
        # 按照 sopno 分組草稿，並為每組收集檔案
        sopno_groups = {}
        for draft in draft_results:
            sopno = draft[7]  # SOPNO
            if sopno not in sopno_groups:
                sopno_groups[sopno] = {
                    'drafts': [],
                    'files': []
                }
            sopno_groups[sopno]['drafts'].append(draft)
            
            # 收集此 draft 的檔案
            if draft[19]:  # FILES
                try:
                    files = json.loads(draft[19])
                    sopno_groups[sopno]['files'].extend(files)
                except:
                    pass
        
        # 為每個不同的 sopno 組合插入 tdr_detail1 並分配不同的 daily_sub_nos
        daily_sub_nos = 1
        sopno_to_daily_sub_nos = {}  # 記錄 sopno 對應的 daily_sub_nos
        
        for sopno, group_data in sopno_groups.items():
            drafts_in_group = group_data['drafts']
            group_files = group_data['files']
            
            # 記錄對應關係
            sopno_to_daily_sub_nos[sopno] = daily_sub_nos
            
            logger.info(f"處理 sopno={sopno}, daily_sub_nos={daily_sub_nos}, 檔案數量={len(group_files)}")
            
            # 插入 tdr_detail1 
            insert_detail1_sql = text("""
                INSERT INTO jps.tdr_detail1 (
                    DAILY_NO, DAILY_SUB_NOS, XUSER, XDATE, XTIME, CUNO1, COMP_SERNO1
                ) VALUES (
                    :daily_no, :daily_sub_nos, :empnamec, :current_date, :current_time, NULL, NULL
                )
            """)
            
            db.execute(insert_detail1_sql, {
                "daily_no": daily_no,
                "daily_sub_nos": daily_sub_nos,
                "empnamec": empnamec,
                "current_date": current_date,
                "current_time": current_time
            })
            
            # 插入 tdr_detail2 (每個工作計畫一條記錄)
            daily_job_nos = 1
            for draft in drafts_in_group:
                # 取得工作項目中文名稱
                work_item_names = []
                if draft[9] and draft[7]:  # WORK_ITEM_SEQ 和 SOPNO
                    seq_parts = str(draft[9]).split('/')
                    for seq in seq_parts:
                        if seq.strip():
                            work_item_sql = text("""
                                SELECT name FROM jps.tpm_sop_detail 
                                WHERE sopno = :sopno AND seq = :seq
                            """)
                            work_item_result = db.execute(work_item_sql, {
                                "sopno": draft[7],
                                "seq": seq.strip()
                            }).fetchone()
                            
                            if work_item_result and work_item_result[0]:
                                work_item_names.append(work_item_result[0])
                            else:
                                work_item_names.append(f"工作項目 {seq}")
                
                work_item_name = " / ".join(work_item_names) if work_item_names else str(draft[9])
                
                insert_detail2_sql = text("""
                    INSERT INTO jps.tdr_detail2 (
                        DAILY_NO, DAILY_SUB_NOS, DAILY_JOB_NOS, COCODE, EMPNO, SOP_CODE, STATUS,
                        XUSER, XDATE, XTIME, ITEMDESC1, PROD_CATE, EXETIME, ESTIMATE, ATTITUDE,
                        PROD_NO, SOLUT_SUBJ, SOLUT_STATUS, EMPNAME1, EMPNAME2, EMPNAME3, EMPNAME4, EMPNAME5,
                        PPS_SERVECOCODE, PPS_EMPNO, PPS_COCODE, PPS_DEPTNO, MEMO_COLLECT, MEMO,
                        PPS_EMPNAMEC, PLANNO, SOPNO
                    ) VALUES (
                        :daily_no, :daily_sub_nos, :daily_job_nos, :cocode, :empno, :work_item_name, 'N',
                        :empnamec, :current_date, :current_time, NULL, NULL, :execution_time_minutes, NULL, NULL,
                        NULL, NULL, NULL, '0', NULL, NULL, NULL, NULL,
                        :service_cocode, :service_empno, :service_cocode, :service_deptno, '1', :content,
                        :service_empnamec, :planno, :sopno
                    )
                """)
                
                db.execute(insert_detail2_sql, {
                    "daily_no": daily_no,
                    "daily_sub_nos": daily_sub_nos,
                    "daily_job_nos": daily_job_nos,
                    "cocode": cocode,
                    "empno": empno,
                    "work_item_name": work_item_name,
                    "empnamec": empnamec,
                    "content": draft[14],  # CONTENT
                    "execution_time_minutes": draft[15]/60,  # EXECUTION_TIME_MINUTES
                    "service_cocode": draft[10],  # SERVICE_COCODE
                    "service_empno": draft[11],   # SERVICE_EMPNO
                    "service_deptno": draft[13],  # SERVICE_DEPTNO
                    "service_empnamec": draft[12], # SERVICE_EMPNAMEC
                    "planno": draft[5] or '0',  # PLANNO
                    "sopno": draft[7],   # SOPNO
                    "current_date": current_date,
                    "current_time": current_time
                })
                
                daily_job_nos += 1
            
            daily_sub_nos += 1
        
        # 為每個 sopno 組處理其對應的檔案
        total_files_processed = 0
        for sopno, group_data in sopno_groups.items():
            group_files = group_data['files']
            corresponding_daily_sub_nos = sopno_to_daily_sub_nos[sopno]
            
            if group_files:
                logger.info(f"處理 sopno={sopno} (daily_sub_nos={corresponding_daily_sub_nos}) 的 {len(group_files)} 個檔案")
                for i, f in enumerate(group_files):
                    logger.info(f"  檔案{i}: {f}")
                
                LegacyReportServiceV2.process_files_for_specific_daily_sub_nos(
                    db=db,
                    daily_no=daily_no,
                    daily_sub_nos=corresponding_daily_sub_nos,
                    empno=empno,
                    cocode=cocode,
                    doc_date=doc_date,
                    files=group_files
                )
                total_files_processed += len(group_files)
                logger.info(f"sopno={sopno} 檔案處理完成")
            else:
                logger.info(f"sopno={sopno} (daily_sub_nos={corresponding_daily_sub_nos}) 沒有檔案")
        
        logger.info(f"檔案處理完成，總共處理 {total_files_processed} 個檔案")
        
        # 更新所有暫存狀態為已提交
        update_draft_sql = text("""
            UPDATE jps.tdr_draft SET STATUS = 'S' WHERE DAILY_NO = :daily_no
        """)
        db.execute(update_draft_sql, {"daily_no": daily_no})
        
        db.commit()
        logger.info(f"日報 {daily_no} 上傳成功，包含 {len(draft_results)} 個工作項目")
        
        return {
            "success": True,
            "daily_no": daily_no,
            "message": "日報上傳成功",
            "work_items_count": len(draft_results),
            "upload_time": f"{current_date} {current_time}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"上傳日報失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"日報上傳失敗: {str(e)}")

@router.get("/execution-works")
async def get_execution_works(
    empno: str = Query(..., description="員工編號"),
    planno: Optional[str] = Query(None, description="專案編號（可選）"),
    db: Session = Depends(get_legacy_db)
):
    """取得執行工作和工作項目（保留舊API以向後兼容）"""
    try:
        from sqlalchemy import text
        
        if planno and planno.strip():
            # 有選擇工作計畫時的查詢 - 需要JOIN tpm_sop取得執行工作描述
            sql = text("""
                SELECT t.sopno, s.sop_desc_c, d.seq, d.name
                FROM jps.tjp_master t
                LEFT JOIN jps.tpm_sop s ON t.sopno = s.sopno
                LEFT JOIN jps.tpm_sop_detail d ON s.sopno = d.sopno
                WHERE t.planno = :planno
                ORDER BY t.sopno, d.seq
            """)
            result = db.execute(sql, {"planno": planno})
        else:
            # 沒有工作計畫時的查詢（使用你提供的SQL）
            sql = text("""
                SELECT A.sopno, A.sop_desc_c, B.seq, B.name
                FROM (
                    SELECT sopno, sop_desc_c
                    FROM jps.tpm_sop
                    WHERE cocode IN ('A','E','H','M','K','P','L','R','G','J07','J09','J10','J11','S','J15','J16','J17','J18','J19')
                    AND xstatus = '1'
                    AND (deptno IS NULL OR deptno = '00253')
                    AND (sop_role IS NULL OR sop_role = '技術同仁')
                    UNION
                    SELECT sopno, sop_desc_c
                    FROM jps.tpm_sop
                    WHERE sopno IN (
                        SELECT sopno FROM jps.TJP_MASTER WHERE empno = :empno
                        UNION ALL
                        SELECT b.sopno FROM jps.tjp_partner a, jps.TJP_MASTER b
                        WHERE A.PLANNO = b.planno AND a.part_empno = :empno
                    )
                ) A
                LEFT JOIN jps.tpm_sop_detail B ON A.sopno = B.sopno
                ORDER BY A.sopno, B.seq
            """)
            result = db.execute(sql, {"empno": empno})
        
        execution_works = []
        current_sop = None
        
        for row in result.fetchall():
            # 兩種查詢現在都返回相同格式：sopno, sop_desc_c, seq, name
            sopno = row[0]
            sop_desc_c = row[1]
            seq = row[2] if len(row) > 2 else None
            work_item_name = row[3] if len(row) > 3 else None
            
            # 找或創建執行工作記錄
            if current_sop != sopno:
                execution_works.append({
                    "sopno": sopno,
                    "sop_desc_c": sop_desc_c or f"執行工作 {sopno}",
                    "work_items": []
                })
                current_sop = sopno
            
            # 添加工作項目
            if seq is not None and work_item_name:
                execution_works[-1]["work_items"].append({
                    "seq": seq,
                    "name": work_item_name
                })
        
        return execution_works
    except Exception as e:
        logger.error(f"Error getting execution works: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得執行工作失敗: {str(e)}")

# === Projects API (前端相容性) ===

# 創建一個專門的 router 處理 /api/projects/ 端點
projects_router = APIRouter(prefix="/projects", tags=["projects"])

@projects_router.get("/")
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得專案/工作計畫列表"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        
        # 取得工作計畫列表
        projects_sql = text("""
            SELECT DISTINCT A.planno, A.plan_subj_c
            FROM jps.tjp_master A
            WHERE (A.empno = :empno OR A.pm_empno = :empno)
            AND (A.plan_date2 IS NULL OR A.plan_date2 >= TO_CHAR(CURRENT_DATE,'YYYYMMDD'))
            ORDER BY A.planno DESC
        """)
        
        result = db.execute(projects_sql, {"empno": empno})
        
        projects = []
        for row in result.fetchall():
            projects.append({
                "id": row[0],  # planno
                "plan_subj_c": row[1] or f"工作計畫 {row[0]}",
                "name": row[1] or f"工作計畫 {row[0]}"  # 別名，以防前端期待 name 欄位
            })
        
        return projects
        
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得專案列表失敗: {str(e)}")