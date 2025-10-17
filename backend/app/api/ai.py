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
from ..services.phison_ai_service import get_phison_enhanced_report

router = APIRouter(tags=["AI Services"])
logger = logging.getLogger(__name__)

# ✅ REMOVED: /api/ai/suggestions/{report_id} - Replaced by /api/supervisor/reports/{report_id}/ai-suggestions

@router.post("/enhance_one/{daily_no}/{planno}/{sopno}")
async def enhance_record(
    daily_no: str,
    planno: str,
    sopno: str,
    ai_service: str = "aoai",  # 新增參數: aoai 或 phison
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """AI 增強單個記錄 (支援多種 AI 服務)"""
    try:
        # 處理空的 planno - 前端傳入 "NULL" 表示空值
        if planno == "NULL":
            planno = ""

        logger.info(f"AI增強請求: daily_no={daily_no}, planno='{planno}', sopno={sopno}, ai_service={ai_service}")

        if not current_user.employee:
            raise HTTPException(status_code=400, detail="User has no employee information")

        empno = current_user.employee.empno

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
            raise HTTPException(status_code=404, detail="Record not found")

        # 處理FILES欄位中的檔案
        files_json = record_result[12] or "[]"  # FILES欄位是第13個（索引12）

        files = []
        try:
            files = json.loads(files_json) if files_json != "[]" else []
        except Exception as e:
            logger.error(f"JSON解析失敗: {e}")
            files = []

        # 檢查FILES中標記為AI參考的檔案
        ai_files = []
        for f in files:
            if f.get('is_selected_for_ai', False):
                ai_files.append(f)

        # 生成 AI 增強內容
        original_content = record_result[1] or ""

        # 檢查是否有AI參考檔案可以處理
        has_ai_files = len(ai_files) > 0

        # 如果既沒有文字內容也沒有AI參考檔案，才拒絕處理
        if not original_content.strip() and not has_ai_files:
            raise HTTPException(status_code=400, detail="Record content is empty and no AI reference data available")

        # 將AI參考檔案轉換為附件格式
        attachments = []
        if has_ai_files:
            for ai_file in ai_files:
                # ✅ 更新: CommonAPI 檔案直接使用 URL
                # CommonAPI 格式: /CommonApi/api/SharedFile?FileId=xxx&Type=upimages&CoCode=A&FileName=xxx
                url_path = ai_file.get('url', '')

                # 創建附件記錄
                attachments.append({
                    "att_id": f"files_{ai_file.get('name', 'unknown')}",
                    "file_name": ai_file.get('name', 'unknown'),
                    "file_path": url_path,  # 直接使用 URL (AI service 會處理)
                    "file_size": ai_file.get('size', 0),
                    "file_type": ai_file.get('type', ''),
                    "is_selected_for_ai": True  # 已經篩選過了
                })

        enhanced_content = await _generate_enhanced_content(
            original_content=original_content,
            work_description=record_result[5] or "未指定專案",  # sop_desc_c
            attachments=attachments,
            ai_service=ai_service  # 傳遞 AI 服務類型
        )
        
        # 更新記錄的 AI 內容和使用的 AI 服務
        update_sql = text("""
            UPDATE jps.tdr_draft
            SET AI_CONTENT = :ai_content,
                AI_SERVICE = :ai_service,
                UPDATED_DATE = TO_CHAR(sysdate, 'YYYYMMDD'),
                UPDATED_TIME = TO_CHAR(sysdate, 'HH24:MI:SS')
            WHERE DAILY_NO = :daily_no AND COALESCE(PLANNO, '') = COALESCE(:planno, '') AND SOPNO = :sopno AND EMPNO = :empno
        """)
        
        db.execute(update_sql, {
            "daily_no": daily_no,
            "planno": planno,
            "sopno": sopno,
            "empno": empno,
            "ai_content": enhanced_content,
            "ai_service": ai_service
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

# ✅ REMOVED: /api/ai/enhance_all - Not used by frontend

async def _generate_enhanced_content(
    original_content: str,
    work_description: str,
    attachments: Optional[List[Dict]] = None,
    ai_service: str = "aoai"
):
    """使用指定的 AI Service 生成增強內容，支援附件處理"""
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
        
        # 根據 ai_service 選擇對應的 AI 服務
        logger.info(f"使用 AI 服務: {ai_service}")
        logger.info(f"增強內容: {content_to_enhance[:100]}...")
        logger.info(f"參考資料數量: {len(reference_texts)}")

        if ai_service == "phison":
            logger.info("調用 Phison LLM 服務進行內容增強...")
            enhanced_content = await get_phison_enhanced_report(
                original_content=content_to_enhance,
                project_name=work_description,
                reference_texts=reference_texts
            )
        else:  # aoai (預設)
            logger.info("調用 Azure OpenAI 服務進行內容增強...")
            enhanced_content = await get_ai_enhanced_report(
                original_content=content_to_enhance,
                project_name=work_description,
                reference_texts=reference_texts
            )

        logger.info(f"AI 內容增強完成 (使用 {ai_service})，結果長度: {len(enhanced_content)}")
        return enhanced_content
    except Exception as e:
        logger.error(f"AI service call failed ({ai_service}): {e}")
        import traceback
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        # 在 AI 服務失敗時,直接拋出例外 (根據用戶需求)
        raise

# ✅ REMOVED: /api/ai/status - Not used by frontend, use /api/monitoring/health instead
