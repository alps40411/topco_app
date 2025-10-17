# backend/app/services/record_service.py

import json
import logging
import os
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import UploadFile, HTTPException

from ..core.config import settings
from ..models.user import User

logger = logging.getLogger(__name__)

class RecordService:
    """專門處理所有與記錄相關的服務邏輯"""

    @staticmethod
    def get_consolidated_today(
        db: Session,
        empno: str,
        doc_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """取得指定日期的合併記錄（兼容今日查詢）"""
        try:
            # 如果沒有提供 doc_date，使用今日日期
            target_date = doc_date or datetime.now().strftime('%Y%m%d')

            # 查詢指定日期的所有活躍記錄
            draft_sql = text("""
                SELECT d.DAILY_NO, d.CONTENT, d.PLANNO, d.PLAN_SUBJ_C, d.SOPNO, d.SOP_DESC_C,
                       d.WORK_ITEM_SEQ, d.SERVICE_COCODE, d.SERVICE_EMPNO, d.SERVICE_EMPNAMEC,
                       d.SERVICE_TARGET_COCODE, d.SERVICE_DEPTNO,
                       d.EXECUTION_TIME_MINUTES, d.FILES, d.AI_CONTENT, d.STATUS
                FROM jps.tdr_draft d
                WHERE d.EMPNO = :empno
                AND d.DOC_DATE = :doc_date
                ORDER BY d.RECORD_ID
            """)

            draft_result = db.execute(draft_sql, {
                "empno": empno,
                "doc_date": target_date
            })

            rows = draft_result.fetchall()
            logger.info(f"查詢到 {len(rows)} 條記錄 for empno={empno}, date={target_date}")

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
                service_target_cocode = row[10] or ""
                service_deptno = row[11] or ""
                execution_time_minutes = row[12] or 0
                files_json = row[13] or "[]"
                ai_content = row[14]
                status = row[15]

                # 解析多個工作項目序號並取得對應的中文名稱
                work_item_names = []
                work_item_ids = []
                if work_item_seq and sopno:
                    logger.info(f"處理工作項目序列: '{work_item_seq}', sopno: '{sopno}'")
                    # 分割工作項目序號（如 "1/2" → ["1", "2"]）
                    seq_parts = work_item_seq.split('/')
                    logger.info(f"分割後的序號: {seq_parts}")
                    for seq in seq_parts:
                        if seq.strip():
                            # 將序號轉換為整數ID (用於前端編輯)
                            try:
                                work_item_ids.append(int(seq.strip()))
                            except ValueError:
                                pass

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

                # 查詢服務公司中文名稱
                service_company_name = service_cocode
                if service_cocode:
                    company_sql = text("""
                        SELECT coabbv FROM jps.dcd001$master
                        WHERE cocode = :cocode
                    """)
                    company_result = db.execute(company_sql, {"cocode": service_cocode}).fetchone()
                    if company_result:
                        service_company_name = company_result[0]

                # 構建服務對象名稱
                service_target_name = ""
                if service_empnamec and service_empno:
                    service_target_name = f"{service_empnamec}"

                # 將 planno 轉換為整數 ID (如果存在)
                project_id = None
                if planno:
                    try:
                        project_id = int(planno)
                    except (ValueError, TypeError):
                        project_id = planno

                # 將 sopno 轉換為整數 ID (如果存在)
                execution_work_id = None
                if sopno:
                    try:
                        execution_work_id = int(sopno)
                    except (ValueError, TypeError):
                        execution_work_id = sopno

                consolidated_records.append({
                    "daily_no": daily_no,
                    "sopno": sopno,
                    "project": {
                        "id": project_id,
                        "planno": planno,
                        "plan_subj_c": plan_subj_c
                    },
                    "execution_work_id": execution_work_id,
                    "execution_work_name": sop_desc_c,
                    "work_item_ids": work_item_ids,
                    "work_item_name": work_item_name,
                    "service_cocode": service_cocode,
                    "service_company_name": service_company_name,
                    "service_empno": service_empno,
                    "service_target_name": service_target_name,
                    "service_target_cocode": service_target_cocode,
                    "service_deptno": service_deptno,
                    "content": content,
                    "files": files,
                    "record_count": 1,
                    "ai_content": ai_content,
                    "total_execution_time_minutes": execution_time_minutes
                })

            return consolidated_records

        except Exception as e:
            logger.error(f"Error getting consolidated today: {str(e)}")
            raise

    # ✅ REMOVED: get_writing_status - Replaced by daily-date-range endpoint

    @staticmethod
    async def upload_file(
        db: Session,
        file: UploadFile,
        doc_date: str,
        empno: str,
        cocode: str
    ) -> Dict[str, Any]:
        """檔案上傳端點 - 使用 CommonAPI"""
        from ..services.commonapi_file_service import CommonApiFileService

        try:
            logger.info(f"上傳檔案: {file.filename}, empno={empno}, cocode={cocode}")

            # 檢查檔案類型
            allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.gif'}
            file_ext = Path(file.filename or "").suffix.lower()
            if file_ext not in allowed_extensions:
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

        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise

    # ✅ REMOVED: delete_upload - CommonAPI 檔案不實體刪除

    @staticmethod
    def submit_daily_report(
        db: Session,
        empno: str,
        cocode: str,
        doc_date: str
    ) -> Dict[str, Any]:
        """
        提交日報到正式表

        Args:
            db: 資料庫 Session
            empno: 員工編號
            cocode: 公司代碼
            doc_date: 日報日期 (YYYYMMDD)

        Returns:
            提交結果
        """
        # 導入需要的服務
        from ..services.legacy_service_v2 import LegacyReportServiceV2

        try:
            now = datetime.now()
            logger.info(f"提交日報，empno={empno}, cocode={cocode}, doc_date={doc_date}")

            # 查詢今日所有暫存資料
            draft_sql = text("""
                SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE,
                       PLANNO, PLAN_SUBJ_C, SOPNO, SOP_DESC_C, WORK_ITEM_SEQ,
                       SERVICE_COCODE, SERVICE_EMPNO, SERVICE_EMPNAMEC, SERVICE_TARGET_COCODE, SERVICE_DEPTNO,
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

            if review_result and review_result[0] in ['Y', 'A']:
                raise HTTPException(
                    status_code=403,
                    detail="此日報已被主管審閱，無法再進行修改"
                )

            should_update_daily_open = not (review_result and review_result[0] == 'T')

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
                total_word_count += draft[17] or 0
                if draft[20]:
                    try:
                        files = json.loads(draft[20])
                        all_files.extend(files)
                    except:
                        pass
                if draft[18]:
                    if all_att_file1:
                        all_att_file1 += "," + draft[18]
                    else:
                        all_att_file1 = draft[18]
                if draft[19]:
                    if all_att_file2:
                        all_att_file2 += "," + draft[19]
                    else:
                        all_att_file2 = draft[19]

            # 取得執行工作描述
            main_sop_desc_c = []
            all_sopno = [draft[7] for draft in draft_results]

            for sopno in all_sopno:
                sop_sql = text("SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno")
                sop_result = db.execute(sop_sql, {"sopno": sopno}).fetchone()
                main_sop_desc_c.append(sop_result[0])
            main_sop_desc_c = list(set(main_sop_desc_c))
            main_sop_desc_c = " ".join(main_sop_desc_c)

            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')

            # 檢查是否為重新提交
            check_master_sql = text("""
                SELECT COUNT(*) FROM jps.tdr_master
                WHERE daily_no = :daily_no
            """)
            master_exists = db.execute(check_master_sql, {"daily_no": daily_no}).scalar() > 0

            if master_exists:
                # 更新現有記錄
                logger.info(f"重新提交日報 {daily_no}，更新 master 資料")
                RecordService._update_existing_report(
                    db, daily_no, empno, doc_date, total_word_count,
                    all_att_file1, all_att_file2, main_sop_desc_c,
                    current_date, current_time
                )
            else:
                # 創建新記錄
                logger.info(f"首次提交日報 {daily_no}，創建新的 master 資料")
                RecordService._create_new_report(
                    db, daily_no, cocode, empno, deptno, doc_date,
                    empnamec, deptnamec, g_deptno, leader,
                    main_sop_desc_c, total_word_count,
                    all_att_file1, all_att_file2,
                    current_date, current_time
                )

            # 處理詳細記錄
            RecordService._process_report_details(
                db, daily_no, draft_results, empnamec,
                cocode, empno, current_date, current_time
            )

            # 處理檔案
            RecordService._process_report_files(
                db, daily_no, draft_results, empno, cocode, doc_date
            )

            # 插入 eai_source 觸發簽核
            RecordService._insert_eai_source(
                db, daily_no, empnamec, main_sop_desc_c,
                cocode, empno, current_time
            )

            # 更新暫存狀態
            update_draft_sql = text("""
                UPDATE jps.tdr_draft SET STATUS = 'S' WHERE DAILY_NO = :daily_no
            """)
            db.execute(update_draft_sql, {"daily_no": daily_no})

            # 更新 tdr_daily_open 狀態
            if should_update_daily_open:
                logger.info(f"更新 tdr_daily_open 狀態為 Complete")
                update_daily_open_sql = text("""
                    UPDATE jps.tdr_daily_open
                    SET status = 'Complete'
                    WHERE cocode = :cocode
                    AND empno = :empno
                    AND status = 'Active'
                    AND doc_date = :doc_date
                """)
                db.execute(update_daily_open_sql, {
                    "cocode": cocode,
                    "empno": empno,
                    "doc_date": doc_date
                })

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
            logger.error(f"提交日報失敗: {str(e)}")
            raise HTTPException(status_code=500, detail=f"日報上傳失敗: {str(e)}")

    @staticmethod
    def _update_existing_report(
        db: Session, daily_no: str, empno: str, doc_date: str,
        total_word_count: int, all_att_file1: str, all_att_file2: str,
        main_sop_desc_c: str, current_date: str, current_time: str
    ):
        """更新現有的日報記錄"""
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

        # 刪除舊記錄
        db.execute(text("DELETE FROM jps.tdr_detail1 WHERE daily_no = :daily_no"), {"daily_no": daily_no})
        db.execute(text("DELETE FROM jps.tdr_detail2 WHERE daily_no = :daily_no"), {"daily_no": daily_no})
        db.execute(text("DELETE FROM jps.eai_source WHERE key = :daily_no"), {"daily_no": daily_no})

        daily_no_prefix = int(daily_no) * 1000000
        db.execute(text("""
            DELETE FROM jps.tdr_upload_file
            WHERE id >= :daily_no_start AND id < :daily_no_end
        """), {
            "daily_no_start": daily_no_prefix,
            "daily_no_end": daily_no_prefix + 1000000
        })

        logger.info(f"已刪除舊記錄: daily_no={daily_no}")

    @staticmethod
    def _create_new_report(
        db: Session, daily_no: str, cocode: str, empno: str, deptno: str,
        doc_date: str, empnamec: str, deptnamec: str, g_deptno: str,
        leader: str, main_sop_desc_c: str, total_word_count: int,
        all_att_file1: str, all_att_file2: str,
        current_date: str, current_time: str
    ):
        """創建新的日報記錄"""
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

    @staticmethod
    def _process_report_details(
        db: Session, daily_no: str, draft_results: List,
        empnamec: str, cocode: str, empno: str,
        current_date: str, current_time: str
    ):
        """處理日報的詳細記錄（detail1 和 detail2）"""
        # 按 planno + sopno 分組
        planno_sopno_groups = {}
        for draft in draft_results:
            planno = draft[5] or ""
            sopno = draft[7]
            group_key = f"{planno}_{sopno}"

            if group_key not in planno_sopno_groups:
                planno_sopno_groups[group_key] = {
                    'planno': planno,
                    'sopno': sopno,
                    'drafts': [],
                    'files': []
                }
            planno_sopno_groups[group_key]['drafts'].append(draft)

            if draft[20]:
                try:
                    files = json.loads(draft[20])
                    planno_sopno_groups[group_key]['files'].extend(files)
                except:
                    pass

        # 插入 detail1 和 detail2
        daily_sub_nos = 1
        planno_sopno_to_daily_sub_nos = {}

        for group_key, group_data in planno_sopno_groups.items():
            planno = group_data['planno']
            sopno = group_data['sopno']
            drafts_in_group = group_data['drafts']

            planno_sopno_to_daily_sub_nos[group_key] = daily_sub_nos

            # 插入 detail1
            db.execute(text("""
                INSERT INTO jps.tdr_detail1 (
                    DAILY_NO, DAILY_SUB_NOS, XUSER, XDATE, XTIME, CUNO1, COMP_SERNO1
                ) VALUES (
                    :daily_no, :daily_sub_nos, :empnamec, :current_date, :current_time, NULL, NULL
                )
            """), {
                "daily_no": daily_no,
                "daily_sub_nos": daily_sub_nos,
                "empnamec": empnamec,
                "current_date": current_date,
                "current_time": current_time
            })

            # 插入 detail2
            daily_job_nos = 1
            for draft in drafts_in_group:
                work_item_names = []
                if draft[9] and draft[7]:
                    seq_parts = str(draft[9]).split('/')
                    for seq in seq_parts:
                        if seq.strip():
                            work_item_result = db.execute(text("""
                                SELECT name FROM jps.tpm_sop_detail
                                WHERE sopno = :sopno AND seq = :seq
                            """), {
                                "sopno": draft[7],
                                "seq": seq.strip()
                            }).fetchone()

                            if work_item_result and work_item_result[0]:
                                work_item_names.append(work_item_result[0])
                            else:
                                work_item_names.append(f"工作項目 {seq}")

                work_item_name = " / ".join(work_item_names) if work_item_names else str(draft[9])

                db.execute(text("""
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
                        :service_cocode, :service_empno, :service_target_cocode, :service_deptno, '1', :content,
                        :service_empnamec, :planno, :sopno
                    )
                """), {
                    "daily_no": daily_no,
                    "daily_sub_nos": daily_sub_nos,
                    "daily_job_nos": daily_job_nos,
                    "cocode": cocode,
                    "empno": empno,
                    "work_item_name": work_item_name,
                    "empnamec": empnamec,
                    "content": draft[15],
                    "execution_time_minutes": draft[16]/60,
                    "service_cocode": draft[10],
                    "service_empno": draft[11],
                    "service_target_cocode": draft[13],
                    "service_deptno": draft[14],
                    "service_empnamec": draft[12],
                    "planno": draft[5] or '0',
                    "sopno": draft[7],
                    "current_date": current_date,
                    "current_time": current_time
                })

                daily_job_nos += 1

            daily_sub_nos += 1

        # 返回分組資訊供檔案處理使用
        return planno_sopno_groups, planno_sopno_to_daily_sub_nos

    @staticmethod
    def _process_report_files(
        db: Session, daily_no: str, draft_results: List,
        empno: str, cocode: str, doc_date: str
    ):
        """處理日報的附件檔案"""
        from ..services.legacy_service_v2 import LegacyReportServiceV2

        # 重新構建分組（與 _process_report_details 相同的邏輯）
        planno_sopno_groups = {}
        for draft in draft_results:
            planno = draft[5] or ""
            sopno = draft[7]
            group_key = f"{planno}_{sopno}"

            if group_key not in planno_sopno_groups:
                planno_sopno_groups[group_key] = {
                    'planno': planno,
                    'sopno': sopno,
                    'drafts': [],
                    'files': []
                }
            planno_sopno_groups[group_key]['drafts'].append(draft)

            if draft[20]:
                try:
                    files = json.loads(draft[20])
                    planno_sopno_groups[group_key]['files'].extend(files)
                except:
                    pass

        daily_sub_nos = 1
        planno_sopno_to_daily_sub_nos = {}
        for group_key in planno_sopno_groups.keys():
            planno_sopno_to_daily_sub_nos[group_key] = daily_sub_nos
            daily_sub_nos += 1

        # 處理檔案
        total_files_processed = 0
        for group_key, group_data in planno_sopno_groups.items():
            planno = group_data['planno']
            sopno = group_data['sopno']
            group_files = group_data['files']
            corresponding_daily_sub_nos = planno_sopno_to_daily_sub_nos[group_key]

            if group_files:
                logger.info(f"處理 planno={planno}, sopno={sopno} (daily_sub_nos={corresponding_daily_sub_nos}) 的 {len(group_files)} 個檔案")

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

        logger.info(f"檔案處理完成，總共處理 {total_files_processed} 個檔案")

    @staticmethod
    def _insert_eai_source(
        db: Session, daily_no: str, empnamec: str, main_sop_desc_c: str,
        cocode: str, empno: str, current_time: str
    ):
        """插入 eai_source 以觸發簽核流程"""
        eai_seq = db.execute(text("SELECT jps.seq_eai_source.nextval FROM dual")).scalar_one()
        eai_current_date = datetime.now().strftime('%Y/%m/%d')

        subject = f'{empnamec}的日報({main_sop_desc_c})'
        report_view_url = f"%2fMyReportAI%2f%3fcocode%3d{cocode}%26daily_no%3d{daily_no}"

        doc_bady = (
            f"Source=JpsReportDailySend^|Action=toWkf^|cocode=toWkf^|xuser={empno}^|"
            f"doc_date={eai_current_date}^|doc_time={current_time}^|"
            f"href={report_view_url}^|Key={daily_no}^|Subject={subject}"
        )

        db.execute(text("""
            INSERT INTO jps.eai_source
            (eai_seq, source, subject, cocode, xuser, touser, doc_date, doc_time, key, action, doc_bady, status)
            VALUES (:eai_seq, 'JpsReportDailySend', :subject, :cocode, :xuser, '', :doc_date, :doc_time, :key, 'toWkf', :doc_bady, 'N')
        """), {
            "eai_seq": eai_seq,
            "subject": subject,
            "cocode": cocode,
            "xuser": empno,
            "doc_date": eai_current_date,
            "doc_time": current_time,
            "key": daily_no,
            "doc_bady": doc_bady
        })

        logger.info(f"成功插入 eai_source 記錄, eai_seq: {eai_seq}")
