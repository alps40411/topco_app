# backend/app/api/ai.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import logging
from datetime import datetime

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..schemas.user import User
from ..services.azure_ai_service import get_ai_enhanced_report

router = APIRouter(tags=["AI Services"])
logger = logging.getLogger(__name__)

@router.post("/suggestions/{report_id}")
async def get_ai_suggestions(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得日報的 AI 建議"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 查詢日報詳細內容
        report_sql = text("""
            SELECT tm.empno, tm.empnamec, tm.sop_desc_c,
                   td.itemdesc1, td.memo, td.cuno_msg, td.ques_desc, td.solut_desc,
                   td.comp_desc, td.cuno_subj, td.ques_subj, td.solut_subj
            FROM jps.tdr_master tm
            LEFT JOIN jps.tdr_detail2 td ON tm.daily_no = td.daily_no
            WHERE tm.daily_no = :daily_no
            ORDER BY td.daily_sub_nos
        """)
        
        report_results = db.execute(report_sql, {"daily_no": report_id}).fetchall()
        
        if not report_results:
            raise HTTPException(status_code=404, detail="找不到指定的日報")
        
        # 組合報告內容
        employee_name = report_results[0][1]  # empnamec
        report_content_parts = []
        
        for row in report_results:
            itemdesc1 = row[3] or ""      # 工作項目描述
            memo = row[4] or ""           # 備註
            cuno_msg = row[5] or ""       # 客戶訊息
            ques_desc = row[6] or ""      # 問題描述
            solut_desc = row[7] or ""     # 解決方案描述
            comp_desc = row[8] or ""      # 抱怨描述
            cuno_subj = row[9] or ""      # 客戶主旨
            ques_subj = row[10] or ""     # 問題主旨
            solut_subj = row[11] or ""    # 解決方案主旨
            
            if itemdesc1:
                report_content_parts.append(f"工作項目: {itemdesc1}")
            if cuno_subj:
                report_content_parts.append(f"客戶主旨: {cuno_subj}")
            if cuno_msg:
                report_content_parts.append(f"客戶內容: {cuno_msg}")
            if ques_subj:
                report_content_parts.append(f"問題主旨: {ques_subj}")
            if ques_desc:
                report_content_parts.append(f"問題描述: {ques_desc}")
            if solut_subj:
                report_content_parts.append(f"解決方案主旨: {solut_subj}")
            if solut_desc:
                report_content_parts.append(f"解決方案: {solut_desc}")
            if comp_desc:
                report_content_parts.append(f"抱怨內容: {comp_desc}")
            if memo:
                report_content_parts.append(f"備註: {memo}")
        
        report_content = "\n".join(report_content_parts)
        
        # 生成 AI 建議
        if not report_content.strip():
            # 沒有具體內容時的通用建議
            suggestions = _get_fallback_suggestions()
        else:
            # 使用 AI 服務生成建議
            suggestions = await _generate_supervisor_reply_suggestions(
                report_content=report_content,
                employee_name=employee_name
            )
        
        return {
            "success": True,
            "data": {
                "suggestions": suggestions,
                "report_id": report_id,
                "employee_name": employee_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail="生成 AI 建議失敗")

def _get_fallback_suggestions():
    """當無法生成 AI 建議時的備用建議"""
    return [
        "感謝您的詳細報告，工作內容清楚明瞭。",
        "您的工作態度積極，請繼續保持。",
        "建議在未來的工作中，可以更詳細地記錄遇到的問題和解決方案。",
        "工作執行情況良好，請注意時間管理。",
        "您的客戶服務表現出色，值得讚許。"
    ]

async def _generate_supervisor_reply_suggestions(report_content: str, employee_name: str):
    """生成主管回覆建議"""
    # 這裡應該整合實際的 AI 服務
    # 目前返回模擬的建議
    suggestions = [
        f"感謝 {employee_name} 的詳細工作報告。",
        "您的工作內容記錄完整，執行情況良好。",
        "建議在處理客戶問題時，可以考慮更主動的溝通方式。",
        "您的解決方案思路清晰，值得其他同事參考學習。",
        "請繼續保持這樣的工作品質和報告水準。"
    ]
    
    return suggestions

@router.post("/enhance_one/{daily_no}/{sopno}")
async def enhance_record(
    daily_no: str,
    sopno: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """AI 增強單個記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        
        # 查詢記錄內容 - 使用 daily_no + sopno 來精確識別單一記錄
        record_sql = text("""
            SELECT DAILY_NO, CONTENT, PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C,
                   WORK_ITEM_SEQ, SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC,
                   EXECUTION_TIME_MINUTES, AI_CONTENT
            FROM jps.tdr_draft
            WHERE DAILY_NO = :daily_no AND SOPNO = :sopno AND EMPNO = :empno
        """)
        
        record_result = db.execute(record_sql, {
            "daily_no": daily_no,
            "sopno": sopno,
            "empno": empno
        }).fetchone()
        
        if not record_result:
            raise HTTPException(status_code=404, detail="找不到指定的記錄")
        
        # 生成 AI 增強內容
        original_content = record_result[1] or ""
        
        if not original_content.strip():
             raise HTTPException(status_code=400, detail="記錄內容為空，無法增強")

        enhanced_content = await _generate_enhanced_content(
            original_content=original_content,
            work_description=record_result[5] or "未指定專案",  # sop_desc_c
        )
        
        # 更新記錄的 AI 內容
        update_sql = text("""
            UPDATE jps.tdr_draft 
            SET AI_CONTENT = :ai_content,
                UPDATED_DATE = TO_CHAR(sysdate, 'YYYYMMDD'),
                UPDATED_TIME = TO_CHAR(sysdate, 'HH24:MI:SS')
            WHERE DAILY_NO = :daily_no AND SOPNO = :sopno AND EMPNO = :empno
        """)
        
        db.execute(update_sql, {
            "daily_no": daily_no,
            "sopno": sopno,
            "empno": empno,
            "ai_content": enhanced_content
        })
        
        db.commit()
        
        planno = record_result[2]
        sop_desc_c = record_result[5]
        
        return {
            "success": True,
            "message": f"執行工作 {sop_desc_c} AI 增強完成",
            "ai_content": enhanced_content,
            "data": {
                "sopno": sopno,
                "planno": planno,
                "daily_no": daily_no,
                "original_content": original_content,
                "ai_content": enhanced_content
            }
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enhancing record {record_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 增強記錄失敗: {e}")

@router.post("/enhance_all")
async def enhance_all_records(
    body: Dict[str, Any] | List[Any] | None = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """批量 AI 增強記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        
        today = ""
        if isinstance(body, dict) and "date" in body:
            today = body.get("date", "")

        if not today:
            from datetime import datetime
            today = datetime.now().strftime('%Y%m%d')
        else:
            today = today.replace("-", "")
        
        # 查詢今天的所有草稿記錄
        records_sql = text("""
            SELECT DAILY_NO, CONTENT, PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C,
                   WORK_ITEM_SEQ, SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC,
                   EXECUTION_TIME_MINUTES, AI_CONTENT
            FROM jps.tdr_draft
            WHERE EMPNO = :empno AND DOC_DATE = :doc_date
            ORDER BY CREATED_DATE ASC
        """)
        
        records_result = db.execute(records_sql, {
            "empno": empno,
            "doc_date": today
        }).fetchall()
        
        if not records_result:
            return {
                "success": True,
                "message": "沒有需要增強的記錄",
                "data": {"enhanced_count": 0, "date": today}
            }

        enhanced_count = 0
        
        for record_row in records_result:
            record_id = record_row[0]
            original_content = record_row[1] or ""
            
            if original_content.strip():
                enhanced_content = await _generate_enhanced_content(
                    original_content=original_content,
                    work_description=record_row[5] or "未指定專案",
                )
                
                update_sql = text("""
                    UPDATE jps.tdr_draft 
                    SET AI_CONTENT = :ai_content,
                        UPDATED_DATE = TO_CHAR(sysdate, 'YYYYMMDD'),
                        UPDATED_TIME = TO_CHAR(sysdate, 'HH24:MI:SS')
                    WHERE DAILY_NO = :record_id
                """)
                
                db.execute(update_sql, {
                    "record_id": record_id,
                    "ai_content": enhanced_content
                })
                
                enhanced_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"成功增強 {enhanced_count} 條記錄",
            "data": {
                "enhanced_count": enhanced_count,
                "date": today
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch enhancing records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量 AI 增強失敗: {e}")

async def _generate_enhanced_content(original_content: str, work_description: str):
    """使用 Azure AI Service 生成增強內容"""
    try:
        # 調用真正的 AI 服務
        enhanced_content = await get_ai_enhanced_report(
            original_content=original_content,
            project_name=work_description
        )
        return enhanced_content
    except Exception as e:
        logger.error(f"Azure AI service call failed: {e}")
        # 在 AI 服務失敗時返回一個有意義的錯誤或備用內容
        return f"AI 服務無法處理您的請求。錯誤：{e}"

@router.get("/status")
async def get_ai_service_status():
    """取得 AI 服務狀態"""
    return {
        "success": True,
        "data": {
            "status": "active",
            "features": {
                "suggestions": True,
                "enhancement": True,
                "batch_enhancement": True
            },
            "version": "1.0.0"
        }
    }
