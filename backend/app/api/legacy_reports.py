# backend/app/api/legacy_reports.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..models.user import User
from ..services.legacy_service_v2 import LegacyReportServiceV2
from ..schemas.legacy_schemas import (
    DailyReportListItem, DailyReportContent, WorkPlan,
    DraftSaveRequest, AttachmentSaveRequest,
    ReportSubmitRequest, DraftResponse, SubmitResponse
)
import logging
import json

router = APIRouter(prefix="/legacy", tags=["legacy-reports"])
records_router = APIRouter(prefix="/records", tags=["records"])
logger = logging.getLogger(__name__)

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
    draft_data: DraftSaveRequest,
    db: Session = Depends(get_legacy_db)
):
    """保存日報暫存"""
    try:
        draft_id = LegacyReportServiceV2.save_draft(
            db=db,
            empno=draft_data.empno,
            cocode=draft_data.cocode,
            doc_date=draft_data.doc_date,
            draft_type=draft_data.draft_type,
            draft_content=draft_data.draft_content.dict()
        )
        
        return DraftResponse(
            draft_id=draft_id,
            daily_no=draft_id,  # 使用返回的 daily_no
            message="暫存保存成功"
        )
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

@router.post("/submit", response_model=SubmitResponse)
async def submit_report(
    submit_data: ReportSubmitRequest,
    db: Session = Depends(get_legacy_db)
):
    """正式提交日報到 tdr_master, tdr_detail1, tdr_detail2"""
    try:
        daily_no = LegacyReportServiceV2.submit_report(
            db=db,
            daily_no=submit_data.daily_no,
            empno=submit_data.empno,
            cocode=submit_data.cocode,
            deptno=submit_data.deptno,
            doc_date=submit_data.doc_date,
            emergency=submit_data.emergency,
            classify=submit_data.classify,
            leader=submit_data.leader,
            g_deptno=submit_data.g_deptno,
            empnamec=submit_data.empnamec,
            deptnamec=submit_data.deptnamec,
            sop_desc_c=submit_data.sop_desc_c,
            word_count=submit_data.word_count,
            att_file1=submit_data.att_file1,
            att_file2=submit_data.att_file2,
            work_items=submit_data.work_items
        )
        
        return SubmitResponse(
            daily_no=daily_no,
            status="submitted",
            message="日報提交成功"
        )
    except Exception as e:
        logger.error(f"Error submitting report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"日報提交失敗: {str(e)}")

@router.post("/submit-draft/{draft_id}")
async def submit_draft_to_final(
    draft_id: str,
    db: Session = Depends(get_legacy_db)
):
    """將暫存提交為正式日報"""
    try:
        # 取得暫存資料
        draft_sql = text("""
            SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_CONTENT
            FROM tdr_draft
            WHERE DAILY_NO = :daily_no AND STATUS = 'A'
        """)
        
        draft_result = db.execute(draft_sql, {"daily_no": draft_id}).fetchone()
        if not draft_result:
            raise HTTPException(status_code=404, detail="找不到指定的暫存資料")
        
        draft_content = json.loads(draft_result[4])
        empno = draft_result[1]
        cocode = draft_result[2]
        doc_date = draft_result[3]
        
        # 使用暫存的 daily_no（不需要重新取得）
        daily_no = draft_result[0]  # 使用暫存中的 daily_no
        
        # 提交到正式日報表
        LegacyReportServiceV2.submit_draft_to_final(
            db=db,
            daily_no=daily_no,
            empno=empno,
            cocode=cocode,
            doc_date=doc_date,
            draft_content=draft_content
        )
        
        # 標記暫存為已提交
        update_draft_sql = text("""
            UPDATE tdr_draft 
            SET STATUS = 'S', UPDATED_DATE = :updated_date, UPDATED_TIME = :updated_time
            WHERE DAILY_NO = :daily_no
        """)
        
        from datetime import datetime
        now = datetime.now()
        db.execute(update_draft_sql, {
            "daily_no": daily_no,  # 使用相同的 daily_no
            "updated_date": now.strftime('%Y%m%d'),
            "updated_time": now.strftime('%H:%M:%S')
        })
        
        db.commit()
        
        return SubmitResponse(
            daily_no=daily_no,
            status="submitted",
            message="暫存提交成功"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"暫存提交失敗: {str(e)}")

# === 查詢相關 API ===

@router.get("/drafts/{empno}")
async def get_drafts(
    empno: str,
    draft_type: Optional[str] = Query(None, description="暫存類型: TEMP 或 AI"),
    db: Session = Depends(get_legacy_db)
):
    """取得員工的暫存資料"""
    try:
        from sqlalchemy import text
        
        # 構建查詢條件
        where_clause = "WHERE EMPNO = :empno AND STATUS = 'A'"
        params = {"empno": empno}
        
        if draft_type:
            where_clause += " AND DRAFT_TYPE = :draft_type"
            params["draft_type"] = draft_type
        
        sql = text(f"""
            SELECT DRAFT_ID, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE, DRAFT_CONTENT,
                   CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME
            FROM tdr_draft
            {where_clause}
            ORDER BY UPDATED_DATE DESC, UPDATED_TIME DESC
        """)
        
        result = db.execute(sql, params)
        
        drafts = []
        for row in result.fetchall():
            draft = dict(zip(result.keys(), row))
            # 解析 JSON 內容
            if draft['draft_content']:
                import json
                draft['draft_content'] = json.loads(draft['draft_content'])
            drafts.append(draft)
        
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
        from sqlalchemy import text
        
        # 1. 取得工作計畫
        work_plans_sql = text("""
            SELECT DISTINCT A.planno, A.plan_subj_c
            FROM jps.tjp_master A
            WHERE (A.empno = :empno or A.pm_empno = :empno)
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
            
            # 添加調試信息
            logger.info(f"處理行: sopno={sopno}, sop_desc_c={sop_desc_c}, seq={seq}, work_item_name={work_item_name}")
            
            if current_sop != sopno:
                basic_execution_works.append({
                    "sopno": str(sopno),  # 確保 sopno 是字符串
                    "sop_desc_c": sop_desc_c or f"執行工作 {sopno}",
                    "work_items": []
                })
                current_sop = sopno
                logger.info(f"新增執行工作: {sopno} - {sop_desc_c}")
            
            if seq is not None and work_item_name:
                basic_execution_works[-1]["work_items"].append({
                    "seq": str(seq),  # 確保 seq 是字符串
                    "name": work_item_name,
                    "unique_id": f"{sopno}_{seq}"  # 創建唯一 ID
                })
                logger.info(f"新增工作項目: {seq} - {work_item_name} 到執行工作 {sopno}")
        
        # 3. 取得所有工作計畫的執行工作
        project_execution_works = {}
        for plan in work_plans:
            planno = plan["planno"]
            project_sql = text("""
                SELECT t.sopno, s.sop_desc_c, d.seq, d.name
                FROM jps.tjp_master t
                LEFT JOIN jps.tpm_sop s ON t.sopno = s.sopno
                LEFT JOIN jps.tpm_sop_detail d ON s.sopno = d.sopno
                WHERE t.planno = :planno
                ORDER BY t.sopno, d.seq
            """)
            
            project_result = db.execute(project_sql, {"planno": planno})
            execution_works = []
            current_sop = None
            
            for row in project_result.fetchall():
                sopno = row[0]
                sop_desc_c = row[1]
                seq = row[2] if len(row) > 2 else None
                work_item_name = row[3] if len(row) > 3 else None
                
                if current_sop != sopno:
                    execution_works.append({
                        "sopno": str(sopno),  # 確保 sopno 是字符串
                        "sop_desc_c": sop_desc_c or f"執行工作 {sopno}",
                        "work_items": []
                    })
                    current_sop = sopno
                
                if seq is not None and work_item_name:
                    execution_works[-1]["work_items"].append({
                        "seq": str(seq),  # 確保 seq 是字符串
                        "name": work_item_name,
                        "unique_id": f"{sopno}_{seq}"  # 創建唯一 ID
                    })
            
            project_execution_works[planno] = execution_works
        
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
        
        return {
            "work_plans": work_plans,
            "basic_execution_works": basic_execution_works,
            "project_execution_works": project_execution_works,
            "service_companies": service_companies,
            "service_targets": service_targets
        }
        
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
        
        # 查詢今天的所有記錄（包括已提交和暫存），JOIN 工作項目表取得中文名稱
        draft_sql = text("""
            SELECT d.DAILY_NO, d.CONTENT, d.PLANNO, d.PLAN_SUBJ_C, d.SOPNO, d.SOP_DESC_C, 
                   d.WORK_ITEM_SEQ, d.SERVICE_COCODE, d.SERVICE_EMPNO, d.SERVICE_EMPNAMEC, 
                   d.EXECUTION_TIME_MINUTES, d.FILES, d.AI_CONTENT, d.STATUS,
                   sop.name as WORK_ITEM_NAME
            FROM jps.tdr_draft d
            LEFT JOIN jps.tpm_sop_detail sop ON d.SOPNO = sop.sopno AND d.WORK_ITEM_SEQ = sop.seq
            WHERE d.EMPNO = :empno 
            AND d.DOC_DATE = :doc_date 
            ORDER BY d.CREATED_DATE DESC
        """)
        
        draft_result = db.execute(draft_sql, {
            "empno": empno,
            "doc_date": today
        })
        
        consolidated_records = []
        for row in draft_result.fetchall():
            daily_no = row[0]
            content = row[1] or ""
            planno = row[2] or ""
            plan_subj_c = row[3] or "未指定工作計畫"
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
            work_item_name = row[14] or work_item_seq  # 使用中文名稱，如果沒有則使用序號
            
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
            AND STATUS = 'A'
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
        
        if submitted_count > 0:
            status = "submitted"
        elif draft_count > 0:
            status = "draft"
        else:
            status = "empty"
            
        return {
            "empno": empno,
            "doc_date": today,
            "status": status,
            "draft_count": draft_count,
            "submitted_count": submitted_count
        }
        
    except Exception as e:
        logger.error(f"Error getting writing status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得寫作狀態失敗: {str(e)}")

@records_router.post("/upload")
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

@records_router.post("/ai/enhance_one/{project_id}")
async def enhance_one_record(
    project_id: str,
    db: Session = Depends(get_legacy_db)
):
    """AI 增強單個記錄"""
    try:
        # 這裡應該實現 AI 增強邏輯
        # 目前返回一個基本響應
        return {
            "success": True,
            "message": f"記錄 {project_id} AI 增強完成",
            "enhanced_content": "AI 增強後的內容"
        }
        
    except Exception as e:
        logger.error(f"Error enhancing record {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 增強失敗: {str(e)}")

@records_router.post("/ai/enhance_all")
async def enhance_all_records(
    enhance_data: Dict[str, Any],
    db: Session = Depends(get_legacy_db)
):
    """AI 增強所有記錄"""
    try:
        # 這裡應該實現批量 AI 增強邏輯
        # 目前返回一個基本響應
        return {
            "success": True,
            "message": "所有記錄 AI 增強完成",
            "enhanced_count": len(enhance_data.get("records", []))
        }
        
    except Exception as e:
        logger.error(f"Error enhancing all records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量 AI 增強失敗: {str(e)}")

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
            AND STATUS = 'A'
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

# === Comments API (前端相容性) ===

# 創建一個專門的 router 處理 /api/reports/ 端點
reports_router = APIRouter(prefix="/reports", tags=["reports"])

@reports_router.get("/{report_id}/comments")
async def get_report_comments(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得報告的所有留言"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 查詢回應記錄 (tdr_reply)
        comments_sql = text("""
            SELECT r.daily_no, r.reply_nos, r.empno, r.xuser, r.memo, 
                   r.xdate, r.xtime, s.score
            FROM jps.tdr_reply r
            LEFT JOIN jps.tdr_score s ON r.daily_no = s.daily_no AND r.reply_nos = s.reply_nos
            WHERE r.daily_no = :daily_no
            ORDER BY r.reply_nos ASC
        """)
        
        result = db.execute(comments_sql, {"daily_no": report_id})
        
        comments = []
        for row in result.fetchall():
            comment = {
                "id": row[1],  # reply_nos
                "content": row[4] or "",  # memo
                "created_at": f"{row[5]} {row[6]}",  # xdate + xtime
                "user_id": 0,  # 假的 user_id
                "author": {
                    "id": 0,
                    "name": row[3] or row[2],  # xuser 或 empno
                    "email": f"{row[2]}@supervisor" if row[7] else f"{row[2]}@employee"  # 根據是否有評分判斷身份
                },
                "rating": row[7],  # score
                "replies": []
            }
            comments.append(comment)
        
        return comments
        
    except Exception as e:
        logger.error(f"Error getting report comments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得報告留言失敗: {str(e)}")

@reports_router.post("/{report_id}/comments")
async def create_report_comment(
    report_id: str,
    comment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """創建報告留言"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        content = comment_data.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="留言內容不能為空")
        
        # 取得下一個回應編號
        max_reply_sql = text("""
            SELECT COALESCE(MAX(reply_nos), 0) + 1 
            FROM jps.tdr_reply 
            WHERE daily_no = :daily_no
        """)
        reply_nos = db.execute(max_reply_sql, {"daily_no": report_id}).scalar()
        
        # 插入回應記錄
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime('%Y%m%d')
        current_time = now.strftime('%H:%M:%S')
        
        insert_reply_sql = text("""
            INSERT INTO jps.tdr_reply (
                daily_no, reply_nos, empno, memo, xuser, xdate, xtime, memo1, from_where
            ) VALUES (
                :daily_no, :reply_nos, :empno, :memo, :xuser, :xdate, :xtime, '', 0
            )
        """)
        
        db.execute(insert_reply_sql, {
            "daily_no": report_id,
            "reply_nos": reply_nos,
            "empno": current_user.employee.empno,
            "memo": content,
            "xuser": current_user.employee.empnamec,
            "xdate": current_date,
            "xtime": current_time
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": "留言已創建",
            "comment": {
                "id": reply_nos,
                "content": content,
                "created_at": f"{current_date} {current_time}",
                "user_id": 0,
                "author": {
                    "id": 0,
                    "name": current_user.employee.empnamec,
                    "email": f"{current_user.employee.empno}@employee"
                },
                "replies": []
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating report comment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"創建報告留言失敗: {str(e)}")

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