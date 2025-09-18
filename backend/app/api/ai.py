# backend/app/api/ai.py

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..core.config import settings
from ..schemas.user import User
from ..services.azure_ai_service import get_ai_enhanced_report, process_attachments_for_ai

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
            raise HTTPException(status_code=400, detail="User has no employee information")
        
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
            raise HTTPException(status_code=404, detail="Daily report not found")
        
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
        raise HTTPException(status_code=500, detail="AI suggestion generation failed")

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

@router.post("/enhance_one/{daily_no}/{planno}/{sopno}")
async def enhance_record(
    daily_no: str,
    planno: str,
    sopno: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """AI 增強單個記錄"""
    try:
        # 處理空的 planno - 前端傳入 "NULL" 表示空值
        if planno == "NULL":
            planno = ""

        print("!!! FUNCTION CALLED !!!")  # 強制輸出
        logger.error(f"! [FORCE] 函數被調用: daily_no={daily_no}, planno='{planno}', sopno={sopno}")

        if not current_user.employee:
            raise HTTPException(status_code=400, detail="User has no employee information")

        empno = current_user.employee.empno
        logger.info(f"[DEBUG] 請求參數: daily_no={daily_no}, planno='{planno}', sopno={sopno}, empno={empno}")
        
        # 查詢記錄內容 - 使用 daily_no + planno + sopno 來精確識別單一記錄，同時取得FILES欄位
        record_sql = text("""
            SELECT DAILY_NO, CONTENT, PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C,
                   WORK_ITEM_SEQ, SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC,
                   EXECUTION_TIME_MINUTES, AI_CONTENT, FILES
            FROM jps.tdr_draft
            WHERE DAILY_NO = :daily_no AND COALESCE(PLANNO, '') = COALESCE(:planno, '') AND SOPNO = :sopno AND EMPNO = :empno
        """)
        
        record_result = db.execute(record_sql, {
            "daily_no": daily_no,
            "planno": planno,
            "sopno": sopno,
            "empno": empno
        }).fetchone()
        
        if not record_result:
            logger.error(f"[DEBUG] 找不到記錄: daily_no={daily_no}, sopno={sopno}, empno={empno}")
            raise HTTPException(status_code=404, detail="Record not found")
        
        logger.info(f"[DEBUG] 找到記錄: daily_no={daily_no}, sopno={sopno}")
        logger.info(f"[DEBUG] 記錄內容長度: {len(record_result[1] or '')}")
        
        # 處理FILES欄位中的檔案
        files_json = record_result[12] or "[]"  # FILES欄位是第13個（索引12）
        logger.info(f"[DEBUG] 原始FILES欄位內容: {repr(files_json)}")
        
        files = []
        try:
            files = json.loads(files_json) if files_json != "[]" else []
            logger.info(f"[DEBUG] JSON解析成功")
        except Exception as e:
            logger.error(f"[DEBUG] JSON解析失敗: {e}")
            files = []
        
        logger.info(f"[DEBUG] FILES欄位檔案數量: {len(files)}")
        logger.info(f"[DEBUG] FILES內容: {files}")
        
        # 檢查FILES中標記為AI參考的檔案
        ai_files = []
        for i, f in enumerate(files):
            is_ai_selected = f.get('is_selected_for_ai', False)
            logger.info(f"[DEBUG] 檔案{i}: name={f.get('name')}, is_selected_for_ai={is_ai_selected} (type: {type(is_ai_selected)})")
            if is_ai_selected:
                ai_files.append(f)
                logger.info(f"[DEBUG] 檔案{i}被加入AI參考列表")
        
        logger.info(f"[DEBUG] AI參考檔案數量: {len(ai_files)}")
        logger.info(f"[DEBUG] AI參考檔案列表: {ai_files}")
        
        # 生成 AI 增強內容
        original_content = record_result[1] or ""
        
        # 檢查是否有AI參考檔案可以處理
        has_ai_files = len(ai_files) > 0
        
        logger.info(f"[DEBUG] 內容檢查 - 原始內容: '{original_content}' (長度: {len(original_content)})")
        logger.info(f"[DEBUG] 內容檢查 - 原始內容strip(): '{original_content.strip()}' (長度: {len(original_content.strip())})")
        logger.info(f"[DEBUG] 內容檢查 - AI參考檔案: {has_ai_files}")
        logger.info(f"[DEBUG] 內容檢查 - AI檔案列表: {ai_files}")
        
        # 如果既沒有文字內容也沒有AI參考檔案，才拒絕處理
        if not original_content.strip() and not has_ai_files:
            logger.error(f"[DEBUG] 拒絕處理: 無文字內容且無AI參考檔案")
            raise HTTPException(status_code=400, detail="Record content is empty and no AI reference data available")
        
        logger.info(f"[DEBUG] 通過檢查，準備AI增強")

        # 將AI參考檔案轉換為附件格式
        attachments = []
        if has_ai_files:
            for ai_file in ai_files:
                # 轉換URL為檔案路徑
                url_path = ai_file.get('url', '')
                if url_path.startswith('/uploads/'):
                    # 轉換為實際檔案路徑  
                    file_path = settings.UPLOAD_DIR + url_path.replace('/uploads/', '/')
                else:
                    file_path = url_path
                
                # 創建附件記錄
                attachments.append({
                    "att_id": f"files_{ai_file.get('name', 'unknown')}",
                    "file_name": ai_file.get('name', 'unknown'),
                    "file_path": file_path,
                    "file_size": ai_file.get('size', 0),
                    "file_type": ai_file.get('type', ''),
                    "is_selected_for_ai": True  # 已經篩選過了
                })
                logger.info(f"[DEBUG] 轉換檔案: {ai_file.get('name')} -> {file_path}")

        enhanced_content = await _generate_enhanced_content(
            original_content=original_content,
            work_description=record_result[5] or "未指定專案",  # sop_desc_c
            attachments=attachments
        )
        
        # 更新記錄的 AI 內容
        update_sql = text("""
            UPDATE jps.tdr_draft 
            SET AI_CONTENT = :ai_content,
                UPDATED_DATE = TO_CHAR(sysdate, 'YYYYMMDD'),
                UPDATED_TIME = TO_CHAR(sysdate, 'HH24:MI:SS')
            WHERE DAILY_NO = :daily_no AND COALESCE(PLANNO, '') = COALESCE(:planno, '') AND SOPNO = :sopno AND EMPNO = :empno
        """)
        
        db.execute(update_sql, {
            "daily_no": daily_no,
            "planno": planno,
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
        logger.error(f"Error enhancing record {daily_no}: {str(e)}")
        raise HTTPException(status_code=500, detail="AI enhancement failed")

@router.post("/enhance_all")
async def enhance_all_records(
    body: Dict[str, Any] | List[Any] | None = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """批量 AI 增強記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="User has no employee information")
        
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
            
            # 取得該記錄的附件
            attachments_sql = text("""
                SELECT att_id, file_name, file_path, file_size, file_type, is_selected_for_ai
                FROM jps.tdr_draft_attachment
                WHERE draft_record_id = :daily_no
            """)
            
            attachments_result = db.execute(attachments_sql, {"daily_no": record_id})
            attachments = []
            for att_row in attachments_result.fetchall():
                attachments.append({
                    "att_id": att_row[0],
                    "file_name": att_row[1],
                    "file_path": att_row[2],
                    "file_size": att_row[3],
                    "file_type": att_row[4],
                    "is_selected_for_ai": att_row[5]
                })
            
            # 檢查是否有內容可以處理（文字內容或AI附件）
            has_ai_attachments = any(att.get('is_selected_for_ai', False) for att in attachments)
            
            if original_content.strip() or has_ai_attachments:
                logger.info(f"處理記錄 {record_id}: 文字={len(original_content)}字符, AI附件={len([att for att in attachments if att.get('is_selected_for_ai')])}")
                
                enhanced_content = await _generate_enhanced_content(
                    original_content=original_content,
                    work_description=record_row[5] or "未指定專案",
                    attachments=attachments
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
            else:
                logger.info(f"跳過記錄 {record_id}: 無文字內容且無AI附件")
        
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
        raise HTTPException(status_code=500, detail="Batch AI enhancement failed")

async def _generate_enhanced_content(original_content: str, work_description: str, attachments: Optional[List[Dict]] = None):
    """使用 Azure AI Service 生成增強內容，支援附件處理"""
    try:
        logger.info(f"開始生成增強內容，工作描述: {work_description}")
        logger.info(f"原始內容長度: {len(original_content)}")
        
        # 處理附件內容
        reference_texts = []
        if attachments:
            logger.info(f"處理 {len(attachments)} 個附件，查找AI參考檔案")
            reference_texts = await process_attachments_for_ai(attachments)
            logger.info(f"成功提取 {len(reference_texts)} 個檔案的內容作為AI參考")
        else:
            logger.info(f"沒有附件需要處理")
        
        # 如果沒有原始內容但有附件內容，則使用附件內容作為主要內容
        content_to_enhance = original_content
        if not original_content.strip() and reference_texts:
            logger.info(f"沒有文字內容，使用附件內容進行AI增強")
            content_to_enhance = "請基於提供的參考資料生成工作報告。"
        
        # 調用真正的 AI 服務，包含附件內容
        logger.info(f"調用 Azure OpenAI 服務進行內容增強...")
        logger.info(f"增強內容: {content_to_enhance[:100]}...")
        logger.info(f"參考資料數量: {len(reference_texts)}")
        
        enhanced_content = await get_ai_enhanced_report(
            original_content=content_to_enhance,
            project_name=work_description,
            reference_texts=reference_texts
        )
        
        logger.info(f"AI 內容增強完成，結果長度: {len(enhanced_content)}")
        return enhanced_content
    except Exception as e:
        logger.error(f"Azure AI service call failed: {e}")
        import traceback
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        # 在 AI 服務失敗時返回一個有意義的錯誤或備用內容
        return "AI service temporarily unavailable"

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
