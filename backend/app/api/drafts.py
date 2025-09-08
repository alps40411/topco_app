# backend/app/api/drafts.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..schemas.user import User

router = APIRouter(tags=["Drafts"])
logger = logging.getLogger(__name__)

@router.get("/")
async def get_drafts(
    draft_type: Optional[str] = Query(None, description="草稿類型: TEMP 或 AI"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得用戶的草稿列表"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        
        # 構建查詢條件
        where_clause = "WHERE EMPNO = :empno AND STATUS = 'A'"
        params = {"empno": empno}
        
        if draft_type:
            where_clause += " AND DRAFT_TYPE = :draft_type"
            params["draft_type"] = draft_type
        
        sql = text(f"""
            SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE, DRAFT_CONTENT,
                   CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME
            FROM jps.tdr_draft
            {where_clause}
            ORDER BY UPDATED_DATE DESC, UPDATED_TIME DESC
        """)
        
        result = db.execute(sql, params)
        
        drafts = []
        for row in result.fetchall():
            # 解析 JSON 內容
            draft_content = {}
            if row[5]:  # DRAFT_CONTENT
                try:
                    draft_content = json.loads(row[5])
                except json.JSONDecodeError:
                    draft_content = {}
            
            # 格式化日期
            doc_date_str = row[3]  # DOC_DATE
            formatted_date = f"{doc_date_str[:4]}-{doc_date_str[4:6]}-{doc_date_str[6:8]}" if doc_date_str else ""
            
            drafts.append({
                "id": row[0],  # DAILY_NO
                "empno": row[1],
                "cocode": row[2],
                "doc_date": formatted_date,
                "draft_type": row[4],
                "draft_content": draft_content,
                "created_at": f"{row[6]} {row[7]}" if row[6] and row[7] else "",
                "updated_at": f"{row[8]} {row[9]}" if row[8] and row[9] else ""
            })
        
        return {
            "success": True,
            "data": drafts,
            "total": len(drafts)
        }
        
    except Exception as e:
        logger.error(f"Error getting drafts: {str(e)}")
        raise HTTPException(status_code=500, detail="取得草稿列表失敗")

@router.get("/{draft_id}")
async def get_draft_detail(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得草稿詳情"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        sql = text("""
            SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE, DRAFT_CONTENT,
                   CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME, STATUS
            FROM jps.tdr_draft
            WHERE DAILY_NO = :draft_id AND EMPNO = :empno
        """)
        
        result = db.execute(sql, {
            "draft_id": draft_id,
            "empno": current_user.employee.empno
        }).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="找不到指定的草稿")
        
        # 檢查是否為當前用戶的草稿
        if result[1] != current_user.employee.empno:
            raise HTTPException(status_code=403, detail="無權限存取此草稿")
        
        # 解析 JSON 內容
        draft_content = {}
        if result[5]:  # DRAFT_CONTENT
            try:
                draft_content = json.loads(result[5])
            except json.JSONDecodeError:
                draft_content = {}
        
        # 格式化日期
        doc_date_str = result[3]
        formatted_date = f"{doc_date_str[:4]}-{doc_date_str[4:6]}-{doc_date_str[6:8]}" if doc_date_str else ""
        
        return {
            "success": True,
            "data": {
                "id": result[0],  # DAILY_NO
                "empno": result[1],
                "cocode": result[2],
                "doc_date": formatted_date,
                "draft_type": result[4],
                "draft_content": draft_content,
                "created_at": f"{result[6]} {result[7]}" if result[6] and result[7] else "",
                "updated_at": f"{result[8]} {result[9]}" if result[8] and result[9] else "",
                "status": result[10]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting draft detail: {str(e)}")
        raise HTTPException(status_code=500, detail="取得草稿詳情失敗")

@router.post("/")
async def create_draft(
    draft_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """創建新草稿"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 取得新的 daily_no
        daily_no_sql = text("SELECT seq_tdr_master.nextval FROM dual")
        daily_no = db.execute(daily_no_sql).scalar()
        
        # 準備插入資料
        empno = current_user.employee.empno
        cocode = draft_data.get("cocode", current_user.employee.cocode or "A")
        doc_date = draft_data.get("doc_date", datetime.now().strftime('%Y%m%d'))
        draft_type = draft_data.get("draft_type", "TEMP")
        draft_content = json.dumps(draft_data.get("draft_content", {}), ensure_ascii=False)
        
        now = datetime.now()
        created_date = now.strftime('%Y%m%d')
        created_time = now.strftime('%H:%M:%S')
        
        # 插入草稿記錄
        insert_sql = text("""
            INSERT INTO jps.tdr_draft (
                DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE, DRAFT_CONTENT,
                STATUS, CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME
            ) VALUES (
                :daily_no, :empno, :cocode, :doc_date, :draft_type, :draft_content,
                'A', :created_date, :created_time, :updated_date, :updated_time
            )
        """)
        
        db.execute(insert_sql, {
            "daily_no": str(daily_no),
            "empno": empno,
            "cocode": cocode,
            "doc_date": doc_date,
            "draft_type": draft_type,
            "draft_content": draft_content,
            "created_date": created_date,
            "created_time": created_time,
            "updated_date": created_date,
            "updated_time": created_time
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": "草稿保存成功",
            "data": {
                "draft_id": str(daily_no),
                "daily_no": str(daily_no)
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating draft: {str(e)}")
        raise HTTPException(status_code=500, detail="創建草稿失敗")

@router.put("/{draft_id}")
async def update_draft(
    draft_id: str,
    draft_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """更新草稿"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 檢查草稿是否存在且屬於當前用戶
        check_sql = text("""
            SELECT EMPNO FROM jps.tdr_draft
            WHERE DAILY_NO = :draft_id AND STATUS = 'A'
        """)
        
        result = db.execute(check_sql, {"draft_id": draft_id}).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="找不到指定的草稿")
        
        if result[0] != current_user.employee.empno:
            raise HTTPException(status_code=403, detail="無權限修改此草稿")
        
        # 更新草稿內容
        draft_content = json.dumps(draft_data.get("draft_content", {}), ensure_ascii=False)
        
        now = datetime.now()
        updated_date = now.strftime('%Y%m%d')
        updated_time = now.strftime('%H:%M:%S')
        
        update_sql = text("""
            UPDATE jps.tdr_draft 
            SET DRAFT_CONTENT = :draft_content,
                UPDATED_DATE = :updated_date,
                UPDATED_TIME = :updated_time
            WHERE DAILY_NO = :draft_id
        """)
        
        result = db.execute(update_sql, {
            "draft_id": draft_id,
            "draft_content": draft_content,
            "updated_date": updated_date,
            "updated_time": updated_time
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="更新失敗，找不到指定的草稿")
        
        db.commit()
        
        return {
            "success": True,
            "message": "草稿更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating draft: {str(e)}")
        raise HTTPException(status_code=500, detail="更新草稿失敗")

@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """刪除草稿（軟刪除）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 檢查草稿是否存在且屬於當前用戶
        check_sql = text("""
            SELECT EMPNO FROM jps.tdr_draft
            WHERE DAILY_NO = :draft_id AND STATUS = 'A'
        """)
        
        result = db.execute(check_sql, {"draft_id": draft_id}).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="找不到指定的草稿")
        
        if result[0] != current_user.employee.empno:
            raise HTTPException(status_code=403, detail="無權限刪除此草稿")
        
        # 軟刪除草稿
        now = datetime.now()
        delete_sql = text("""
            UPDATE jps.tdr_draft 
            SET STATUS = 'D', 
                UPDATED_DATE = :updated_date, 
                UPDATED_TIME = :updated_time
            WHERE DAILY_NO = :draft_id
        """)
        
        db.execute(delete_sql, {
            "draft_id": draft_id,
            "updated_date": now.strftime('%Y%m%d'),
            "updated_time": now.strftime('%H:%M:%S')
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": "草稿刪除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting draft: {str(e)}")
        raise HTTPException(status_code=500, detail="刪除草稿失敗")

@router.post("/{draft_id}/submit")
async def submit_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """提交草稿為正式日報"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 取得草稿資料
        draft_sql = text("""
            SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_CONTENT
            FROM jps.tdr_draft
            WHERE DAILY_NO = :daily_no AND STATUS = 'A' AND EMPNO = :empno
        """)
        
        draft_result = db.execute(draft_sql, {
            "daily_no": draft_id,
            "empno": current_user.employee.empno
        }).fetchone()
        
        if not draft_result:
            raise HTTPException(status_code=404, detail="找不到指定的草稿")
        
        # 解析草稿內容
        try:
            draft_content = json.loads(draft_result[4]) if draft_result[4] else {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="草稿內容格式錯誤")
        
        # 這裡應該調用提交服務將草稿轉為正式日報
        # 為了簡化，暫時只標記草稿為已提交狀態
        
        # 標記草稿為已提交
        update_draft_sql = text("""
            UPDATE jps.tdr_draft 
            SET STATUS = 'S', 
                UPDATED_DATE = :updated_date, 
                UPDATED_TIME = :updated_time
            WHERE DAILY_NO = :daily_no
        """)
        
        now = datetime.now()
        db.execute(update_draft_sql, {
            "daily_no": draft_id,
            "updated_date": now.strftime('%Y%m%d'),
            "updated_time": now.strftime('%H:%M:%S')
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": "草稿提交成功",
            "data": {
                "daily_no": draft_id,
                "status": "submitted"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting draft: {str(e)}")
        raise HTTPException(status_code=500, detail="提交草稿失敗")

@router.get("/today/consolidated")
async def get_today_consolidated_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得今日合併記錄（相容於現有前端API）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        today = datetime.now().strftime('%Y%m%d')
        
        # 查詢今天的所有記錄，JOIN 工作項目表取得中文名稱
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
            # 解析檔案
            try:
                files = json.loads(row[11]) if row[11] else []
            except:
                files = []
            
            # 構建服務對象名稱
            service_target_name = ""
            if row[9] and row[8]:  # service_empnamec and service_empno
                service_target_name = f"{row[9]}({row[8]})"
            
            consolidated_records.append({
                "project": {
                    "id": row[2],  # planno
                    "plan_subj_c": row[3] or "基本工作項目"
                },
                "execution_work_name": row[5] or "",  # sop_desc_c
                "work_item_name": row[14] or row[6] or "",  # work_item_name 或 work_item_seq
                "service_company_name": row[7] or "",  # service_cocode
                "service_target_name": service_target_name,
                "content": row[1] or "",  # content
                "files": files,
                "record_count": 1,
                "ai_content": row[12],  # ai_content
                "total_execution_time_minutes": row[10] or 0  # execution_time_minutes
            })
        
        return {
            "success": True,
            "data": consolidated_records
        }
        
    except Exception as e:
        logger.error(f"Error getting today consolidated records: {str(e)}")
        raise HTTPException(status_code=500, detail="取得今日合併記錄失敗")

@router.get("/writing-status")
async def get_writing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得寫作狀態（相容於現有前端API）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        today = datetime.now().strftime('%Y%m%d')
        
        # 檢查是否有草稿
        draft_count_sql = text("""
            SELECT COUNT(*) 
            FROM jps.tdr_draft 
            WHERE EMPNO = :empno AND DOC_DATE = :doc_date AND STATUS = 'A'
        """)
        
        draft_count = db.execute(draft_count_sql, {
            "empno": empno,
            "doc_date": today
        }).scalar()
        
        # 檢查是否已提交
        submitted_count_sql = text("""
            SELECT COUNT(*) 
            FROM jps.tdr_master 
            WHERE EMPNO = :empno AND DOC_DATE = :doc_date
        """)
        
        submitted_count = db.execute(submitted_count_sql, {
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
            "success": True,
            "data": {
                "empno": empno,
                "doc_date": today,
                "status": status,
                "draft_count": draft_count,
                "submitted_count": submitted_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting writing status: {str(e)}")
        raise HTTPException(status_code=500, detail="取得寫作狀態失敗")

@router.put("/by-daily-sopno/{daily_no}/{sopno}")
async def update_draft_by_daily_sopno(
    daily_no: str,
    sopno: str,
    update_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """使用daily_no + sopno精確更新單一草稿記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        
        # 使用daily_no + sopno精確查找要更新的記錄
        find_sql = text("""
            SELECT DAILY_NO, PLANNO, SOPNO, SOP_DESC_C 
            FROM jps.tdr_draft 
            WHERE DAILY_NO = :daily_no AND SOPNO = :sopno AND EMPNO = :empno AND STATUS = 'A'
        """)
        
        record_result = db.execute(find_sql, {
            "daily_no": daily_no,
            "sopno": sopno,
            "empno": empno
        }).fetchone()
        
        if not record_result:
            raise HTTPException(status_code=404, detail=f"找不到daily_no {daily_no} + sopno {sopno} 的記錄")
        
        planno = record_result[1]
        sop_desc_c = record_result[3]
        
        # 準備更新數據
        content = update_data.get('content', '')
        files = update_data.get('files', [])
        files_json = json.dumps(files) if files else "[]"
        
        # 更新指定的記錄 - 使用daily_no + sopno確保精確性
        update_sql = text("""
            UPDATE jps.tdr_draft 
            SET CONTENT = :content,
                FILES = :files,
                UPDATED_DATE = TO_CHAR(sysdate, 'YYYYMMDD'),
                UPDATED_TIME = TO_CHAR(sysdate, 'HH24:MI:SS')
            WHERE DAILY_NO = :daily_no AND SOPNO = :sopno AND EMPNO = :empno
        """)
        
        db.execute(update_sql, {
            "content": content,
            "files": files_json,
            "daily_no": daily_no,
            "sopno": sopno,
            "empno": empno
        })
        
        db.commit()
        
        logger.info(f"成功更新記錄: daily_no={daily_no}, sopno={sopno}, empno={empno}")
        
        return {
            "success": True,
            "message": f"執行工作 {sop_desc_c} 記錄更新成功",
            "data": {
                "daily_no": daily_no,
                "sopno": sopno,
                "planno": planno,
                "content": content,
                "files": files
            }
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating draft by sopno {sopno}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新記錄失敗: {str(e)}")