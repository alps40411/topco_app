# backend/app/services/draft_service.py

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DraftService:
    """專門處理所有與 tdr_draft 資料表相關的服務"""
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
                
                # 檔案處理：使用前端傳來的完整檔案列表（已處理刪除）
                # 直接替換，而非合併，以支援檔案刪除同步
                merged_files = files_json  # 使用前端傳來的檔案列表（已反映刪除操作）
                merged_att_file1 = att_file1  # 使用前端傳來的檔案名稱列表
                merged_att_file2 = att_file2  # 使用前端傳來的檔案路徑列表

                logger.info(f"檔案列表更新（替換模式）: {len(files)} 個檔案")
                
                # 更新現有記錄
                update_sql = text("""
                    UPDATE jps.tdr_draft
                    SET PLAN_SUBJ_C = :plan_subj_c,
                        SOP_DESC_C = :sop_desc_c,
                        WORK_ITEM_SEQ = :work_item_seq,
                        SERVICE_COCODE = COALESCE(:service_cocode, SERVICE_COCODE),
                        SERVICE_EMPNO = COALESCE(:service_empno, SERVICE_EMPNO),
                        SERVICE_EMPNAMEC = COALESCE(:service_empnamec, SERVICE_EMPNAMEC),
                        SERVICE_TARGET_COCODE = COALESCE(:service_target_cocode, SERVICE_TARGET_COCODE),
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
                    "service_target_cocode": draft_content.get('service_target_cocode'),
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
                        SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC, SERVICE_TARGET_COCODE, SERVICE_DEPTNO,
                        CONTENT, EXECUTION_TIME_MINUTES, WORD_COUNT,
                        ATT_FILE1, ATT_FILE2, FILES,
                        STATUS, CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME
                    ) VALUES (
                        :daily_no, :empno, :cocode, :doc_date, :draft_type,
                        :planno, :plan_subj_c, :sopno, :sop_desc_c, :work_item_seq,
                        :service_cocode, :service_empno, :service_empnamec, :service_target_cocode, :service_deptno,
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
                    "service_target_cocode": draft_content.get('service_target_cocode'),
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

    def get_drafts(db: Session, empno: str, doc_date: str, draft_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """取得員工的暫存資料"""
        try:
            logger.info(f"取得員工 {empno} 在 {doc_date} 的暫存資料")
            
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
                files = []
                if row[19]:
                    try:
                        files = json.loads(row[19])
                    except:
                        files = []
                
                draft = {
                    "daily_no": row[0], "empno": row[1], "cocode": row[2],
                    "doc_date": row[3], "draft_type": row[4], "planno": row[5],
                    "plan_subj_c": row[6], "sopno": row[7], "sop_desc_c": row[8],
                    "work_item_seq": row[9], "service_cocode": row[10],
                    "service_empno": row[11], "service_empnamec": row[12],
                    "service_deptno": row[13], "content": row[14],
                    "execution_time_minutes": row[15], "word_count": row[16],
                    "att_file1": row[17], "att_file2": row[18], "files": files,
                    "created_date": row[20], "created_time": row[21],
                    "updated_date": row[22], "updated_time": row[23]
                }
                drafts.append(draft)
            
            logger.info(f"找到 {len(drafts)} 筆暫存記錄")
            return drafts
        except Exception as e:
            logger.error(f"Error getting drafts from service: {str(e)}")
            raise

    @staticmethod
    def update_draft(db: Session, daily_no: str, planno: str, sopno: str, update_data: Dict[str, Any]) -> None:
        """根據 daily_no、planno 和 sopno 更新特定的暫存記錄"""
        try:
            if planno == "NULL":
                planno = ""

            check_sql = text("""
                SELECT RECORD_ID FROM jps.tdr_draft
                WHERE DAILY_NO = :daily_no AND COALESCE(PLANNO, '') = COALESCE(:planno, '') AND SOPNO = :sopno
            """)
            existing_record = db.execute(check_sql, {"daily_no": daily_no, "planno": planno, "sopno": sopno}).fetchone()

            if not existing_record:
                raise ValueError("找不到指定的暫存記錄")

            content = update_data.get('content', '')
            files = update_data.get('files', [])
            new_planno = update_data.get('planno', '')
            new_sopno = update_data.get('sopno', '')
            work_item_ids = update_data.get('work_item_ids', [])
            service_cocode = update_data.get('service_cocode', '')
            service_empno = update_data.get('service_empno', '')
            service_empnamec = update_data.get('service_empnamec', '')
            service_target_cocode = update_data.get('service_target_cocode', '')
            service_deptno = update_data.get('service_deptno', '')
            execution_time_minutes = update_data.get('execution_time_minutes', 0)

            att_file1_list = [f.get('name', '') for f in files if isinstance(f, dict) and f.get('name')]
            att_file2_list = [f.get('url', '') for f in files if isinstance(f, dict) and f.get('url')]
            files_json = json.dumps(files, ensure_ascii=False) if files else "[]"
            att_file1 = ','.join(att_file1_list)
            att_file2 = ','.join(att_file2_list)
            word_count = len(content)
            work_item_seq = '/'.join(map(str, work_item_ids))

            plan_subj_c = ""
            if new_planno:
                plan_sql = text("SELECT plan_subj_c FROM jps.tjp_master WHERE planno = :planno")
                plan_result = db.execute(plan_sql, {"planno": new_planno}).fetchone()
                if plan_result: plan_subj_c = plan_result[0]

            sop_desc_c = ""
            if new_sopno:
                sop_sql = text("SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno")
                sop_result = db.execute(sop_sql, {"sopno": new_sopno}).fetchone()
                if sop_result: sop_desc_c = sop_result[0]

            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')

            update_sql = text("""
                UPDATE jps.tdr_draft
                SET CONTENT = :content, WORD_COUNT = :word_count, ATT_FILE1 = :att_file1,
                    ATT_FILE2 = :att_file2, FILES = :files, PLANNO = :new_planno,
                    PLAN_SUBJ_C = :plan_subj_c, SOPNO = :new_sopno, SOP_DESC_C = :sop_desc_c,
                    WORK_ITEM_SEQ = :work_item_seq, SERVICE_COCODE = :service_cocode,
                    SERVICE_EMPNO = :service_empno, SERVICE_EMPNAMEC = :service_empnamec,
                    SERVICE_TARGET_COCODE = :service_target_cocode, SERVICE_DEPTNO = :service_deptno,
                    EXECUTION_TIME_MINUTES = :execution_time_minutes,
                    UPDATED_DATE = :updated_date, UPDATED_TIME = :updated_time
                WHERE DAILY_NO = :daily_no AND COALESCE(PLANNO, '') = COALESCE(:planno, '') AND SOPNO = :sopno
            """)
            db.execute(update_sql, {
                "content": content, "word_count": word_count, "att_file1": att_file1,
                "att_file2": att_file2, "files": files_json, "new_planno": new_planno,
                "plan_subj_c": plan_subj_c, "new_sopno": new_sopno, "sop_desc_c": sop_desc_c,
                "work_item_seq": work_item_seq, "service_cocode": service_cocode,
                "service_empno": service_empno, "service_empnamec": service_empnamec,
                "service_target_cocode": service_target_cocode, "service_deptno": service_deptno,
                "execution_time_minutes": execution_time_minutes,
                "updated_date": current_date, "updated_time": current_time,
                "daily_no": daily_no, "planno": planno, "sopno": sopno
            })
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating draft in service: {str(e)}")
            raise

    @staticmethod
    def delete_draft_record(db: Session, daily_no: str, planno: str, sopno: str) -> None:
        """刪除指定的單筆草稿記錄及其相關檔案"""
        import os
        from pathlib import Path

        try:
            if planno == "NULL":
                planno = ""

            # 1. 先查詢該記錄的檔案資訊
            query_sql = text("""
                SELECT FILES FROM jps.tdr_draft
                WHERE DAILY_NO = :daily_no
                AND COALESCE(PLANNO, '') = COALESCE(:planno, '')
                AND SOPNO = :sopno
            """)

            result = db.execute(query_sql, {
                "daily_no": daily_no,
                "planno": planno,
                "sopno": sopno
            }).fetchone()

            if not result:
                raise ValueError(f"找不到指定的草稿記錄 (daily_no: {daily_no}, planno: {planno}, sopno: {sopno})")

            # 2. 收集需要刪除的檔案路徑
            files_to_delete = []
            if result[0]:
                try:
                    files = json.loads(result[0])
                    for file_info in files:
                        if isinstance(file_info, dict):
                            file_url = file_info.get('url', '')
                            if file_url:
                                # 從 URL 提取檔案路徑 (假設 URL 格式為 /uploads/xxx)
                                if file_url.startswith('/uploads/'):
                                    file_path = file_url.replace('/uploads/', '')
                                    files_to_delete.append(file_path)
                except:
                    logger.warning(f"無法解析檔案 JSON: {result[0]}")

            # 3. 刪除資料庫記錄
            delete_sql = text("""
                DELETE FROM jps.tdr_draft
                WHERE DAILY_NO = :daily_no
                AND COALESCE(PLANNO, '') = COALESCE(:planno, '')
                AND SOPNO = :sopno
            """)

            db.execute(delete_sql, {
                "daily_no": daily_no,
                "planno": planno,
                "sopno": sopno
            })

            db.commit()

            logger.info(f"已從資料庫刪除草稿記錄 (daily_no: {daily_no}, planno: {planno}, sopno: {sopno})")

            # 4. 刪除實體檔案
            upload_base_dir = Path("uploads")
            deleted_files = 0
            failed_files = []

            for file_path in files_to_delete:
                try:
                    full_path = upload_base_dir / file_path
                    if full_path.exists() and full_path.is_file():
                        os.remove(full_path)
                        deleted_files += 1
                        logger.info(f"已刪除檔案: {full_path}")
                    else:
                        logger.warning(f"檔案不存在: {full_path}")
                except Exception as e:
                    logger.error(f"刪除檔案失敗 {full_path}: {str(e)}")
                    failed_files.append(file_path)

            if failed_files:
                logger.warning(f"有 {len(failed_files)} 個檔案刪除失敗")

            logger.info(f"草稿記錄刪除完成 - 檔案: {deleted_files} 個")

        except ValueError:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting draft record: {str(e)}")
            raise
