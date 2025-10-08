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
