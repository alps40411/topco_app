# backend/app/api/weekly.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json
import os
from pathlib import Path

from app.core.legacy_database import get_legacy_db
from app.core.deps import get_current_user
from app.schemas.user import User as UserSchema
from app.schemas.weekly_report_detail import ShowWeeklyReportResponse
from app.schemas.reply_weekly import ReplyWeeklyReportRequest, ReplyWeeklyReportResponse

router = APIRouter(prefix="/weekly", tags=["Weekly Reports"])
logger = logging.getLogger(__name__)


@router.get("/can-submit")
async def check_can_submit(
    weekly_no: Optional[str] = None,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    檢查是否可以提交/編輯週報

    業務規則：
    1. 時間窗口檢查：週五 17:00 ~ 週一 08:30
    2. 審閱狀態檢查：是否已被主管回覆/評分

    Returns:
        - can_submit: 是否可提交
        - can_edit: 是否可編輯
        - reason: 原因說明
        - next_submit_time: 下次可提交的時間
        - has_replies: 是否已被主管審閱
    """
    from datetime import datetime, timedelta
    import pytz

    try:
        # 使用台灣時區
        taiwan_tz = pytz.timezone('Asia/Taipei')
        now = datetime.now(taiwan_tz)

        # 1. 時間窗口檢查
        day_of_week = now.weekday()  # 0=週一, 1=週二, ..., 4=週五, 5=週六, 6=週日
        hour = now.hour
        minute = now.minute

        in_time_window = False

        if day_of_week == 4:  # 週五
            if hour >= 17:
                in_time_window = True
        elif day_of_week == 5 or day_of_week == 6:  # 週六、週日
            in_time_window = True
        elif day_of_week == 0:  # 週一
            if hour < 8 or (hour == 8 and minute < 30):
                in_time_window = True

        # 計算下次可提交的時間
        next_submit_time = ""
        if not in_time_window:
            # 計算下個週五 17:00
            days_until_friday = (4 - day_of_week) % 7
            if days_until_friday == 0 and (hour >= 17 or (hour == 8 and minute >= 30)):
                days_until_friday = 7

            next_friday = now + timedelta(days=days_until_friday)
            next_submit_datetime = next_friday.replace(hour=17, minute=0, second=0, microsecond=0)
            next_submit_time = next_submit_datetime.strftime("%Y-%m-%d %H:%M:%S")

        # 2. 審閱狀態檢查（如果有提供 weekly_no）
        has_replies = False
        if weekly_no:
            # 檢查是否有主管回覆記錄
            reply_check_sql = text("""
                SELECT COUNT(*) FROM jps.tdr_weekly_reply
                WHERE weekly_no = :weekly_no and from_where is not NULL
            """)

            reply_result = db.execute(reply_check_sql, {"weekly_no": weekly_no}).fetchone()
            has_replies = reply_result[0] > 0 if reply_result else False

        # 3. 決定最終結果
        # 週報系統權限規則：
        # - can_edit: 只要未被回覆就可編輯（無時間限制）
        # - can_delete: 只要未被回覆就可刪除（無時間限制）
        # - can_submit: 需在時間範圍內且未被回覆
        can_edit = not has_replies
        can_delete = not has_replies
        can_submit = in_time_window and not has_replies

        # 4. 生成原因說明
        if has_replies:
            reason = "此週報已被主管審閱，無法再修改或刪除"
        elif not in_time_window:
            reason = f"不在提交時間範圍內（週五 17:00 ~ 週一 08:30），但仍可編輯。下次可提交時間：{next_submit_time}"
        else:
            reason = "可以編輯、刪除和提交週報"

        return {
            "can_submit": can_submit,
            "can_edit": can_edit,
            "can_delete": can_delete,
            "reason": reason,
            "next_submit_time": next_submit_time,
            "has_replies": has_replies,
            "in_submit_window": in_time_window  # 是否在提交時間窗口內（週五 17:00 ~ 週一 08:30）
        }

    except Exception as e:
        logger.error(f"檢查提交狀態失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # 預設允許提交（防止 API 錯誤影響使用）
        return {
            "can_submit": True,
            "can_edit": True,
            "can_delete": True,
            "reason": "檢查失敗，預設允許提交",
            "next_submit_time": "",
            "has_replies": False,
            "in_submit_window": True  # 預設為在提交窗口內，避免影響列表頁顯示
        }


async def _generate_enhanced_weekly_content(
    original_content: str,
    subject: str,
    job_item: str,
    attachments: Optional[List[Dict]] = None,
    ai_service: str = "aoai"
) -> str:
    """
    使用指定的 AI Service 生成週報增強內容，支援附件處理
    
    Args:
        original_content: 原始週報內容（可能包含 HTML）
        subject: 週報主題
        job_item: 工作項目
        attachments: 附件列表（已標記 is_selected_for_ai 的）
        ai_service: AI 服務類型（aoai 或 phison）
    
    Returns:
        AI 潤飾後的內容
    """
    from app.services.azure_ai_service import process_attachments_for_ai, get_ai_enhanced_weekly_report
    from app.services.phison_ai_service import get_phison_weekly_report
    
    try:
        logger.info(f"開始生成週報增強內容，工作項目: {job_item}, AI服務: {ai_service}")
        logger.info(f"原始內容長度: {len(original_content)}")
        
        # 處理附件內容
        reference_texts = []
        if attachments:
            logger.info(f"處理 {len(attachments)} 個附件，查找 AI 參考檔案")
            reference_texts = await process_attachments_for_ai(attachments)
            logger.info(f"成功提取 {len(reference_texts)} 個檔案的內容作為AI參考")
        else:
            logger.info(f"沒有附件需要處理")
        
        # 檢查是否有內容可以潤飾
        if not original_content.strip() and not reference_texts:
            raise HTTPException(status_code=400, detail="內容不能為空且沒有參考資料")
        
        # 如果沒有文字內容但有附件內容，則使用附件內容作為主要內容
        content_to_enhance = original_content
        if not original_content.strip() and reference_texts:
            logger.info(f"沒有文字內容，使用附件內容進行AI增強")
            content_to_enhance = "請基於提供的參考資料生成週報內容。"
        
        # 根據 ai_service 選擇對應的 AI 服務
        logger.info(f"使用 AI 服務: {ai_service}")
        logger.info(f"增強內容: {content_to_enhance[:100]}...")
        logger.info(f"參考資料數量: {len(reference_texts)}")
        
        if ai_service == "phison":
            # Phison 需要純文字，清理 HTML
            def clean_html_for_phison(html_content: str) -> str:
                import re
                from html import unescape
                text = re.sub(r'<[^>]+>', ' ', html_content)
                text = unescape(text)
                text = re.sub(r'\s+', ' ', text)
                text = text.replace('\u202f', ' ').replace('\xa0', ' ')
                return text.strip()
            
            logger.info("調用 Phison AI 服務進行週報內容增強...")
            clean_content = clean_html_for_phison(content_to_enhance)
            clean_subject = clean_html_for_phison(subject)
            cleaned_reference_texts = [clean_html_for_phison(ref) for ref in reference_texts] if reference_texts else []
            
            enhanced_content = await get_phison_weekly_report(
                original_content=clean_content,
                job_item=job_item,
                subject=clean_subject,
                reference_texts=cleaned_reference_texts
            )
        else:  # aoai (預設)
            logger.info("調用 Azure OpenAI 服務進行週報內容增強...")
            enhanced_content = await get_ai_enhanced_weekly_report(
                original_content=content_to_enhance,
                job_item=job_item,
                subject=subject,
                reference_texts=reference_texts
            )
        
        logger.info(f"AI 週報內容增強完成 (使用 {ai_service})，結果長度: {len(enhanced_content)}")
        return enhanced_content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI service call failed ({ai_service}): {e}")
        import traceback
        logger.error(f"錯誤詳情: {traceback.format_exc()}")
        raise





# 固定的工作項目
JOB_ITEMS = ["營收報告", "工作重點", "應收帳款追蹤", "原廠說明", "市場動態", "競爭者資訊", "專案", "部門人事", "其他"]

# 檔案儲存路徑
STORAGE_PATH = Path("storage/weekly")
STORAGE_PATH.mkdir(parents=True, exist_ok=True)


def get_current_week_info():
    """獲取當前年份和週次（ISO 8601 標準）"""
    now = datetime.now()
    iso_calendar = now.isocalendar()
    year = iso_calendar[0]  # ISO 年份（該周禮拜四所在的年份）
    week = iso_calendar[1]  # ISO 週次
    return year, week


def generate_weekly_no(db: Session) -> str:
    """
    生成新的 weekly_no - 直接從 sequence 取得
    """
    try:
        seq_sql = text("SELECT jps.seq_tdr_weekly_master.nextval FROM dual")
        seq_result = db.execute(seq_sql).fetchone()
        seq_num = seq_result[0]

        weekly_no = str(seq_num)
        logger.info(f"Generated new weekly_no: {weekly_no}")
        return weekly_no
    except Exception as e:
        logger.error(f"Error generating weekly_no: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法生成週報編號: {str(e)}")


def get_next_seq(db: Session, weekly_no: str) -> int:
    """獲取指定 weekly_no 的下一個 seq"""
    sql = text("""
        SELECT COALESCE(MAX(seq), 0) + 1 as next_seq
        FROM jps.tdr_weekly_draft
        WHERE weekly_no = :weekly_no
    """)
    result = db.execute(sql, {"weekly_no": weekly_no}).fetchone()
    return result[0] if result else 1


@router.get("/job-items")
async def get_job_items():
    """獲取工作項目列表"""
    return {"job_items": JOB_ITEMS}


@router.get("/weekly-no")
async def get_weekly_no(
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """獲取或生成週報編號"""
    empno = current_user.employee.empno
    cocode = current_user.employee.cocode or "A"
    year, week = get_current_week_info()

    # 檢查該週是否已有 weekly_no（只接受純數字格式）
    sql = text("""
        SELECT weekly_no
        FROM jps.tdr_weekly_draft
        WHERE empno = :empno
          AND cocode = :cocode
          AND TO_CHAR(TO_DATE(doc_date, 'YYYYMMDD'), 'IYYY') = :year
          AND TO_CHAR(TO_DATE(doc_date, 'YYYYMMDD'), 'IW') = :week
          AND (status IS NULL OR status != 'D')
          AND weekly_no NOT LIKE 'W%'
        ORDER BY weekly_no DESC
        LIMIT 1
    """)

    result = db.execute(sql, {
        "empno": empno,
        "cocode": cocode,
        "year": str(year),
        "week": str(week).zfill(2)
    }).fetchone()

    if result:
        weekly_no = result[0]
    else:
        weekly_no = generate_weekly_no(db)

    return {
        "weekly_no": weekly_no,
        "year": year,
        "week": week
    }


@router.get("/drafts")
async def get_weekly_drafts(
    year: Optional[int] = None,
    week: Optional[int] = None,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """獲取週報草稿列表"""
    if not year or not week:
        year, week = get_current_week_info()

    empno = current_user.employee.empno
    cocode = current_user.employee.cocode or "A"

    # 查詢草稿（排除已刪除的）
    sql = text("""
        SELECT
            weekly_no, empno, cocode, doc_date, seq,
            subject, job_item, content, word_count,
            att_file1, att_file2, files, draft_type, status,
            created_date, created_time, updated_date, updated_time,
            ai_content, ai_service
        FROM jps.tdr_weekly_draft
        WHERE empno = :empno
          AND cocode = :cocode
          AND TO_CHAR(TO_DATE(doc_date, 'YYYYMMDD'), 'IYYY') = :year
          AND TO_CHAR(TO_DATE(doc_date, 'YYYYMMDD'), 'IW') = :week
          AND (status IS NULL OR status != 'D')
        ORDER BY weekly_no, seq
    """)

    results = db.execute(sql, {
        "empno": empno,
        "cocode": cocode,
        "year": str(year),
        "week": str(week).zfill(2)
    }).fetchall()

    drafts = []
    weekly_no_from_drafts = None

    empno = current_user.employee.empno
    cocode = current_user.employee.cocode or "A"

    for row in results:
        # 解析 files JSON
        files_data = []
        if row[11]:  # files column
            try:
                files_data = json.loads(row[11])
                # 確保每個檔案都有正確的下載 URL
                for file in files_data:
                    if file.get("file_path") and not file.get("url"):
                        from app.services.commonapi_file_service import CommonApiFileService
                        file_id = file.get("file_path") or file.get("id")
                        filename = file.get("filename") or file.get("name") or "file"
                        file["url"] = CommonApiFileService.generate_download_url(file_id, filename, cocode)
                    # 確保 name 欄位存在（用於前端顯示）
                    if not file.get("name") and file.get("filename"):
                        file["name"] = file.get("filename")
            except:
                files_data = []

        # 記錄第一個有效的（純數字）weekly_no
        if not weekly_no_from_drafts and row[0]:
            logger.info(f"Found weekly_no in draft: {row[0]}, starts with 'W': {str(row[0]).startswith('W')}")
            if not str(row[0]).startswith('W'):
                weekly_no_from_drafts = row[0]
                logger.info(f"Using valid weekly_no from drafts: {weekly_no_from_drafts}")

        draft = {
            "weekly_no": row[0],
            "empno": row[1],
            "cocode": row[2],
            "doc_date": row[3],
            "seq": row[4],
            "subject": row[5],
            "job_item": row[6],
            "content": row[7],
            "word_count": row[8] or 0,
            "att_file1": row[9],
            "att_file2": row[10],
            "files": files_data,
            "draft_type": row[12],
            "status": row[13],
            "created_date": row[14],
            "created_time": row[15],
            "updated_date": row[16],
            "updated_time": row[17],
            "ai_content": row[18],
            "ai_service": row[19]
        }
        drafts.append(draft)

    # 如果找到有效的 weekly_no 就用它，否則生成新的
    if not weekly_no_from_drafts:
        logger.info(f"No valid weekly_no found in drafts, generating new one")
        weekly_no_from_drafts = generate_weekly_no(db)

    logger.info(f"Returning weekly_no: {weekly_no_from_drafts}")
    return {
        "weekly_no": weekly_no_from_drafts,
        "year": year,
        "week": week,
        "drafts": drafts
    }


@router.post("/drafts")
async def save_weekly_draft(
    draft_data: Dict[str, Any],
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """新增或更新週報草稿"""
    try:
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or "A"

        weekly_no = draft_data.get("weekly_no")
        seq = draft_data.get("seq")
        subject = draft_data.get("subject", "")
        job_item = draft_data.get("job_item")
        content = draft_data.get("content", "")
        files = draft_data.get("files", [])

        # 驗證必填欄位
        if not weekly_no:
            raise HTTPException(status_code=400, detail="缺少 weekly_no")
        if not job_item or job_item not in JOB_ITEMS:
            raise HTTPException(status_code=400, detail="無效的工作項目")

        # 計算字數
        word_count = len(content)

        # 準備檔案資料
        files_json = json.dumps(files, ensure_ascii=False) if files else None
        # att_file1: 第一個檔案的原始檔名
        # att_file2: 第一個檔案的路徑（CommonAPI FileId）
        att_file1 = files[0].get("filename") or files[0].get("name") if len(files) > 0 else None
        att_file2 = files[0].get("file_path") or files[0].get("id") if len(files) > 0 else None

        now = datetime.now()
        current_date = now.strftime("%Y%m%d")
        current_time = now.strftime("%H:%M:%S")

        if seq and weekly_no:
            # 更新現有草稿
            update_sql = text("""
                UPDATE jps.tdr_weekly_draft
                SET
                    subject = :subject,
                    job_item = :job_item,
                    content = :content,
                    word_count = :word_count,
                    att_file1 = :att_file1,
                    att_file2 = :att_file2,
                    files = :files,
                    updated_date = :updated_date,
                    updated_time = :updated_time
                WHERE weekly_no = :weekly_no AND seq = :seq
            """)

            db.execute(update_sql, {
                "weekly_no": weekly_no,
                "seq": seq,
                "subject": subject,
                "job_item": job_item,
                "content": content,
                "word_count": word_count,
                "att_file1": att_file1,
                "att_file2": att_file2,
                "files": files_json,
                "updated_date": current_date,
                "updated_time": current_time
            })
            db.commit()

            return {
                "weekly_no": weekly_no,
                "seq": seq,
                "message": "草稿更新成功"
            }
        else:
            # 新增草稿 - 生成新的 weekly_no
            if not weekly_no:
                weekly_no = generate_weekly_no(db)

            seq = get_next_seq(db, weekly_no)

            insert_sql = text("""
                INSERT INTO jps.tdr_weekly_draft (
                    weekly_no, empno, cocode, doc_date, seq,
                    subject, job_item, content, word_count,
                    att_file1, att_file2, files, draft_type, status,
                    created_date, created_time, updated_date, updated_time
                ) VALUES (
                    :weekly_no, :empno, :cocode, :doc_date, :seq,
                    :subject, :job_item, :content, :word_count,
                    :att_file1, :att_file2, :files, :draft_type, :status,
                    :created_date, :created_time, :updated_date, :updated_time
                )
            """)

            db.execute(insert_sql, {
                "weekly_no": weekly_no,
                "empno": empno,
                "cocode": cocode,
                "doc_date": current_date,
                "seq": seq,
                "subject": subject,
                "job_item": job_item,
                "content": content,
                "word_count": word_count,
                "att_file1": att_file1,
                "att_file2": att_file2,
                "files": files_json,
                "draft_type": "TEMP",
                "status": "A",
                "created_date": current_date,
                "created_time": current_time,
                "updated_date": current_date,
                "updated_time": current_time
            })
            db.commit()

            return {
                "weekly_no": weekly_no,
                "seq": seq,
                "message": "草稿保存成功"
            }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving weekly draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存草稿失敗: {str(e)}")


@router.delete("/drafts/{weekly_no}/{seq}")
async def delete_weekly_draft(
    weekly_no: str,
    seq: int,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """刪除週報草稿"""
    try:
        # 軟刪除
        sql = text("""
            UPDATE jps.tdr_weekly_draft
            SET status = 'D',
            updated_date = :updated_date,
            updated_time = :updated_time
            WHERE weekly_no = :weekly_no
              AND seq = :seq
              AND (status IS NULL OR status != 'D')
        """)

        now = datetime.now()
        current_date = now.strftime("%Y%m%d")
        current_time = now.strftime("%H:%M:%S")

        result = db.execute(sql, {
            "weekly_no": weekly_no,
            "seq": seq,
            "updated_date": current_date,
            "updated_time": current_time
        })
        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="找不到要刪除的記錄")

        return {"message": "草稿刪除成功"}

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting weekly draft: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除草稿失敗: {str(e)}")


@router.post("/drafts/upload")
async def upload_weekly_file(
    file: UploadFile = File(...),
    weekly_no: str = Form(...),
    seq: int = Form(...),
    current_user: UserSchema = Depends(get_current_user)
):
    """上傳週報附件 - 使用 CommonAPI"""
    from app.services.commonapi_file_service import CommonApiFileService

    try:
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or "A"

        logger.info(f"上傳檔案: {file.filename}, empno={empno}, cocode={cocode}, weekly_no={weekly_no}, seq={seq}")

        # 檢查檔案類型
        not_allowed_extensions = {'.exe', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.msi', '.dll', '.com'}
        file_ext = Path(file.filename or "").suffix.lower()
        if file_ext in not_allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的檔案類型: {file_ext}"
            )

        # 使用 CommonAPI 上傳
        result = await CommonApiFileService.upload_file(
            file=file,
            cocode=cocode,
            csrf_token=""  # 如需要可從 request header 取得
        )

        logger.info(f"檔案上傳成功: {result['id']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {str(e)}")


@router.delete("/drafts/files/{weekly_no}/{seq}/{filename}")
async def delete_weekly_file(
    weekly_no: str,
    seq: int,
    filename: str,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """刪除週報附件 - CommonAPI 檔案不實體刪除，只從記錄中移除"""
    try:
        # 查詢當前的 files JSON
        sql = text("""
            SELECT files
            FROM jps.tdr_weekly_draft
            WHERE weekly_no = :weekly_no AND seq = :seq
        """)

        result = db.execute(sql, {"weekly_no": weekly_no, "seq": seq}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="找不到草稿記錄")

        files_json = result[0]
        if not files_json:
            raise HTTPException(status_code=404, detail="沒有附件記錄")

        # 解析並移除指定檔案
        files = json.loads(files_json)
        updated_files = [f for f in files if f.get("filename") != filename and f.get("name") != filename]

        if len(updated_files) == len(files):
            raise HTTPException(status_code=404, detail="找不到要刪除的檔案")

        # 更新資料庫
        update_sql = text("""
            UPDATE jps.tdr_weekly_draft
            SET files = :files,
            updated_date = :updated_date,
            updated_time = :updated_time
            WHERE weekly_no = :weekly_no AND seq = :seq
        """)

        now = datetime.now()
        db.execute(update_sql, {
            "weekly_no": weekly_no,
            "seq": seq,
            "files": json.dumps(updated_files, ensure_ascii=False) if updated_files else None,
            "updated_date": now.strftime("%Y%m%d"),
            "updated_time": now.strftime("%H:%M:%S")
        })
        db.commit()

        logger.info(f"檔案已從記錄中移除: {filename}")
        return {"message": "檔案刪除成功"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案刪除失敗: {str(e)}")


@router.post("/report-list")
async def get_weekly_report_list(
    payload: Dict[str, Any],
    current_user: UserSchema = Depends(get_current_user)
):
    """
    獲取週報列表 - 轉發到 CommonAPI

    payload: {
        "empno": "",  # 可選，會自動使用當前用戶的 empno
        "year": "2025",
        "weeklyNo": "52"
    }
    """
    import httpx
    from app.core.config import settings

    try:
        # 使用當前用戶的 empno
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or "A"

        # 構建請求參數
        request_data = {
            "empno": empno,
            "year": payload.get("year", ""),
            "weeklyNo": payload.get("weeklyNo", "")
        }

        # 調用 CommonAPI（使用測試環境的 URL）
        commonapi_url = settings.WEEKLY_REPORT_LIST_API_URL
        logger.info(f"調用 CommonAPI 週報列表: {commonapi_url}, params={request_data}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                commonapi_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"CommonAPI 返回錯誤: {response.status_code}, {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"CommonAPI 調用失敗: {response.text}"
                )

            result = response.json()
            logger.info(f"CommonAPI 返回成功，資料筆數: {len(result.get('ResponseData', []))}")

            return result

    except httpx.TimeoutException:
        logger.error("CommonAPI 請求超時")
        raise HTTPException(status_code=504, detail="請求超時")
    except httpx.RequestError as e:
        logger.error(f"CommonAPI 請求錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"請求錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"獲取週報列表失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"獲取週報列表失敗: {str(e)}")


@router.post("/drafts/enhance-one/{weekly_no}/{seq}")
async def enhance_weekly_note(
    weekly_no: str,
    seq: int,
    ai_service: str = "aoai",
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """AI 潤飾單筆週報筆記並存入資料庫"""
    from starlette.concurrency import run_in_threadpool
    
    try:
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or "A"
        
        logger.info(f"🔥 AI潤飾週報: weekly_no={weekly_no}, seq={seq}, ai_service={ai_service}")
        
        # 查詢筆記內容
        query_sql = text("""
            SELECT weekly_no, seq, subject, job_item, content, files
            FROM jps.tdr_weekly_draft
            WHERE weekly_no = :weekly_no
              AND seq = :seq
              AND empno = :empno
              AND cocode = :cocode
              AND (status IS NULL OR status != 'D')
        """)
        
        result = await run_in_threadpool(
            lambda: db.execute(query_sql, {
                "weekly_no": weekly_no,
                "seq": seq,
                "empno": empno,
                "cocode": cocode
            }).fetchone()
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="找不到該筆記")
        
        subject = result[2] or ""
        job_item = result[3] or ""
        content = result[4] or ""
        files_json = result[5] or "[]"
        
        # 解析檔案 JSON
        files = []
        try:
            files = json.loads(files_json) if files_json != "[]" else []
        except Exception as e:
            logger.error(f"JSON解析失敗: {e}")
            files = []
        
        # 處理 AI 參考檔案（轉換為 attachments 格式）
        attachments = []
        if files:
            for file in files:
                if file.get("is_selected_for_ai", False):
                    attachments.append({
                        "att_id": f"files_{file.get('name', 'unknown')}",
                        "file_name": file.get("name", "unknown"),
                        "file_path": file.get("url", ""),
                        "file_size": file.get("size", 0),
                        "file_type": file.get("type", ""),
                        "is_selected_for_ai": True
                    })
        
        # 調用 service 層生成 AI 內容
        ai_content = await _generate_enhanced_weekly_content(
            original_content=content,
            subject=subject,
            job_item=job_item,
            attachments=attachments,
            ai_service=ai_service
        )
        
        logger.info(f"AI 潤飾完成，結果長度: {len(ai_content) if ai_content else 0}")
        
        # 更新資料庫 - 存入 ai_content 和 ai_service
        update_sql = text("""
            UPDATE jps.tdr_weekly_draft
            SET ai_content = :ai_content,
            ai_service = :ai_service,
            updated_date = TO_CHAR(sysdate, 'YYYYMMDD'),
            updated_time = TO_CHAR(sysdate, 'HH24:MI:SS')
            WHERE weekly_no = :weekly_no
              AND seq = :seq
              AND empno = :empno
              AND cocode = :cocode
        """)
        
        await run_in_threadpool(
            lambda: db.execute(update_sql, {
                "weekly_no": weekly_no,
                "seq": seq,
                "empno": empno,
                "cocode": cocode,
                "ai_content": ai_content,
                "ai_service": ai_service
            })
        )
        
        await run_in_threadpool(db.commit)
        
        logger.info(f"✅ AI 內容已存入資料庫")
        
        return {
            "success": True,
            "message": f"筆記 {subject} 已完成 AI 潤飾",
            "ai_content": ai_content,
            "weekly_no": weekly_no,
            "seq": seq
        }
        
    except HTTPException:
        await run_in_threadpool(db.rollback)
        raise
    except Exception as e:
        await run_in_threadpool(db.rollback)
        logger.error(f"AI 潤飾失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"AI 潤飾失敗: {str(e)}")


@router.post("/overdue-ar")
async def get_overdue_ar(
    payload: Dict[str, Any],
    current_user: UserSchema = Depends(get_current_user)
):
    """
    獲取逾期應收帳款 - 轉發到 CommonAPI

    payload: {
        "year": 2025,
        "week_no": 1,
        "empno": "12345"  // 可選，若不傳則使用當前用戶的工號
    }
    """
    import httpx
    from app.core.config import settings

    try:
        # 若有傳入 empno 則使用傳入的，否則使用當前用戶的工號
        empno = payload.get("empno") or current_user.employee.empno
        deptno = current_user.employee.deptno or ""

        # 構建請求參數（測試用固定值）
        request_data = {
            "empno": empno,
            "deptno": deptno,
            "year": payload.get("year", 0),
            "week_no": payload.get("week_no", 0)
        }

        # 調用 CommonAPI
        commonapi_url = settings.OVERDUE_AR_API_URL
        logger.info(f"調用 CommonAPI 逾期應收帳款: {commonapi_url}, params={request_data}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                commonapi_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"CommonAPI 返回錯誤: {response.status_code}, {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"CommonAPI 調用失敗: {response.text}"
                )

            result = response.json()
            logger.info(f"CommonAPI 返回成功，資料筆數: {len(result.get('ResponseData', []))}")

            return result

    except httpx.TimeoutException:
        logger.error("CommonAPI 請求超時")
        raise HTTPException(status_code=504, detail="請求超時")
    except httpx.RequestError as e:
        logger.error(f"CommonAPI 請求錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"請求錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"獲取逾期應收帳款失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"獲取逾期應收帳款失敗: {str(e)}")


@router.post("/revenue")
async def get_revenue(
    payload: Dict[str, Any],
    current_user: UserSchema = Depends(get_current_user)
):
    """
    獲取營收達成率 - 轉發到 CommonAPI

    payload: {
        "year": 2025,
        "week_no": 1,
        "empno": "12345"  // 可選，若不傳則使用當前用戶的工號
    }
    """
    import httpx
    from app.core.config import settings

    try:
        # 若有傳入 empno 則使用傳入的，否則使用當前用戶的工號
        empno = payload.get("empno") or current_user.employee.empno

        # 構建請求參數（測試用固定值）
        request_data = {
            "empno": empno,
            "year": payload.get("year", 0),
            "week_no": payload.get("week_no", 0)
        }

        # 調用 CommonAPI
        commonapi_url = settings.REVENUE_API_URL
        logger.info(f"調用 CommonAPI 營收達成率: {commonapi_url}, params={request_data}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                commonapi_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"CommonAPI 返回錯誤: {response.status_code}, {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"CommonAPI 調用失敗: {response.text}"
                )

            result = response.json()
            # logger.info(f"CommonAPI 返回成功，資料筆數: {len(result.get('ResponseData', []))}")

            return result

    except httpx.TimeoutException:
        logger.error("CommonAPI 請求超時")
        raise HTTPException(status_code=504, detail="請求超時")
    except httpx.RequestError as e:
        logger.error(f"CommonAPI 請求錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"請求錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"獲取營收達成率失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"獲取營收達成率失敗: {str(e)}")


@router.post("/submit-weekly-report")
async def submit_weekly_report(
    payload: Dict[str, Any],
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    提交週報 - 轉發到 CommonAPI

    payload: {
        "weekly_no": "12345",
        "year": 2025,
        "week_no": 48
    }
    """
    import httpx
    from app.core.config import settings
    from datetime import datetime

    try:
        # 使用當前用戶的資訊
        empno = current_user.employee.empno
        empname = current_user.employee.empnamec or current_user.employee.name or ""
        cocode = current_user.employee.cocode or "A"
        deptno = current_user.employee.deptno or ""
        g_deptno = current_user.employee.g_deptno or ""
        deptname = current_user.employee.department_name or ""

        weekly_no = payload.get("weekly_no", "")
        year = payload.get("year", 0)
        week_no = payload.get("week_no", 0)

        # 查詢該週報的所有草稿，組合成 content
        sql = text("""
            SELECT subject, job_item, content, att_file1, att_file2
            FROM jps.tdr_weekly_draft
            WHERE weekly_no = :weekly_no
              AND empno = :empno
              AND cocode = :cocode
              AND (status IS NULL OR status != 'D')
            ORDER BY seq
        """)

        drafts = db.execute(sql, {
            "weekly_no": weekly_no,
            "empno": empno,
            "cocode": cocode
        }).fetchall()

        # 組合多筆 draft 為 content 陣列
        content_list = []
        for draft in drafts:
            subject = draft[0] or ""
            job_item = draft[1] or ""
            content = draft[2] or ""
            att_file1 = draft[3] or ""
            att_file2 = draft[4] or ""

            # 每筆 draft 對應一個 content 對象
            content_obj = {
                "m_attfile1": att_file1,
                "m_attfile2": att_file2,
                "planno": "",
                "SUBJECT": subject,
                "JOB_ITEM": job_item,
                "PROJNO": "",
                "CUNO": "",
                "SUNO": "",
                "CATENO1": "",
                "CATENO2": "",
                "CATENO3": "",
                "CATENO4": "",
                "CONTENT4": "",
                "CONTENT1": "",
                "CONTENT2": "",
                "CONTENT": content
            }
            content_list.append(content_obj)

        # 計算週的開始和結束日期
        from app.utils.weekUtils import get_week_start_date, get_week_end_date
        sdate = get_week_start_date(year, week_no)  # YYYYMMDD
        edate = get_week_end_date(year, week_no)    # YYYYMMDD

        # 構建請求參數
        request_data = {
            "cocode": cocode,
            "deptno": deptno,
            "g_deptno": g_deptno,
            "deptname": deptname,
            "empno": empno,
            "empname": empname,
            "status": "N",  # S = Submitted
            "change": "N",  # N = New
            "WeeklyNo": int(weekly_no),
            "year": str(year),
            "sdate": sdate,
            "edate": edate,
            "end_date": edate,
            "week_no": str(week_no),
            "details": content_list, # 改為陣列，支援多筆 draft
            "classify": True,
            "emergency": False
        }

        # 調用 CommonAPI
        commonapi_url = settings.SUBMIT_WEEKLY_REPORT_API_URL
        logger.info(f"調用 CommonAPI 提交週報: {commonapi_url}, weekly_no={weekly_no}")
        logger.info(f"提交週報 Payload: {json.dumps(request_data, ensure_ascii=False)}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                commonapi_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"CommonAPI 返回錯誤: {response.status_code}, {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"CommonAPI 調用失敗: {response.text}"
                )

            result = response.json()
            logger.info(f"CommonAPI 返回成功: {result}")

            # 檢查提交是否成功
            if result.get("ResponseNa") == '週報儲存成功':
                # 更新草稿狀態為已提交
                update_sql = text("""
                    UPDATE jps.tdr_weekly_draft
                    SET status = 'S',
                        updated_date = :updated_date,
                        updated_time = :updated_time
                    WHERE weekly_no = :weekly_no
                      AND empno = :empno
                      AND cocode = :cocode
                      AND (status IS NULL OR status != 'D')
                """)

                now = datetime.now()
                db.execute(update_sql, {
                    "weekly_no": weekly_no,
                    "empno": empno,
                    "cocode": cocode,
                    "updated_date": now.strftime("%Y%m%d"),
                    "updated_time": now.strftime("%H:%M:%S")
                })
                db.commit()

                logger.info(f"週報提交成功，已更新草稿狀態: {weekly_no}")

            return result

    except httpx.TimeoutException:
        logger.error("CommonAPI 請求超時")
        raise HTTPException(status_code=504, detail="請求超時")
    except httpx.RequestError as e:
        logger.error(f"CommonAPI 請求錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"請求錯誤: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"提交週報失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"提交週報失敗: {str(e)}")


@router.get("/report-detail/{weekly_no}")
async def get_weekly_report_detail(
    weekly_no: str,
    current_user: UserSchema = Depends(get_current_user)
):
    """
    獲取週報詳情（包含主檔、明細、回覆）

    Args:
        weekly_no: 週報編號
        current_user: 當前登入使用者

    Returns:
        ShowWeeklyReportResponse: 週報詳細資料
    """
    import httpx
    from app.core.config import settings

    try:
        # 從使用者資訊獲取 empno
        empno = current_user.employee.empno

        logger.info(f"獲取週報詳情: weekly_no={weekly_no}, empno={empno}")

        # 準備請求資料
        request_data = {
            "weekly_no": int(weekly_no),
            "empno": empno,
            "fromWfinbox": False
        }

        logger.info(f"調用 CommonAPI: {settings.SHOW_WEEKLY_REPORT_API_URL}")
        logger.info(f"請求參數: {request_data}")

        # 調用 CommonAPI
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.SHOW_WEEKLY_REPORT_API_URL,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"CommonAPI 回應狀態: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"CommonAPI 回應錯誤: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"CommonAPI 回應錯誤: {response.text}"
                )

            result = response.json()
            logger.info(f"CommonAPI 回應: ResponseNo={result.get('ResponseNo')}, ResponseNa={result.get('ResponseNa')}")

            # 檢查 CommonAPI 回傳的狀態
            if result.get("ResponseNo") != "0000":
                logger.warning(f"CommonAPI 回傳錯誤: {result.get('ResponseNa')}")
                raise HTTPException(
                    status_code=400,
                    detail=result.get("ResponseNa", "獲取週報詳情失敗")
                )

            return result

    except httpx.TimeoutException:
        logger.error("CommonAPI 請求超時")
        raise HTTPException(status_code=504, detail="請求超時")
    except httpx.RequestError as e:
        logger.error(f"CommonAPI 請求錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"請求錯誤: {str(e)}")
    except Exception as e:
        logger.error(f"獲取週報詳情失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"獲取週報詳情失敗: {str(e)}")


@router.get("/forward/candidates")
async def get_forward_candidates(
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    獲取轉寄候選人名單

    Returns:
        - user_adm_rank: 當前用戶的管理員級別
        - candidates: 轉寄候選人列表（包含職稱和部門）
    """
    try:
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or "A"

        logger.info(f"獲取轉寄候選人: empno={empno}, cocode={cocode}")

        # 1. 查詢當前用戶的 adm_rank（管理員級別）
        user_rank_sql = text("""
            SELECT adm_rank FROM jps.dcd003$master
            WHERE empno = :empno AND cocode = :cocode
        """)
        rank_result = db.execute(user_rank_sql, {
            "empno": empno,
            "cocode": cocode
        }).fetchone()

        if not rank_result:
            raise HTTPException(status_code=404, detail="找不到用戶資料")

        adm_rank = int(rank_result[0]) if rank_result[0] else 99

        candidates = []

        # 2. 基礎職稱轉寄名單（所有人都能用）
        title_sql = text("""
            SELECT a.empno, a.empname, 'title' AS type
            FROM jps.tdr_forward_visor a
            LEFT JOIN jps.dcd003$master b ON a.empno = b.empno
                AND b.estatus <> '3'
                AND (b.RIGHT_STOP_DATE IS NULL OR b.RIGHT_STOP_DATE <= TO_CHAR(sysdate, 'yyyyMMdd'))
                AND cocode IN (SELECT cocode FROM jps.dcd001$master WHERE eip_active = 'Y')
            ORDER BY a.sorting
        """)
        title_rows = db.execute(title_sql).fetchall()
        candidates.extend([{
            "empno": row[0],
            "empname": row[1],
            "type": row[2]
        } for row in title_rows])

        logger.info(f"基礎職稱轉寄名單數量: {len(candidates)}, adm_rank={adm_rank}")

        return {
            "user_adm_rank": adm_rank,
            "candidates": candidates
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取轉寄候選人失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"獲取轉寄候選人失敗: {str(e)}")


@router.get("/forward/employees")
async def get_forward_employees(
    db: Session = Depends(get_legacy_db)
):
    """
    獲取部門轉寄員工列表（使用 CorpEmployeeService.load_forward）

    Returns:
        三層結構的員工資料：
        - 第一層: 業務單位/幕僚單位
        - 第二層: 部門名稱
        - 第三層: 員工列表
    """
    try:
        logger.info("獲取部門轉寄員工列表")

        # 1. 從 tdr_forward_duty 表取得職稱列表
        duty_sql = text("""
            SELECT DISTINCT dutyname
            FROM jps.tdr_forward_duty
            ORDER BY dutyname
        """)
        duty_result = db.execute(duty_sql).fetchall()
        ls_forward_duty = [row[0] for row in duty_result]

        logger.info(f"職稱列表數量: {len(ls_forward_duty)}")

        # 2. 調用 CorpEmployeeService 載入轉寄資料
        from app.services.corp_employee_service import CorpEmployeeService
        corp_service = CorpEmployeeService()
        forward_data = corp_service.load_forward(
            ls_forward_duty=ls_forward_duty,
            table_name="tdr_forward_employees"
        )

        logger.info(f"成功載入部門轉寄資料，組織單位數量: {len(forward_data)}")

        return {
            "success": True,
            "data": forward_data
        }

    except Exception as e:
        logger.error(f"獲取部門轉寄員工列表失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"獲取部門轉寄員工列表失敗: {str(e)}")


@router.post("/reports/{weekly_no}/ai-suggestions")
async def get_ai_suggestions(
    weekly_no: str,
    request_data: Dict[str, Any],
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    獲取 AI 回覆建議

    Args:
        weekly_no: 週報編號
        request_data: 包含 rating（評分）的請求資料
        current_user: 當前登入使用者
        db: 資料庫連線

    Returns:
        AI 生成的回覆建議列表
    """
    from app.services.ai_suggestion_service import generate_supervisor_reply_suggestions

    try:
        rating = request_data.get("rating")

        logger.info(f"獲取 AI 建議: weekly_no={weekly_no}, rating={rating}")

        # 1. 查詢週報內容
        sql = text("""
            SELECT subject, job_item, content
            FROM jps.tdr_weekly_draft
            WHERE weekly_no = :weekly_no
              AND (status IS NULL OR status != 'D')
            ORDER BY seq
        """)

        results = db.execute(sql, {"weekly_no": weekly_no}).fetchall()

        if not results:
            raise HTTPException(status_code=404, detail="找不到週報內容")

        # 2. 組合週報內容
        report_parts = []
        employee_name = "員工"  # 預設名稱

        for row in results:
            subject = row[0] or ""
            job_item = row[1] or ""
            content = row[2] or ""

            if subject or content:
                report_parts.append(f"【{job_item}】{subject}\n{content}")

        report_content = "\n\n".join(report_parts)

        # 3. 從週報主檔取得員工姓名
        master_sql = text("""
            SELECT d.empno, d.empnamec
            FROM jps.tdr_weekly_draft w
            JOIN jps.dcd003$master d ON w.empno = d.empno AND w.cocode = d.cocode
            WHERE w.weekly_no = :weekly_no
            LIMIT 1
        """)

        master_result = db.execute(master_sql, {"weekly_no": weekly_no}).fetchone()
        if master_result and master_result[1]:
            employee_name = master_result[1]

        logger.info(f"週報作者: {employee_name}, 內容長度: {len(report_content)}")

        # 4. 調用 AI 服務生成建議
        suggestions = await generate_supervisor_reply_suggestions(
            report_content=report_content,
            employee_name=employee_name,
            rating=rating,
            recent_context=None
        )

        logger.info(f"AI 建議生成成功，數量: {len(suggestions)}")

        return {
            "suggestions": suggestions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取 AI 建議失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"獲取 AI 建議失敗: {str(e)}")


@router.post("/reply")
async def reply_weekly_report(
    request_data: ReplyWeeklyReportRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    回覆週報 - 轉發到 CommonAPI

    Args:
        request_data: 回覆請求資料
        current_user: 當前登入使用者（回覆者）
        db: 資料庫連線

    Returns:
        ReplyWeeklyReportResponse: 回覆結果
    """
    import httpx
    from app.core.config import settings
    from datetime import datetime

    try:
        # 1. 獲取回覆者資訊
        empno = current_user.employee.empno
        empname = current_user.employee.empnamec or current_user.employee.name or ""
        cocode = current_user.employee.cocode or "A"

        weekly_no = request_data.weekly_no

        logger.info(f"回覆週報: weekly_no={weekly_no}, 回覆者={empno} {empname}")

        # 2. 查詢週報資料，獲取年份、週次、日期
        sql = text("""
            SELECT DISTINCT
                TO_CHAR(TO_DATE(doc_date, 'YYYYMMDD'), 'IYYY') as year,
                TO_CHAR(TO_DATE(doc_date, 'YYYYMMDD'), 'IW') as week_no,
                doc_date
            FROM jps.tdr_weekly_draft
            WHERE weekly_no = :weekly_no
            LIMIT 1
        """)

        result = db.execute(sql, {"weekly_no": weekly_no}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail=f"找不到週報編號: {weekly_no}")

        year = int(result[0])
        week_no = int(result[1])
        doc_date = result[2]  # YYYYMMDD 格式

        # 3. 查詢所有工作項目並組合
        job_items_sql = text("""
            SELECT DISTINCT job_item
            FROM jps.tdr_weekly_draft
            WHERE weekly_no = :weekly_no
              AND job_item IS NOT NULL
              AND (status IS NULL OR status != 'D')
            ORDER BY job_item
        """)

        job_items_result = db.execute(job_items_sql, {"weekly_no": weekly_no}).fetchall()
        job_items = [row[0] for row in job_items_result if row[0]]

        # 組合工作項目（用逗號分隔）
        job_item = ", ".join(job_items) if job_items else ""

        logger.info(f"週報資訊: year={year}, week_no={week_no}, doc_date={doc_date}, job_item={job_item}")

        # 4. 準備 CommonAPI 請求參數
        commonapi_request = {
            "year": year,
            "week_no": week_no,
            "weekly_report_no": int(weekly_no),
            "doc_date": datetime.now().strftime("%Y%m%d"),  # 當前回覆時間
            "cocode": cocode,
            "empno": empno,  # 回覆者
            "empname": empname,  # 回覆者
            "reply": request_data.reply_memo,
            "score": str(request_data.score) if request_data.score else "",  # 評分轉字串，無評分時傳空字串
            "touser": request_data.to_users,
            "fwuser": request_data.forward_users,
            "job_item": job_item
        }

        logger.info(f"調用 CommonAPI 回覆週報: {settings.REPLY_WEEKLY_REPORT_API_URL}")
        logger.info(f"請求參數: {commonapi_request}")

        # 5. 調用 CommonAPI
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.REPLY_WEEKLY_REPORT_API_URL,
                json=commonapi_request,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"CommonAPI 回應狀態: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"CommonAPI 回應錯誤: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"CommonAPI 回應錯誤: {response.text}"
                )

            result = response.json()
            logger.info(f"CommonAPI 回應: ResponseNo={result.get('ResponseNo')}, ResponseNa={result.get('ResponseNa')}")

            # 檢查 CommonAPI 回傳的狀態
            if result.get("ResponseNo") != "0000":
                logger.warning(f"CommonAPI 回傳錯誤: {result.get('ResponseNa')}")
                raise HTTPException(
                    status_code=400,
                    detail=result.get("ResponseNa", "回覆週報失敗")
                )

            return result

    except httpx.TimeoutException:
        logger.error("CommonAPI 請求超時")
        raise HTTPException(status_code=504, detail="請求超時")
    except httpx.RequestError as e:
        logger.error(f"CommonAPI 請求錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"請求錯誤: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"回覆週報失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"回覆週報失敗: {str(e)}")


@router.delete("/report/{weekly_no}")
async def delete_weekly_report(
    weekly_no: str,
    current_user: UserSchema = Depends(get_current_user)
):
    """
    刪除週報 - 轉發到 CommonAPI

    Args:
        weekly_no: 週報編號
        current_user: 當前登入使用者

    Returns:
        刪除結果

    業務規則：
    1. 只能刪除自己的週報
    2. 已被主管回覆的週報不能刪除（由 CommonAPI 檢查）
    """
    import httpx
    from app.core.config import settings

    try:
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or "A"

        logger.info(f"刪除週報: weekly_no={weekly_no}, empno={empno}, cocode={cocode}")

        # 準備 CommonAPI 請求參數
        request_data = {
            "cocode": cocode,
            "empno": empno,
            "weekly_no": int(weekly_no)
        }

        # 調用 CommonAPI 刪除週報
        commonapi_url = settings.DELETE_WEEKLY_REPORT_API_URL
        logger.info(f"調用 CommonAPI 刪除週報: {commonapi_url}")
        logger.info(f"請求參數: {request_data}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                commonapi_url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"CommonAPI 回應狀態: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"CommonAPI 回應錯誤: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"CommonAPI 回應錯誤: {response.text}"
                )

            result = response.json()
            logger.info(f"CommonAPI 回應: ResponseNo={result.get('ResponseNo')}, ResponseNa={result.get('ResponseNa')}")

            # 檢查 CommonAPI 回傳的狀態
            if result.get("ResponseNo") != "0000":
                logger.warning(f"CommonAPI 回傳錯誤: {result.get('ResponseNa')}")
                raise HTTPException(
                    status_code=400,
                    detail=result.get("ResponseNa", "刪除週報失敗")
                )

            return result

    except httpx.TimeoutException:
        logger.error("CommonAPI 請求超時")
        raise HTTPException(status_code=504, detail="請求超時")
    except httpx.RequestError as e:
        logger.error(f"CommonAPI 請求錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"請求錯誤: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除週報失敗: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"刪除週報失敗: {str(e)}")