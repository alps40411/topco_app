# backend/app/services/legacy_service_v2.py

import json
import logging
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..schemas.legacy_schemas import DailyReportListItem, DailyReportContent, WorkPlan

logger = logging.getLogger(__name__)

class LegacyReportServiceV2:
    """Legacy 日報服務 - 支援新的 tdr_draft 資料表結構和完整的 legacy 資料庫操作"""
    
    @staticmethod
    def get_project_name_by_planno(db: Session, planno: str) -> str:
        """根據工作計畫編號取得專案名稱"""
        try:
            if not planno:
                return ""
            
            plan_sql = text("SELECT plan_subj_c FROM jps.tjp_master WHERE planno = :planno")
            plan_result = db.execute(plan_sql, {"planno": planno}).fetchone()
            if plan_result:
                return plan_result[0] or ""
            return ""
        except Exception as e:
            logger.error(f"Error getting project name for planno {planno}: {str(e)}")
            return ""
    
    @staticmethod
    def save_draft(db: Session, empno: str, cocode: str, doc_date: str, 
                   draft_type: str, draft_content: Dict[str, Any], daily_no: Optional[str] = None) -> str:
        """保存日報暫存 - 使用新的資料表結構，支援 daily_no 生成和合併邏輯"""
        try:
            # 確保交易狀態正常
            try:
                db.rollback()
            except:
                pass
                
            # 取得目前日期時間
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 從 tjp_master 取得工作計畫和執行工作的中文名稱
            planno = draft_content.get('planno', '')
            sopno = draft_content.get('sopno', '')
            plan_subj_c = ''
            sop_desc_c = ''
            
            if planno:
                plan_sql = text("SELECT plan_subj_c FROM jps.tjp_master WHERE planno = :planno")
                plan_result = db.execute(plan_sql, {"planno": planno}).fetchone()
                if plan_result:
                    plan_subj_c = plan_result[0] or ''
            
            if sopno:
                try:
                    # 統一從 tpm_sop 取得正確的執行工作描述
                    sop_sql = text("SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno")
                    sop_result = db.execute(sop_sql, {"sopno": sopno}).fetchone()
                    if sop_result:
                        sop_desc_c = sop_result[0] or ''
                    else:
                        # 如果 tpm_sop 中沒找到，使用傳入的值作為備用
                        sop_desc_c = draft_content.get('sop_desc_c', '')
                except Exception as e:
                    logger.warning(f"無法取得 sopno {sopno} 的執行工作描述: {str(e)}")
                    sop_desc_c = draft_content.get('sop_desc_c', '')
            
            # 處理工作項目序列
            work_item_seq = draft_content.get('work_item_seq', [])
            if isinstance(work_item_seq, list):
                work_item_seq_str = '/'.join(work_item_seq)
            else:
                work_item_seq_str = str(work_item_seq) if work_item_seq else ''
            
            # 計算字數
            content = draft_content.get('content', '')
            word_count = len(content) if content else 0
            
            # 處理檔案 - 支援多檔案，用逗號分隔
            files = draft_content.get('files', [])
            att_file1_list = []  # 檔案名稱列表
            att_file2_list = []  # 檔案路徑列表
            files_json_list = []  # 完整檔案資訊列表
            
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
            
            # 處理 daily_no 邏輯
            if daily_no:
                # 使用前端提供的 daily_no
                logger.info(f"使用前端提供的 daily_no: {daily_no}")
            else:
                # 查找今天是否已經有暫存記錄
                existing_daily_sql = text("""
                    SELECT DAILY_NO
                    FROM jps.tdr_draft
                    WHERE EMPNO = :empno 
                    AND COCODE = :cocode
                    AND DOC_DATE = :doc_date
                    LIMIT 1
                """)
                
                existing_daily_result = db.execute(existing_daily_sql, {
                    "empno": empno,
                    "cocode": cocode,
                    "doc_date": doc_date
                }).fetchone()
                
                if existing_daily_result:
                    # 今天已經有暫存記錄，使用現有的 daily_no
                    daily_no = existing_daily_result[0]
                    logger.info(f"今天已有暫存記錄，使用現有 daily_no: {daily_no}")
                else:
                    # 今天第一次填寫，取得新的 daily_no
                    try:
                        # 嘗試使用 Oracle 序列
                        daily_no_sql = text("SELECT seq_tdr_master.nextval FROM dual")
                        daily_no_result = db.execute(daily_no_sql).fetchone()
                        daily_no = str(daily_no_result[0])
                    except Exception as e:
                        # 如果序列不存在或出錯，使用時間戳記
                        logger.warning(f"無法使用序列取得 daily_no: {str(e)}，使用時間戳記")
                        daily_no = f"DR{current_date}{current_time.replace(':', '')}"
                    logger.info(f"今天第一次填寫，創建新 daily_no: {daily_no}")
            
            # 檢查是否已存在相同 planno + sopno + work_item_seq 組合的記錄
            existing_exact_match_sql = text("""
                SELECT RECORD_ID, DAILY_NO, CONTENT, EXECUTION_TIME_MINUTES, WORK_ITEM_SEQ, 
                       WORD_COUNT, ATT_FILE1, ATT_FILE2, FILES
                FROM jps.tdr_draft
                WHERE DAILY_NO = :daily_no 
                AND COALESCE(PLANNO, '') = COALESCE(:planno, '')
                AND COALESCE(SOPNO, '') = COALESCE(:sopno, '')
                AND COALESCE(WORK_ITEM_SEQ, '') = COALESCE(:work_item_seq, '')
            """)
            
            existing_exact_match = db.execute(existing_exact_match_sql, {
                "daily_no": daily_no,
                "planno": planno,
                "sopno": sopno,
                "work_item_seq": work_item_seq_str
            }).fetchone()
            
            if existing_exact_match:
                # 完全相同的工作計畫+執行工作+工作項目：合併內容
                logger.info(f"找到完全相同的 planno({planno})+sopno({sopno})+work_item_seq({work_item_seq_str}) 組合，合併內容")
                
                # 合併內容
                existing_content = existing_exact_match[2] or ""
                merged_content = f"{existing_content}\n{content}".strip() if existing_content else content
                
                # 累加執行時間
                existing_time = existing_exact_match[3] or 0
                total_time = existing_time + draft_content.get('execution_time_minutes', 0)
                
                # 工作項目序列保持不變（因為完全相同）
                merged_work_items = work_item_seq_str
                
                # 計算新的字數
                merged_word_count = len(merged_content) if merged_content else 0
                
                # 合併檔案和更新 att_file1、att_file2
                existing_files = existing_exact_match[8] or "[]"
                existing_att_file1 = existing_exact_match[6] or ""  # 現有的檔案名稱
                existing_att_file2 = existing_exact_match[7] or ""  # 現有的檔案路徑
                
                # 合併檔案 JSON
                if files_json and files_json != "[]":
                    try:
                        existing_files_list = json.loads(existing_files) if existing_files != "[]" else []
                        new_files_list = json.loads(files_json)
                        merged_files_list = existing_files_list + new_files_list
                        merged_files = json.dumps(merged_files_list)
                    except:
                        merged_files = files_json
                else:
                    merged_files = existing_files
                
                # 合併 att_file1 (檔案名稱) 和 att_file2 (檔案路徑)
                merged_att_file1 = existing_att_file1 or ""
                merged_att_file2 = existing_att_file2 or ""
                
                if att_file1:  # 有新的檔案名稱
                    if merged_att_file1:
                        merged_att_file1 += "," + att_file1
                    else:
                        merged_att_file1 = att_file1
                        
                if att_file2:  # 有新的檔案路徑
                    if merged_att_file2:
                        merged_att_file2 += "," + att_file2
                    else:
                        merged_att_file2 = att_file2
                
                # 更新現有記錄
                update_sql = text("""
                    UPDATE jps.tdr_draft 
                    SET PLAN_SUBJ_C = :plan_subj_c,
                        SOP_DESC_C = :sop_desc_c,
                        WORK_ITEM_SEQ = :work_item_seq,
                        SERVICE_COCODE = COALESCE(:service_cocode, SERVICE_COCODE),
                        SERVICE_EMPNO = COALESCE(:service_empno, SERVICE_EMPNO),
                        SERVICE_EMPNAMEC = COALESCE(:service_empnamec, SERVICE_EMPNAMEC),
                        SERVICE_DEPTNO = COALESCE(:service_deptno, SERVICE_DEPTNO),
                        CONTENT = :content,
                        EXECUTION_TIME_MINUTES = :execution_time_minutes,
                        WORD_COUNT = :word_count,
                        ATT_FILE1 = :att_file1,
                        ATT_FILE2 = :att_file2,
                        FILES = :files,
                        UPDATED_DATE = :updated_date,
                        UPDATED_TIME = :updated_time
                    WHERE RECORD_ID = :record_id
                """)
                
                update_params = {
                    "plan_subj_c": plan_subj_c,
                    "sop_desc_c": sop_desc_c,
                    "work_item_seq": merged_work_items,
                    "service_cocode": draft_content.get('service_cocode'),
                    "service_empno": draft_content.get('service_empno'),
                    "service_empnamec": draft_content.get('service_empnamec'),
                    "service_deptno": draft_content.get('service_deptno'),
                    "content": merged_content,
                    "execution_time_minutes": total_time,
                    "word_count": merged_word_count,
                    "att_file1": merged_att_file1,
                    "att_file2": merged_att_file2,
                    "files": merged_files,
                    "updated_date": current_date,
                    "updated_time": current_time,
                    "record_id": existing_exact_match[0]
                }

                db.execute(update_sql, update_params)

                db.commit()
                logger.info(f"合併更新完成，record_id: {existing_exact_match[0]}，總執行時間: {total_time} 分鐘")
                return daily_no
                
            else:
                # 檢查是否存在相同 planno + sopno 但不同 work_item_seq 的記錄
                existing_partial_match_sql = text("""
                    SELECT RECORD_ID, WORK_ITEM_SEQ
                    FROM jps.tdr_draft
                    WHERE DAILY_NO = :daily_no 
                    AND COALESCE(PLANNO, '') = COALESCE(:planno, '')
                    AND COALESCE(SOPNO, '') = COALESCE(:sopno, '')
                    AND COALESCE(WORK_ITEM_SEQ, '') != COALESCE(:work_item_seq, '')
                """)
                
                existing_partial_matches = db.execute(existing_partial_match_sql, {
                    "daily_no": daily_no,
                    "planno": planno,
                    "sopno": sopno,
                    "work_item_seq": work_item_seq_str
                }).fetchall()
                
                if existing_partial_matches:
                    # 相同工作計畫+執行工作，但不同工作項目：合併工作項目序列
                    logger.info(f"找到相同 planno({planno})+sopno({sopno})，但不同工作項目，合併工作項目序列")
                    
                    # 收集所有現有的工作項目序列
                    existing_work_item_seqs = []
                    for match in existing_partial_matches:
                        existing_seq = match[1] or ""
                        if existing_seq:
                            existing_work_item_seqs.extend(existing_seq.split('/'))
                    
                    # 新增當前的工作項目序列
                    if work_item_seq_str:
                        existing_work_item_seqs.extend(work_item_seq_str.split('/'))
                    
                    logger.info(f"合併前的工作項目序列: {existing_work_item_seqs}")
                    
                    # 去重並排序 - 確保去除空白字串
                    unique_seqs = sorted(list(set(seq.strip() for seq in existing_work_item_seqs if seq and seq.strip())))
                    final_work_item_seq = '/'.join(unique_seqs)
                    
                    logger.info(f"去重後的工作項目序列: {final_work_item_seq}")
                    
                    # 更新第一個匹配的記錄，合併工作項目序列
                    first_match_id = existing_partial_matches[0][0]
                    
                    # 合併檔案資訊
                    existing_record_sql = text("""
                        SELECT ATT_FILE1, ATT_FILE2, FILES
                        FROM jps.tdr_draft
                        WHERE RECORD_ID = :record_id
                    """)
                    existing_record = db.execute(existing_record_sql, {"record_id": first_match_id}).fetchone()

                    existing_att_file1 = existing_record[0] or "" if existing_record else ""
                    existing_att_file2 = existing_record[1] or "" if existing_record else ""
                    existing_files = existing_record[2] or "[]" if existing_record else "[]"

                    # 合併檔案
                    merged_att_file1 = existing_att_file1
                    merged_att_file2 = existing_att_file2

                    if att_file1:
                        merged_att_file1 = f"{merged_att_file1},{att_file1}" if merged_att_file1 else att_file1
                    if att_file2:
                        merged_att_file2 = f"{merged_att_file2},{att_file2}" if merged_att_file2 else att_file2

                    # 合併 files JSON
                    if files_json and files_json != "[]":
                        try:
                            existing_files_list = json.loads(existing_files) if existing_files != "[]" else []
                            new_files_list = json.loads(files_json)
                            merged_files_list = existing_files_list + new_files_list
                            merged_files = json.dumps(merged_files_list, ensure_ascii=False)
                        except:
                            merged_files = files_json
                    else:
                        merged_files = existing_files

                    update_partial_sql = text("""
                        UPDATE jps.tdr_draft
                        SET WORK_ITEM_SEQ = :work_item_seq,
                            CONTENT = COALESCE(CONTENT, '') || CASE WHEN COALESCE(CONTENT, '') = '' THEN '' ELSE '\n' END || :new_content,
                            EXECUTION_TIME_MINUTES = COALESCE(EXECUTION_TIME_MINUTES, 0) + :additional_time,
                            WORD_COUNT = CHAR_LENGTH(COALESCE(CONTENT, '') || CASE WHEN COALESCE(CONTENT, '') = '' THEN '' ELSE '\n' END || :new_content),
                            ATT_FILE1 = :att_file1,
                            ATT_FILE2 = :att_file2,
                            FILES = :files,
                            UPDATED_DATE = :updated_date,
                            UPDATED_TIME = :updated_time
                        WHERE RECORD_ID = :record_id
                    """)



                    db.execute(update_partial_sql, {
                        "work_item_seq": final_work_item_seq,
                        "new_content": content,
                        "additional_time": draft_content.get('execution_time_minutes', 0),
                        "att_file1": merged_att_file1,
                        "att_file2": merged_att_file2,
                        "files": merged_files,
                        "updated_date": current_date,
                        "updated_time": current_time,
                        "record_id": first_match_id
                    })
                    
                    db.commit()
                    logger.info(f"合併工作項目序列完成，最終序列: {final_work_item_seq}")
                    return daily_no
                else:
                    # 完全不同的工作計畫+執行工作：新增一筆記錄
                    logger.info(f"完全不同的 planno({planno})+sopno({sopno}) 組合，新增記錄（daily_no: {daily_no}）")
                
                insert_sql = text("""
                    INSERT INTO jps.tdr_draft (
                        DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE,
                        PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C, WORK_ITEM_SEQ,
                        SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC, SERVICE_DEPTNO,
                        CONTENT, EXECUTION_TIME_MINUTES, WORD_COUNT,
                        ATT_FILE1, ATT_FILE2, FILES,
                        STATUS, CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME
                    ) VALUES (
                        :daily_no, :empno, :cocode, :doc_date, :draft_type,
                        :planno, :plan_subj_c, :sopno, :sop_desc_c, :work_item_seq,
                        :service_cocode, :service_empno, :service_empnamec, :service_deptno,
                        :content, :execution_time_minutes, :word_count,
                        :att_file1, :att_file2, :files,
                        'A', :created_date, :created_time, :updated_date, :updated_time
                    )
                """)
                
                insert_params = {
                    "daily_no": daily_no,
                    "empno": empno,
                    "cocode": cocode,
                    "doc_date": doc_date,
                    "draft_type": draft_type,
                    "planno": planno,
                    "plan_subj_c": plan_subj_c,
                    "sopno": sopno,
                    "sop_desc_c": sop_desc_c,
                    "work_item_seq": work_item_seq_str,
                    "service_cocode": draft_content.get('service_cocode'),
                    "service_empno": draft_content.get('service_empno'),
                    "service_empnamec": draft_content.get('service_empnamec'),
                    "service_deptno": draft_content.get('service_deptno'),
                    "content": content,
                    "execution_time_minutes": draft_content.get('execution_time_minutes', 0),
                    "word_count": word_count,
                    "att_file1": att_file1,
                    "att_file2": att_file2,
                    "files": files_json,
                    "created_date": current_date,
                    "created_time": current_time,
                    "updated_date": current_date,
                    "updated_time": current_time
                }


                db.execute(insert_sql, insert_params)

                db.commit()
                logger.info(f"新增記錄完成，daily_no: {daily_no}")
                return daily_no
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving draft: {str(e)}")
            raise
    
    @staticmethod
    def get_today_drafts(db: Session, empno: str, cocode: str, doc_date: str) -> List[Dict[str, Any]]:
        """取得今日的暫存資料 - 使用新的資料表結構"""
        try:
            sql = text("""
                SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE,
                       PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C, WORK_ITEM_SEQ,
                       SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC, SERVICE_DEPTNO,
                       CONTENT, EXECUTION_TIME_MINUTES, WORD_COUNT,
                       ATT_FILE1, ATT_FILE2, FILES,
                       CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME, STATUS,
                       AI_CONTENT
                FROM jps.tdr_draft
                WHERE EMPNO = :empno 
                AND COCODE = :cocode
                AND DOC_DATE = :doc_date
                ORDER BY CREATED_DATE DESC, CREATED_TIME DESC
            """)
            
            result = db.execute(sql, {
                "empno": empno,
                "cocode": cocode,
                "doc_date": doc_date
            })
            
            drafts = []
            for row in result:
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
                    "updated_time": row[23],
                    "status": row[24],
                    "ai_content": row[25]
                }
                drafts.append(draft)
            
            return drafts
            
        except Exception as e:
            logger.error(f"Error getting today drafts: {str(e)}")
            return []
    
    @staticmethod
    def submit_draft_to_final(db: Session, daily_no: str, empno: str, cocode: str, 
                             doc_date: str) -> str:
        """將暫存提交為正式日報 - 使用新的資料表結構，支援多個工作計畫"""
        try:
            # 取得所有暫存資料（可能有多個工作計畫）
            draft_sql = text("""
                SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE,
                       PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C, WORK_ITEM_SEQ,
                       SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC, SERVICE_DEPTNO,
                       CONTENT, EXECUTION_TIME_MINUTES, WORD_COUNT,
                       ATT_FILE1, ATT_FILE2, FILES,
                       CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME, STATUS
                FROM jps.tdr_draft 
                WHERE DAILY_NO = :daily_no
                ORDER BY PLANNO, SOPNO
            """)
            draft_results = db.execute(draft_sql, {"daily_no": daily_no}).fetchall()
            
            if not draft_results:
                raise ValueError(f"Draft {daily_no} not found")
            
            # 使用原始的 COCODE（不需要轉換）
            original_cocode = cocode
            
            # 取得員工和部門資訊 (JOIN 部門主檔)
            emp_sql = text("""
                SELECT e.empnamec, e.deptno, d.deptnamec, e.g_deptno, e.leader
                FROM jps.dcd003$master e
                LEFT JOIN jps.dcd002$master d ON e.deptno = d.deptno AND e.cocode = d.cocode
                WHERE e.empno = :empno AND e.cocode = :original_cocode
            """)
            emp_result = db.execute(emp_sql, {"empno": empno, "original_cocode": original_cocode}).fetchone()
            
            if not emp_result:
                raise ValueError(f"Employee {empno} not found")
            
            empnamec, deptno, deptnamec, g_deptno, leader = emp_result
            
            # 取得目前日期時間
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 計算總字數和按 sopno 分組收集檔案
            total_word_count = 0
            all_att_file1 = None
            all_att_file2 = None
            sopno_groups = {}
            
            for draft in draft_results:
                total_word_count += draft[16] or 0  # WORD_COUNT
                sopno = draft[7]  # SOPNO
                
                # 按 sopno 分組
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
            
            # 檢查是否為重新提交（tdr_master 已存在）
            check_master_sql = text("""
                SELECT COUNT(*) FROM jps.tdr_master 
                WHERE daily_no = :daily_no
            """)
            master_exists = db.execute(check_master_sql, {"daily_no": daily_no}).scalar() > 0
            
            if master_exists:
                logger.info(f"重新提交日報 {daily_no}，保留 master 資料，重建 detail 資料")
                
                # 刪除現有的 detail1、detail2 和檔案記錄
                delete_detail1_sql = text("DELETE FROM jps.tdr_detail1 WHERE daily_no = :daily_no")
                delete_detail2_sql = text("DELETE FROM jps.tdr_detail2 WHERE daily_no = :daily_no")
                # 根據 daily_no 的檔案ID模式刪除檔案
                daily_no_prefix = int(daily_no) * 1000000
                delete_files_sql = text("""
                    DELETE FROM jps.tdr_upload_file 
                    WHERE id >= :daily_no_start AND id < :daily_no_end
                """)
                
                logger.info(f"開始刪除舊記錄：daily_no={daily_no}, empno={empno}")
                
                detail1_deleted = db.execute(delete_detail1_sql, {"daily_no": daily_no}).rowcount
                detail2_deleted = db.execute(delete_detail2_sql, {"daily_no": daily_no}).rowcount
                files_deleted = db.execute(delete_files_sql, {
                    "daily_no_start": daily_no_prefix,
                    "daily_no_end": daily_no_prefix + 1000000
                }).rowcount
                
                logger.info(f"服務層刪除結果：detail1={detail1_deleted}筆, detail2={detail2_deleted}筆, files={files_deleted}筆")
                
                # 更新 master 資料的一些欄位（如字數、時間等）
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
            else:
                logger.info(f"首次提交日報 {daily_no}，創建新的 master 資料")
                
                # 插入新的 tdr_master
                master_sql = text("""
                    INSERT INTO tdr_master (
                        DAILY_NO, COCODE, EMPNO, DEPTNO, DOC_DATE, EMERGENCY, CLASSIFY, SCORE,
                        XUSER, XDATE, XTIME, STATUS, LEADER, G_DEPTNO, EMPNAMEC, DEPTNAMEC,
                        UPLOAD_SITE, EMPNAMEC_N, WFINBOX_STATUS, SOP_DESC_C, CUST_ENAME1, CUST_COMP_ABBV1,
                        WORD_COUNT, ATT_FILE1, ATT_FILE2, openpath, openwebpage
                    ) VALUES (
                        :daily_no, :cocode, :empno, :deptno, :doc_date, NULL, NULL, 0,
                        :empno, :current_date, :current_time, 'N', :leader, :g_deptno, :empnamec, :deptnamec,
                        'D', :empnamec, 'N', :sop_desc_c, NULL, NULL,
                        :word_count, :att_file1, :att_file2, '/MyReport/', 'viewed.aspx'
                    )
                """)
            
            # 從 tpm_sop 重新取得正確的 SOP_DESC_C（忽略暫存中的錯誤資料）
            main_sop_desc_c = ''
            first_sopno = draft_results[0][7] if len(draft_results) > 0 and draft_results[0][7] else None  # SOPNO
            if first_sopno:
                try:
                    sop_sql = text("SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno")
                    sop_result = db.execute(sop_sql, {"sopno": first_sopno}).fetchone()
                    if sop_result and sop_result[0]:
                        main_sop_desc_c = sop_result[0]
                        # 限制長度為50字元
                        if len(main_sop_desc_c) > 50:
                            main_sop_desc_c = main_sop_desc_c[:47] + '...'
                except Exception as e:
                    logger.warning(f"無法取得 sopno {first_sopno} 的正確執行工作描述: {str(e)}")
                    # 如果無法取得正確描述，使用暫存中的資料並截斷
                    main_sop_desc_c = draft_results[0][8] if draft_results[0][8] else ''
                    if len(main_sop_desc_c) > 50:
                        main_sop_desc_c = main_sop_desc_c[:47] + '...'
            
            # 執行對應的 SQL（INSERT 或 UPDATE）
            master_params = {
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
            }
            
            if master_exists:
                # 執行更新
                db.execute(update_master_sql, master_params)
            else:
                # 執行插入
                db.execute(master_sql, master_params)
            
            # 為每個sopno組創建detail1和detail2記錄
            daily_sub_nos = 1
            sopno_to_daily_sub_nos = {}  # 記錄 sopno 對應的 daily_sub_nos
            
            for sopno, group_data in sopno_groups.items():
                drafts_in_group = group_data['drafts']
                group_files = group_data['files']
                
                # 記錄對應關係
                sopno_to_daily_sub_nos[sopno] = daily_sub_nos
                
                logger.info(f"服務層處理 sopno={sopno}, daily_sub_nos={daily_sub_nos}, 檔案數量={len(group_files)}")
                # 插入 tdr_detail1（每個sopno組一次）
                detail1_sql = text("""
                    INSERT INTO tdr_detail1 (
                        DAILY_NO, DAILY_SUB_NOS, XUSER, XDATE, XTIME, CUNO1, COMP_SERNO1
                    ) VALUES (
                        :daily_no, :daily_sub_nos, :empno, :current_date, :current_time, NULL, NULL
                    )
                """)
                
                db.execute(detail1_sql, {
                    "daily_no": daily_no,
                    "daily_sub_nos": daily_sub_nos,
                    "empno": empno,
                    "current_date": current_date,
                    "current_time": current_time
                })
                
                # 插入 tdr_detail2（該sopno組內的每個記錄）
                daily_job_nos = 1
                for draft in drafts_in_group:
                    detail2_sql = text("""
                        INSERT INTO tdr_detail2 (
                            DAILY_NO, DAILY_SUB_NOS, DAILY_JOB_NOS, COCODE, EMPNO, SOP_CODE, STATUS,
                            XUSER, XDATE, XTIME, ITEMDESC1, PROD_CATE, EXETIME, ESTIMATE, ATTITUDE,
                            PROD_NO, SOLUT_SUBJ, SOLUT_STATUS, EMPNAME1, EMPNAME2, EMPNAME3, EMPNAME4, EMPNAME5,
                            PPS_SERVECOCODE, PPS_EMPNO, PPS_COCODE, PPS_DEPTNO, MEMO_COLLECT, MEMO,
                            PPS_EMPNAMEC, PLANNO, SOPNO
                        ) VALUES (
                            :daily_no, :daily_sub_nos, :daily_job_nos, :cocode, :empno, :work_item_seq, 'N',
                            :empnamec, :current_date, :current_time, :content, NULL, :execution_time_minutes, NULL, NULL,
                            NULL, NULL, NULL, '0', NULL, NULL, NULL, NULL,
                            :service_cocode, :service_empno, :service_cocode, :service_deptno, '1', :content,
                            :service_empnamec, :planno, :sopno
                        )
                    """)
                    
                    db.execute(detail2_sql, {
                        "daily_no": daily_no,
                        "daily_sub_nos": daily_sub_nos,
                        "daily_job_nos": daily_job_nos,
                        "cocode": cocode,
                        "empno": empno,
                        "work_item_seq": draft[9],  # WORK_ITEM_SEQ
                        "empnamec": empnamec,
                        "content": draft[14],  # CONTENT
                        "execution_time_minutes": draft[15],  # EXECUTION_TIME_MINUTES
                        "service_cocode": draft[10],  # SERVICE_COCODE
                        "service_empno": draft[11],   # SERVICE_EMPNO
                        "service_deptno": draft[13],  # SERVICE_DEPTNO
                        "service_empnamec": draft[12], # SERVICE_EMPNAMEC
                        "planno": draft[5],  # PLANNO (should be numeric from tdr_draft.PLANNO)
                        "sopno": draft[7],   # SOPNO (should be numeric from tdr_draft.SOPNO)
                        "current_date": current_date,
                        "current_time": current_time
                    })
                    
                    daily_job_nos += 1
                
                daily_sub_nos += 1
            
            # 更新所有暫存狀態為已提交
            update_draft_sql = text("""
                UPDATE jps.tdr_draft SET STATUS = 'S' WHERE DAILY_NO = :daily_no
            """)
            db.execute(update_draft_sql, {"daily_no": daily_no})
            
            # 為每個 sopno 組處理其對應的檔案
            total_files_processed = 0
            for sopno, group_data in sopno_groups.items():
                group_files = group_data['files']
                corresponding_daily_sub_nos = sopno_to_daily_sub_nos[sopno]
                
                if group_files:
                    logger.info(f"服務層處理 sopno={sopno} (daily_sub_nos={corresponding_daily_sub_nos}) 的 {len(group_files)} 個檔案")
                    for i, f in enumerate(group_files):
                        logger.info(f"  檔案{i}: {f}")
                    
                    LegacyReportServiceV2.process_files_for_specific_daily_sub_nos(
                        db=db,
                        daily_no=daily_no,
                        daily_sub_nos=corresponding_daily_sub_nos,
                        empno=empno,
                        cocode=original_cocode,
                        doc_date=doc_date,
                        files=group_files
                    )
                    total_files_processed += len(group_files)
                    logger.info(f"服務層 sopno={sopno} 檔案處理完成")
                else:
                    logger.info(f"服務層 sopno={sopno} (daily_sub_nos={corresponding_daily_sub_nos}) 沒有檔案")
            
            logger.info(f"服務層檔案處理完成，總共處理 {total_files_processed} 個檔案")
            db.commit()
            logger.info(f"Successfully submitted draft {daily_no} to final with {len(draft_results)} work items")
            return daily_no
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error submitting draft to final: {str(e)}")
            raise
    
    @staticmethod
    def get_reports_by_date(db: Session, doc_date: str, supervisor_empno: str, cocode: str) -> List[Dict[str, Any]]:
        """根據日期查詢已提交的日報 (主管查看下屬的日報)"""
        try:
            sql = text("""
                SELECT m.DAILY_NO, m.EMPNO, m.EMPNAMEC, m.DEPTNO, m.DEPTNAMEC,
                       m.DOC_DATE, m.STATUS, m.SOP_DESC_C, m.WORD_COUNT,
                       m.ATT_FILE1, m.ATT_FILE2, m.XDATE, m.XTIME
                FROM tdr_master m
                WHERE m.DOC_DATE = :doc_date
                AND m.COCODE = :cocode
                AND m.STATUS = 'N'
                ORDER BY m.XDATE DESC, m.XTIME DESC
            """)
            
            result = db.execute(sql, {
                "doc_date": doc_date,
                "cocode": cocode
            })
            
            reports = []
            for row in result:
                reports.append({
                    "daily_no": row[0],
                    "empno": row[1],
                    "empnamec": row[2],
                    "deptno": row[3],
                    "deptnamec": row[4],
                    "doc_date": row[5],
                    "status": row[6],
                    "sop_desc_c": row[7],
                    "word_count": row[8],
                    "att_file1": row[9],
                    "att_file2": row[10],
                    "xdate": row[11],
                    "xtime": row[12]
                })
            
            return reports
            
        except Exception as e:
            logger.error(f"Error getting reports by date: {str(e)}")
            return []
    
    @staticmethod
    def get_report_details_by_daily_no(db: Session, daily_no: str) -> Dict[str, Any]:
        """根據日報編號取得日報詳細內容"""
        try:
            # 取得主檔資料
            master_sql = text("""
                SELECT DAILY_NO, EMPNO, EMPNAMEC, DEPTNO, DEPTNAMEC, DOC_DATE,
                       STATUS, SOP_DESC_C, WORD_COUNT, ATT_FILE1, ATT_FILE2,
                       XDATE, XTIME, COCODE
                FROM tdr_master
                WHERE DAILY_NO = :daily_no
            """)
            
            master_result = db.execute(master_sql, {"daily_no": daily_no}).fetchone()
            if not master_result:
                return {}
            
            # 取得詳細資料
            detail_sql = text("""
                SELECT d1.DAILY_SUB_NOS, d2.SOP_CODE, d2.MEMO, d2.EXETIME,
                       d2.PLANNO, d2.SOPNO, d2.PPS_SERVECOCODE, d2.PPS_EMPNO,
                       d2.PPS_EMPNAMEC, d2.PPS_DEPTNO, d2.ITEMDESC1
                FROM tdr_detail1 d1
                JOIN tdr_detail2 d2 ON d1.DAILY_NO = d2.DAILY_NO AND d1.DAILY_SUB_NOS = d2.DAILY_SUB_NOS
                WHERE d1.DAILY_NO = :daily_no
                ORDER BY d1.DAILY_SUB_NOS
            """)
            
            detail_results = db.execute(detail_sql, {"daily_no": daily_no})
            
            details = []
            for row in detail_results:
                details.append({
                    "daily_sub_nos": row[0],
                    "sop_code": row[1],
                    "memo": row[2],
                    "exetime": row[3],
                    "planno": row[4],
                    "sopno": row[5],
                    "service_cocode": row[6],
                    "service_empno": row[7],
                    "service_empnamec": row[8],
                    "service_deptno": row[9],
                    "itemdesc1": row[10]
                })
            
            return {
                "master": {
                    "daily_no": master_result[0],
                    "empno": master_result[1],
                    "empnamec": master_result[2],
                    "deptno": master_result[3],
                    "deptnamec": master_result[4],
                    "doc_date": master_result[5],
                    "status": master_result[6],
                    "sop_desc_c": master_result[7],
                    "word_count": master_result[8],
                    "att_file1": master_result[9],
                    "att_file2": master_result[10],
                    "xdate": master_result[11],
                    "xtime": master_result[12],
                    "cocode": master_result[13]
                },
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Error getting report details: {str(e)}")
            return {}
    
    @staticmethod
    def get_daily_reports_by_supervisor(
        db: Session, 
        empno: str, 
        doc_date: str, 
        cocode: str = None, 
        deptno: str = None
    ) -> List[Dict[str, Any]]:
        """取得日報列表 BY 工號（主管） - 從 tdr_master 查詢"""
        try:
            # 簡化版本的查詢，先實現基本功能
            sql = text("""
                SELECT
                    a.daily_no,
                    a.cocode,
                    a.empno,
                    a.empnamec,
                    a.emergency,
                    a.classify,
                    a.att_file1,
                    a.att_file2,
                    a.sop_desc_c,
                    a.doc_date,
                    a.openpath,
                    a.openwebpage,
                    d.g_deptno,
                    d.deptnamec
                FROM tdr_master a
                LEFT JOIN jps.dcd003$master e
                    ON a.cocode = e.cocode
                   AND a.empno = e.empno
                LEFT JOIN jps.dcd002$master d
                    ON e.cocode = d.cocode
                   AND e.deptno = d.deptno
                WHERE
                    a.status = 'N'
                    AND a.doc_date = :doc_date
                    AND (e.QUITDATE IS NULL OR e.QUITDATE >= a.DOC_DATE)
                    AND a.empno <> '01188'
                ORDER BY a.daily_no
            """)
            
            params = {
                "doc_date": doc_date
            }
            
            result = db.execute(sql, params)
            columns = result.keys()
            reports = []
            
            for row in result.fetchall():
                report_dict = dict(zip(columns, row))
                reports.append(report_dict)
            
            logger.info(f"Found {len(reports)} daily reports for supervisor {empno}")
            return reports
            
        except Exception as e:
            logger.error(f"Error getting daily reports by supervisor: {str(e)}")
            return []
    
    @staticmethod
    def get_daily_report_content(
        db: Session, 
        daily_no: str
    ) -> Dict[str, Any]:
        """取得日報內容 - 從 tdr_master, tdr_detail1, tdr_detail2 查詢"""
        try:
            # 使用您提供的正確 SQL 查詢
            sql = text("""
                SELECT a.cuno1,
                       b.daily_sub_nos,
                       b.sopno,
                       b.sop_code,
                       b.prod_cate,
                       b.itemdesc1,
                       b.exetime,
                       b.estimate,
                       b.attitude,
                       b.memo_collect,
                       b.cuno_subj,
                       b.cuno_msg,
                       b.cuno_collect,
                       b.comp_inf,
                       b.comp_desc,
                       b.comp_collect,
                       b.ques_subj,
                       b.ques_desc,
                       b.solut_subj,
                       b.solut_desc,
                       b.solut_status,
                       b.att_file3,
                       b.xuser,
                       b.xdate,
                       b.xtime,
                       b.empname1,
                       b.empname2,
                       b.empname3,
                       b.prod_no,
                       b.create_msg,
                       b.comp_serno,
                       b.cuno_comp_serno,
                       b.cocode,
                       b.empno,
                       b.status,
                       b.planno,
                       b.memo,
                       b.empname4,
                       b.empname5,
                       b.cuno_infcont,
                       b.comp_infcont,
                       b.ques_infcont,
                       b.solut_infcont,
                       b.finish_rate,
                       b.pps_cocode,
                       b.pps_empno,
                       b.pps_deptno,
                       b.pps_empnamec,
                       b.ship_log,
                       b.cuno_msg1,
                       b.ques_desc1,
                       b.solut_desc1,
                       b.memo1,
                       b.cuno_msg2,
                       b.ques_desc2,
                       b.solut_desc2,
                       b.memo2,
                       b.reply,
                       b.pps_servecocode,
                       b.projno,
                       b.proj_cocode,
                       b.memo_collect
                FROM tdr_detail1 a
                JOIN tdr_detail2 b ON b.daily_no = a.daily_no
                AND b.daily_sub_nos = a.daily_sub_nos
                WHERE a.daily_no = :daily_no
                ORDER BY a.daily_sub_nos, b.daily_job_nos
            """)
            
            result = db.execute(sql, {"daily_no": daily_no})
            columns = result.keys()
            content = []
            
            for row in result.fetchall():
                content_dict = dict(zip(columns, row))
                content.append(content_dict)
            
            logger.info(f"Found {len(content)} detail records for daily_no {daily_no}")
            return {"details": content}
            
        except Exception as e:
            logger.error(f"Error getting daily report content: {str(e)}")
            return {"details": []}
    
    @staticmethod
    def get_work_plans(
        db: Session, 
        empno: str, 
        cocode: str = None
    ) -> List[Dict[str, Any]]:
        """取得工作計畫（只返回大類，不包含工作項目詳細資料）"""
        sql = text("""
            SELECT DISTINCT A.planno, A.plan_subj_c
            FROM jps.tjp_master A
            WHERE (A.empno = :empno or A.pm_empno = :empno)
            and (A.plan_date2 is null or A.plan_date2 >= TO_CHAR(CURRENT_DATE,'YYYYMMDD'))
            ORDER BY A.planno DESC
        """)

        try:
            result = db.execute(sql, {"empno": empno})

            # 將結果轉換為字典列表
            columns = result.keys()
            plans = []
            
            # 添加預設的"請選擇工作計畫"選項
            plans.append({
                'empno': empno,
                'planno': '',  # 空字串表示未選擇
                'plan_subj_c': '請選擇工作計畫'
            })
            
            for row in result.fetchall():
                plan_dict = dict(zip(columns, row))
                # 確保返回的格式與前端期望一致
                plan_dict['empno'] = empno
                plan_dict['planno'] = plan_dict['planno']
                plan_dict['plan_subj_c'] = plan_dict['plan_subj_c'] or f"工作計畫 {plan_dict['planno']}"
                plans.append(plan_dict)

            logger.info(f"Found {len(plans)-1} work plans for empno={empno} (plus default option)")
            return plans

        except Exception as e:
            logger.error(f"Error fetching work plans: {str(e)}")
            raise
    
    
    @staticmethod
    def save_attachment(
        db: Session,
        draft_record_id: str,
        file_name: str,
        file_path: str,
        file_size: int,
        file_type: str,
        is_selected_for_ai: bool = False
    ) -> str:
        """保存附件到 tdr_draft_attachment 表"""
        try:
            from sqlalchemy import text
            from datetime import datetime
            
            # 生成附件ID
            att_id = str(uuid.uuid4())
            
            # 取得daily_no (從draft_record_id中取得)
            daily_no = draft_record_id
            
            # 插入附件記錄
            insert_sql = text("""
                INSERT INTO jps.tdr_draft_attachment(
                    att_id, draft_record_id, daily_no, file_name, file_path, 
                    file_size, file_type, is_selected_for_ai, upload_date, 
                    upload_time, status
                ) VALUES (
                    :att_id, :draft_record_id, :daily_no, :file_name, :file_path,
                    :file_size, :file_type, :is_selected_for_ai, :upload_date,
                    :upload_time, :status
                )
            """)
            
            now = datetime.now()
            db.execute(insert_sql, {
                "att_id": att_id,
                "draft_record_id": draft_record_id,
                "daily_no": daily_no,
                "file_name": file_name,
                "file_path": file_path,
                "file_size": file_size,
                "file_type": file_type,
                "is_selected_for_ai": is_selected_for_ai,
                "upload_date": now.strftime('%Y%m%d'),
                "upload_time": now.strftime('%H%M%S'),
                "status": 'A'
            })
            
            db.commit()
            logger.info(f"附件保存成功: att_id={att_id}, file_name={file_name}")
            return att_id
            
        except Exception as e:
            logger.error(f"Error saving attachment: {str(e)}")
            db.rollback()
            raise
    
    @staticmethod
    def process_files_for_formal_report(
        db: Session,
        daily_no: str,
        empno: str,
        cocode: str,
        doc_date: str,
        all_files: List[Dict[str, Any]]
    ) -> None:
        """處理檔案上傳到正式版報告系統 (tdr_upload_file表)"""
        try:
            logger.info(f"開始處理檔案上傳：daily_no={daily_no}, empno={empno}, all_files={all_files}")
            
            if not all_files:
                logger.info("沒有檔案需要處理")
                return
            
            # 取得所有的 daily_sub_nos
            detail_sql = text("""
                SELECT DISTINCT daily_sub_nos 
                FROM jps.tdr_detail2 
                WHERE daily_no = :daily_no 
                ORDER BY daily_sub_nos
            """)
            detail_results = db.execute(detail_sql, {"daily_no": daily_no}).fetchall()
            logger.info(f"找到的 daily_sub_nos: {[row[0] for row in detail_results]}")
            
            if not detail_results:
                logger.warning(f"找不到 daily_no {daily_no} 的詳細記錄")
                return
            
            # 處理檔案 - 正確邏輯：為每個 daily_sub_nos 都創建檔案記錄
            logger.info(f"為所有 daily_sub_nos 創建檔案記錄: {[row[0] for row in detail_results]}")
            
            for file_info in all_files:
                file_name = file_info.get('name', '')
                if not file_name:
                    continue
                
                # 為每個 daily_sub_nos 都建立檔案記錄，每個都使用 file_index=1
                for detail_row in detail_results:
                    daily_sub_no = detail_row[0]
                    file_index = 1  # 每個 daily_sub_nos 的檔案索引都從1開始
                    
                    # 生成檔案ID: dailyNo * 1000000 + dailySubNo * 1000 + 1
                    file_id = int(daily_no) * 1000000 + daily_sub_no * 1000 + file_index
                
                # 生成檔名編碼
                now = datetime.now()
                # 格式: empNo + "_" + ddHHmmssfffffff (其中fffffff是7位毫秒)
                microseconds = now.microsecond
                milliseconds_7digit = f"{microseconds}0"[:7]  # 將6位微秒擴展為7位
                hash_input = f"{empno}_{now.strftime('%d%H%M%S')}{milliseconds_7digit}"
                hash_md5 = hashlib.md5(hash_input.encode()).hexdigest()
                
                logger.info(f"檔名編碼輸入: {hash_input} -> MD5: {hash_md5}")
                
                # 取得原始檔案副檔名
                original_ext = ""
                if '.' in file_name:
                    original_ext = file_name[file_name.rfind('.'):]
                
                encoded_filename = f"{hash_md5}{original_ext}"
                
                # 生成檔案路徑: yyyyMM(依日報日期取年月) + / + 檔名編碼
                year_month = doc_date[:6]  # 取日報日期的 yyyyMM
                file_path = f"{year_month}/{encoded_filename}"
                
                # 插入 tdr_upload_file 記錄的時間資訊
                current_date = now.strftime('%Y%m%d')  # xdate: 當前日期 yyyyMMdd
                current_time = now.strftime('%H:%M:%S')  # xtime: 當前時間 HH:mm:ss
                
                logger.info(f"檔案路徑: {file_path}, docdate: {doc_date}, xdate: {current_date}, xtime: {current_time}")
                
                # 檢查是否已存在相同ID的記錄
                check_sql = text("SELECT COUNT(*) FROM jps.tdr_upload_file WHERE id = :id")
                exists = db.execute(check_sql, {"id": file_id}).scalar() > 0
                
                if exists:
                    logger.info(f"檔案記錄 {file_id} 已存在，跳過插入")
                    file_index += 1
                    continue
                
                insert_sql = text("""
                    INSERT INTO jps.tdr_upload_file (
                        id, cocode, empno, docdate, filepath, filename, status, xdate, xtime
                    ) VALUES (
                        :id, :cocode, :empno, :docdate, :filepath, :filename, :status, :xdate, :xtime
                    )
                """)
                
                try:
                    db.execute(insert_sql, {
                        "id": file_id,                    # id = dailyNo * 1000000 + dailySubNos * 1000 + index
                        "cocode": cocode,                # coCode
                        "empno": empno,                  # empNo
                        "docdate": doc_date,             # docDate(yyyyMMdd) - 日報日期
                        "filepath": file_path,           # filePath = yyyyMM/ + 檔名編碼
                        "filename": file_name,           # {原始檔名}
                        "status": "Online",              # 'Online'
                        "xdate": current_date,           # yyyyMMdd - 當前日期
                        "xtime": current_time            # HH:mm:ss - 當前時間
                    })
                    
                    logger.info(f"檔案記錄插入成功:")
                    logger.info(f"   ID: {file_id} (daily_no={daily_no}, daily_sub_nos={daily_sub_no}, index={file_index})")
                    logger.info(f"   檔案: {file_name} -> {file_path}")
                    logger.info(f"   日期: docdate={doc_date}, xdate={current_date}, xtime={current_time}")
                except Exception as insert_error:
                    logger.error(f"插入檔案記錄失敗: id={file_id}, error={str(insert_error)}")
                    raise
                
                file_index += 1
            
            logger.info(f"成功處理 {len(all_files)} 個檔案到正式版報告系統")
            
        except Exception as e:
            logger.error(f"處理正式版檔案上傳失敗: {str(e)}")
            raise
    
    @staticmethod
    def process_files_for_specific_daily_sub_nos(
        db: Session,
        daily_no: str,
        daily_sub_nos: int,
        empno: str,
        cocode: str,
        doc_date: str,
        files: List[Dict[str, Any]]
    ) -> None:
        """為特定 daily_sub_nos 處理檔案上傳 (修復版本)"""
        try:
            logger.info(f"為 daily_sub_nos={daily_sub_nos} 處理檔案：daily_no={daily_no}, 檔案數量={len(files)}")
            
            if not files:
                logger.info(f"daily_sub_nos={daily_sub_nos} 沒有檔案需要處理")
                return
            
            # 處理每個檔案
            file_index = 1
            for file_info in files:
                file_name = file_info.get('name', '')
                if not file_name:
                    continue
                
                # 生成檔案ID: dailyNo * 1000000 + dailySubNos * 1000 + index
                file_id = int(daily_no) * 1000000 + daily_sub_nos * 1000 + file_index
                
                # 生成檔名編碼
                now = datetime.now()
                # 格式: empNo + "_" + ddHHmmssfffffff (其中fffffff是7位毫秒)
                microseconds = now.microsecond
                milliseconds_7digit = f"{microseconds}0"[:7]  # 將6位微秒擴展為7位
                hash_input = f"{empno}_{now.strftime('%d%H%M%S')}{milliseconds_7digit}"
                hash_md5 = hashlib.md5(hash_input.encode()).hexdigest()
                
                logger.info(f"檔名編碼輸入: {hash_input} -> MD5: {hash_md5}")
                
                # 取得原始檔案副檔名
                original_ext = ""
                if '.' in file_name:
                    original_ext = file_name[file_name.rfind('.'):]
                
                encoded_filename = f"{hash_md5}{original_ext}"
                
                # 生成檔案路徑: yyyyMM(依日報日期取年月) + / + 檔名編碼
                year_month = doc_date[:6]  # 取日報日期的 yyyyMM
                file_path = f"{year_month}/{encoded_filename}"
                
                # 插入 tdr_upload_file 記錄的時間資訊
                current_date = now.strftime('%Y%m%d')  # xdate: 當前日期 yyyyMMdd
                current_time = now.strftime('%H:%M:%S')  # xtime: 當前時間 HH:mm:ss
                
                logger.info(f"檔案路徑: {file_path}, docdate: {doc_date}, xdate: {current_date}, xtime: {current_time}")
                
                # 檢查是否已存在相同ID的記錄
                check_sql = text("SELECT COUNT(*) FROM jps.tdr_upload_file WHERE id = :id")
                exists = db.execute(check_sql, {"id": file_id}).scalar() > 0
                
                if exists:
                    logger.info(f"檔案記錄 {file_id} 已存在，跳過插入")
                    file_index += 1
                    continue
                
                insert_sql = text("""
                    INSERT INTO jps.tdr_upload_file (
                        id, cocode, empno, docdate, filepath, filename, status, xdate, xtime
                    ) VALUES (
                        :id, :cocode, :empno, :docdate, :filepath, :filename, :status, :xdate, :xtime
                    )
                """)
                
                try:
                    db.execute(insert_sql, {
                        "id": file_id,                    # id = dailyNo * 1000000 + dailySubNos * 1000 + index
                        "cocode": cocode,                # coCode
                        "empno": empno,                  # empNo
                        "docdate": doc_date,             # docDate(yyyyMMdd) - 日報日期
                        "filepath": file_path,           # filePath = yyyyMM/ + 檔名編碼
                        "filename": file_name,           # {原始檔名}
                        "status": "Online",              # 'Online'
                        "xdate": current_date,           # yyyyMMdd - 當前日期
                        "xtime": current_time            # HH:mm:ss - 當前時間
                    })
                    
                    logger.info(f"檔案記錄插入成功:")
                    logger.info(f"   ID: {file_id} (daily_no={daily_no}, daily_sub_nos={daily_sub_nos}, index={file_index})")
                    logger.info(f"   檔案: {file_name} -> {file_path}")
                    logger.info(f"   日期: docdate={doc_date}, xdate={current_date}, xtime={current_time}")
                except Exception as insert_error:
                    logger.error(f"插入檔案記錄失敗: id={file_id}, error={str(insert_error)}")
                    raise
                
                file_index += 1
            
            logger.info(f"成功為 daily_sub_nos={daily_sub_nos} 處理 {len(files)} 個檔案")
            
        except Exception as e:
            logger.error(f"為 daily_sub_nos={daily_sub_nos} 處理檔案失敗: {str(e)}")
            raise
    
# submit_report 方法已移除，請使用新的上傳邏輯
