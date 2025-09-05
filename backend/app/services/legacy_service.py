# backend/app/services/legacy_service.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from ..schemas.legacy_schemas import DailyReportListItem, DailyReportContent, WorkPlan
import logging
import json
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class LegacyReportService:
    
    @staticmethod
    def get_daily_reports_by_supervisor(
        db: Session, 
        empno: str, 
        doc_date: str, 
        cocode: str = None, 
        deptno: str = None
    ) -> List[Dict[str, Any]]:
        """取得日報列表 BY 工號（主管）"""
        
        # 構建動態的工號後4碼（如果需要的話）
        empno_suffix = empno[-4:] if len(empno) >= 4 else empno
        
        sql = text("""
            SELECT
                daily_no,
                cocode,
                empno,
                empnamec,
                emergency,
                classify,
                att_file1,
                att_file2,
                att_file3,
                cust_ename1,
                cust_ename2,
                cust_ename3,
                cust_comp_abbv1,
                cust_comp_abbv2,
                cust_comp_abbv3,
                sop_desc_c,
                reply_status,
                memo_status,
                doc_date,
                proj_status,
                openpath,
                openwebpage,
                sort_cocode,
                g_deptno,
                deptnamec,
                reply_count,
                replier_count,
                my_ask,
                other_ask,
                isForwarded,
                LASTDATETIME,
                practice_cocode,
                coabbv
            FROM (
                SELECT
                    a.daily_no,
                    a.cocode,
                    a.empno,
                    a.empnamec,
                    a.emergency,
                    a.classify,
                    a.att_file1,
                    a.att_file2,
                    a.att_file3,
                    a.cust_ename1,
                    a.cust_ename2,
                    a.cust_ename3,
                    a.cust_comp_abbv1,
                    a.cust_comp_abbv2,
                    a.cust_comp_abbv3,
                    a.sop_desc_c,
                    a.reply_status,
                    a.memo_status,
                    a.doc_date,
                    a.proj_status,
                    a.openpath,
                    a.openwebpage,
                    d.g_deptno AS gdeptno,
                    CASE
                        WHEN COALESCE(e.practice_cocode, a.cocode) = 'J10' THEN 'J071'
                        WHEN COALESCE(e.practice_cocode, a.cocode) = 'J17' THEN 'J072'
                        ELSE COALESCE(e.practice_cocode, a.cocode)
                    END AS sort_cocode,
                    (
                        CASE
                            WHEN e.practice_cocode IS NULL AND e.practice_deptno IS NULL
                                THEN d.g_deptno
                            ELSE (
                                SELECT g_deptno
                                FROM dcd002$master g
                                WHERE g.cocode = e.practice_cocode
                                  AND g.deptno = e.practice_deptno
                            )
                        END
                    ) AS g_deptno,
                    (
                        CASE
                            WHEN e.practice_cocode IS NULL AND e.practice_deptno IS NULL
                                THEN CASE
                                    WHEN a.cocode = 'A' THEN d.deptnamec
                                    ELSE (
                                        SELECT c1.coabbv
                                        FROM dcd001$master c1
                                        WHERE c1.cocode = a.cocode
                                    ) || '-' || (
                                        SELECT c2.deptnamec
                                        FROM dcd002$master c2
                                        WHERE c2.cocode = a.cocode
                                          AND c2.deptno = d.deptno
                                          AND d.deptno <> '00000'
                                    )
                                END
                            ELSE CASE
                                WHEN e.practice_cocode = 'A' THEN ''
                                ELSE (
                                    SELECT c1.coabbv
                                    FROM dcd001$master c1
                                    WHERE c1.cocode = e.practice_cocode
                                ) || '-'
                            END || (
                                SELECT c2.deptnamec
                                FROM dcd002$master c2
                                WHERE c2.cocode = e.practice_cocode
                                  AND c2.deptno = e.practice_deptno
                            )
                        END
                    ) AS deptnamec,
                    (
                        SELECT COUNT(daily_no) AS cnt
                        FROM tdr_reply
                        WHERE daily_no = a.daily_no
                    ) AS reply_count,
                    (
                        SELECT COUNT(daily_no) AS cnt
                        FROM tdr_reply
                        WHERE daily_no = a.daily_no
                          AND empno = :empno
                    ) AS replier_count,
                    (
                        SELECT CASE WHEN COUNT(daily_no) > 0 THEN 'true' ELSE '' END AS cnt
                        FROM tdr_reply
                        WHERE daily_no = a.daily_no
                          AND empno = :empno
                          AND memo NOT LIKE '電子表單%'
                          AND memo NOT IN (SELECT memo FROM TDR_REPLY_GENERAL_COMMENT)
                    ) AS my_ask,
                    (
                        SELECT CASE WHEN COUNT(daily_no) > 0 THEN 'true' ELSE '' END AS cnt
                        FROM tdr_reply
                        WHERE daily_no = a.daily_no
                          AND empno <> :empno
                          AND memo NOT LIKE '電子表單%'
                          AND memo NOT IN (SELECT memo FROM TDR_REPLY_GENERAL_COMMENT)
                    ) AS other_ask,
                    (
                        SELECT CASE WHEN COUNT(daily_no) > 0 THEN 'true' ELSE 'false' END AS cnt
                        FROM tdr_msg_send_log
                        WHERE daily_no = a.daily_no
                          AND from_empno = :empno
                    ) AS isForwarded,
                    a.LASTDATETIME,
                    e.practice_cocode,
                    f.coabbv
                FROM tdr_master a
                LEFT JOIN dcd003$master e
                    ON a.cocode = e.cocode
                   AND a.empno = e.empno
                LEFT JOIN dcd002$master d
                    ON e.cocode = d.cocode
                   AND e.deptno = d.deptno
                LEFT JOIN dcd001$master f
                    ON e.cocode = f.cocode
                WHERE
                    a.status = 'N'
                    AND a.doc_date = :doc_date
                    AND (e.QUITDATE IS NULL OR e.QUITDATE >= a.DOC_DATE)
                    AND (e.RIGHT_STOP_DATE IS NULL OR e.RIGHT_STOP_DATE > a.DOC_DATE)
                    AND a.empno <> '01188'
                    AND (a.cocode, a.empno) IN (
                        SELECT cocode, empno
                        FROM groupfoodchn
                        WHERE supervisor IN (:empno, :empno_suffix)
                          AND empno NOT IN ('?0002', '?0003')
                          OR :empno IN ('00002','01174','01376','02970','Z0005')

                        UNION ALL

                        SELECT s1.cocode, s1.empno
                        FROM dcd003$master s1
                        JOIN dcd002$master s2
                            ON s1.cocode = s2.cocode
                           AND s2.deptno = s1.deptno
                        WHERE (:cocode IS NULL OR s1.cocode = :cocode)
                          AND (
                            s1.empno = :empno
                            OR (
                                (
                                    (s1.PRACTICE_COCODE IS NULL OR s1.PRACTICE_DEPTNO IS NULL)
                                    AND (:cocode IS NULL OR s1.cocode = :cocode)
                                    AND (
                                        s1.deptno IN (
                                            SELECT DISTINCT deptno
                                            FROM GROUPDEPTCHN
                                            WHERE cocode = 'A'
                                              AND (leader=:empno OR pleader=:empno)
                                        )
                                        OR (:deptno IS NULL OR s1.deptno = :deptno)
                                    )
                                )
                                OR (
                                    s1.PRACTICE_COCODE IS NOT NULL
                                    AND s1.PRACTICE_DEPTNO IS NOT NULL
                                    AND (:cocode IS NULL OR s1.PRACTICE_COCODE = :cocode)
                                    AND (
                                        s1.PRACTICE_DEPTNO IN (
                                            SELECT DISTINCT deptno
                                            FROM GROUPDEPTCHN
                                            WHERE cocode = 'A'
                                              AND (leader=:empno OR pleader=:empno)
                                        )
                                        OR (:deptno IS NULL OR s1.deptno = :deptno)
                                    )
                                )
                                OR (
                                    s1.PRACTICE_COCODE IS NOT NULL
                                    AND s1.PRACTICE_DEPTNO IS NOT NULL
                                    AND (s1.PRACTICE_COCODE, s1.PRACTICE_DEPTNO) IN (
                                        SELECT practice_cocode, practice_deptno
                                        FROM dcd003$master
                                        WHERE (cocode, empno) IN ((:cocode, :empno))
                                    )
                                )
                            )
                          )

                        UNION ALL

                        SELECT e_cocode AS cocode, empno
                        FROM diarysupers
                        WHERE cmark IS NULL
                          AND (VALID_DATE IS NULL OR VALID_DATE > :doc_date)
                          AND supervisor IN (:empno, :empno_suffix)
                    )
            ) 
            ORDER BY
                sort_cocode,
                CASE WHEN SUBSTRING(g_deptno FROM 1 FOR 2) = '00' THEN '99' ELSE g_deptno END,
                deptnamec,
                empno,
                daily_no
        """)
        
        try:
            result = db.execute(sql, {
                "empno": empno,
                "empno_suffix": empno_suffix,
                "doc_date": doc_date,
                "cocode": cocode,
                "deptno": deptno
            })
            
            # 將結果轉換為字典列表
            columns = result.keys()
            reports = []
            for row in result.fetchall():
                report_dict = dict(zip(columns, row))
                reports.append(report_dict)
            
            logger.info(f"Found {len(reports)} daily reports for empno={empno}, date={doc_date}")
            return reports
            
        except Exception as e:
            logger.error(f"Error fetching daily reports: {str(e)}")
            raise
    
    @staticmethod
    def get_daily_report_content(db: Session, daily_no: str) -> List[Dict[str, Any]]:
        """取得日報內容"""
        
        sql = text("""
            SELECT a.cuno1
            ,b.daily_sub_nos
            ,b.sopno
            ,b.sop_code
            ,b.prod_cate
            ,b.itemdesc1
            ,b.exetime
            ,b.estimate
            ,b.attitude
            ,b.memo_collect
            ,b.cuno_subj
            ,b.cuno_msg
            ,b.cuno_collect
            ,b.comp_inf
            ,b.comp_desc
            ,b.comp_collect
            ,b.ques_subj
            ,b.ques_desc
            ,b.solut_subj
            ,b.solut_desc
            ,b.solut_status
            ,b.att_file3
            ,b.xuser
            ,b.xdate
            ,b.xtime
            ,b.empname1
            ,b.empname2
            ,b.empname3
            ,b.prod_no
            ,b.create_msg
            ,b.comp_serno
            ,b.cuno_comp_serno
            ,b.cocode
            ,b.empno
            ,b.status
            ,b.planno
            ,b.memo
            ,b.empname4
            ,b.empname5
            ,b.cuno_infcont
            ,b.comp_infcont
            ,b.ques_infcont
            ,b.solut_infcont
            ,b.finish_rate
            ,b.pps_cocode
            ,b.pps_empno
            ,b.pps_deptno
            ,b.pps_empnamec
            ,b.ship_log
            ,b.cuno_msg1
            ,b.ques_desc1
            ,b.solut_desc1
            ,b.memo1
            ,b.cuno_msg2
            ,b.ques_desc2
            ,b.solut_desc2
            ,b.memo2
            ,b.reply
            ,b.pps_servecocode
            ,b.projno
            ,b.proj_cocode
            ,b.pps_empno
            ,b.pps_cocode
            ,b.memo_collect
            FROM tdr_detail1 a
            JOIN tdr_detail2 b ON b.daily_no = a.daily_no
            AND b.daily_sub_nos = a.daily_sub_nos
            WHERE a.daily_no = :daily_no
            ORDER BY a.daily_sub_nos, b.daily_job_nos
        """)
        
        try:
            result = db.execute(sql, {"daily_no": daily_no})
            
            # 將結果轉換為字典列表
            columns = result.keys()
            contents = []
            for row in result.fetchall():
                content_dict = dict(zip(columns, row))
                contents.append(content_dict)
                
            logger.info(f"Found {len(contents)} content records for daily_no={daily_no}")
            return contents
            
        except Exception as e:
            logger.error(f"Error fetching daily report content: {str(e)}")
            raise
    
    @staticmethod
    def get_work_plans(db: Session, empno: str) -> List[Dict[str, Any]]:
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
            for row in result.fetchall():
                plan_dict = dict(zip(columns, row))
                # 確保返回的格式與前端期望一致
                plan_dict['empno'] = empno
                plan_dict['planno'] = plan_dict['planno']
                plan_dict['plan_subj_c'] = plan_dict['plan_subj_c'] or f"工作計畫 {plan_dict['planno']}"
                plans.append(plan_dict)

            logger.info(f"Found {len(plans)} work plans for empno={empno}")
            return plans

        except Exception as e:
            logger.error(f"Error fetching work plans: {str(e)}")
            raise
    
    @staticmethod
    def save_draft(db: Session, empno: str, cocode: str, doc_date: str, 
                   draft_type: str, draft_content: Dict[str, Any]) -> str:
        """保存日報暫存 - 支援合併相同工作計畫的內容"""
        try:
            # 取得目前日期時間
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 檢查是否已有相同工作計畫和執行工作的暫存
            existing_draft_sql = text("""
                SELECT DAILY_NO, DRAFT_CONTENT
                FROM tdr_draft
                WHERE EMPNO = :empno 
                AND COCODE = :cocode
                AND DOC_DATE = :doc_date
                AND STATUS = 'A'
                AND DRAFT_CONTENT::json->>'planno' = :planno
                AND DRAFT_CONTENT::json->>'sopno' = :sopno
            """)
            
            existing_result = db.execute(existing_draft_sql, {
                "empno": empno,
                "cocode": cocode,
                "doc_date": doc_date,
                "planno": draft_content.get('planno'),
                "sopno": draft_content.get('sopno')
            }).fetchone()
            
            if existing_result:
                # 合併現有暫存內容
                existing_content = json.loads(existing_result[1])
                merged_content = LegacyReportService._merge_draft_content(existing_content, draft_content)
                
                # 更新現有暫存
                update_sql = text("""
                    UPDATE tdr_draft 
                    SET DRAFT_CONTENT = :draft_content,
                        UPDATED_DATE = :updated_date,
                        UPDATED_TIME = :updated_time
                    WHERE DAILY_NO = :daily_no
                """)
                
                db.execute(update_sql, {
                    "daily_no": existing_result[0],
                    "draft_content": json.dumps(merged_content, ensure_ascii=False),
                    "updated_date": current_date,
                    "updated_time": current_time
                })
                
                db.commit()
                logger.info(f"Draft merged successfully: {existing_result[0]}")
                return existing_result[0]
            else:
                # 取得新的日報編號
                daily_no_sql = text("SELECT seq_tdr_master.nextval FROM dual")
                daily_no_result = db.execute(daily_no_sql)
                daily_no = str(daily_no_result.scalar())
                
                # 創建新的暫存記錄
                insert_sql = text("""
                    INSERT INTO tdr_draft (
                        DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE, DRAFT_CONTENT,
                        CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME, STATUS
                    ) VALUES (
                        :daily_no, :empno, :cocode, :doc_date, :draft_type, :draft_content,
                        :created_date, :created_time, :updated_date, :updated_time, 'A'
                    )
                """)
                
                db.execute(insert_sql, {
                    "daily_no": daily_no,
                    "empno": empno,
                    "cocode": cocode,
                    "doc_date": doc_date,
                    "draft_type": draft_type,
                    "draft_content": json.dumps(draft_content, ensure_ascii=False),
                    "created_date": current_date,
                    "created_time": current_time,
                    "updated_date": current_date,
                    "updated_time": current_time
                })
                
                db.commit()
                logger.info(f"Draft saved successfully: {daily_no}")
                return daily_no
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving draft: {str(e)}")
            raise
    
    @staticmethod
    def _merge_draft_content(existing_content: Dict[str, Any], new_content: Dict[str, Any]) -> Dict[str, Any]:
        """合併暫存內容"""
        merged = existing_content.copy()
        
        # 合併工作項目（陣列）
        existing_items = existing_content.get('work_item_seq', []) or []
        new_items = new_content.get('work_item_seq', []) or []
        merged['work_item_seq'] = list(set(existing_items + new_items))  # 去重
        
        # 合併檔案
        existing_files = existing_content.get('files', []) or []
        new_files = new_content.get('files', []) or []
        merged['files'] = existing_files + new_files
        
        # 合併內容（文字）
        existing_text = existing_content.get('content', '') or ''
        new_text = new_content.get('content', '') or ''
        if existing_text and new_text:
            merged['content'] = f"{existing_text}\n\n{new_text}"
        elif new_text:
            merged['content'] = new_text
        
        # 累加執行時間
        existing_time = existing_content.get('execution_time_minutes', 0) or 0
        new_time = new_content.get('execution_time_minutes', 0) or 0
        merged['execution_time_minutes'] = existing_time + new_time
        
        # 更新其他欄位（以新內容為準）
        for key in ['planno', 'plan_subj_c', 'sopno', 'sop_desc_c', 'work_item_name',
                   'service_cocode', 'service_empno', 'service_empnamec', 'service_deptno']:
            if new_content.get(key):
                merged[key] = new_content[key]
        
        return merged
    
    @staticmethod
    def get_today_drafts(db: Session, empno: str, cocode: str, doc_date: str) -> List[Dict[str, Any]]:
        """取得今日的暫存資料"""
        try:
            sql = text("""
                SELECT DAILY_NO, EMPNO, COCODE, DOC_DATE, DRAFT_TYPE, DRAFT_CONTENT,
                       CREATED_DATE, CREATED_TIME, UPDATED_DATE, UPDATED_TIME, STATUS
                FROM tdr_draft
                WHERE EMPNO = :empno 
                AND COCODE = :cocode
                AND DOC_DATE = :doc_date
                AND STATUS = 'A'
                ORDER BY CREATED_DATE DESC, CREATED_TIME DESC
            """)
            
            result = db.execute(sql, {
                "empno": empno,
                "cocode": cocode,
                "doc_date": doc_date
            })
            
            drafts = []
            for row in result:
                draft_content = json.loads(row[5]) if row[5] else {}
                drafts.append({
                    "daily_no": row[0],
                    "empno": row[1],
                    "cocode": row[2],
                    "doc_date": row[3],
                    "draft_type": row[4],
                    "draft_content": draft_content,
                    "created_date": row[6],
                    "created_time": row[7],
                    "updated_date": row[8],
                    "updated_time": row[9],
                    "status": row[10]
                })
            
            return drafts
            
        except Exception as e:
            logger.error(f"Error getting today drafts: {str(e)}")
            return []
    
    @staticmethod
    def submit_draft_to_final(db: Session, daily_no: str, empno: str, cocode: str, 
                             doc_date: str, draft_content: Dict[str, Any]) -> str:
        """將暫存提交為正式日報"""
        try:
            from datetime import datetime
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 取得員工和部門資訊
            emp_sql = text("""
                SELECT EMPNAMEC, DEPTNO, DEPTNAMEC, G_DEPTNO, LEADER
                FROM dcd003$master
                WHERE EMPNO = :empno AND COCODE = :cocode
            """)
            
            emp_result = db.execute(emp_sql, {"empno": empno, "cocode": cocode}).fetchone()
            if not emp_result:
                raise Exception(f"找不到員工資訊: {empno}")
            
            empnamec, deptno, deptnamec, g_deptno, leader = emp_result
            
            # 計算字數
            content = draft_content.get('content', '')
            word_count = len(content) if content else 0
            
            # 1. 插入 tdr_master
            master_sql = text("""
                INSERT INTO tdr_master (
                    DAILY_NO, COCODE, EMPNO, DEPTNO, DOC_DATE, EMERGENCY, 
                    CLASSIFY, SCORE, XUSER, XDATE, XTIME, STATUS, LEADER, G_DEPTNO, EMPNAMEC, 
                    DEPTNAMEC, UPLOAD_SITE, EMPNAMEC_N, WFINBOX_STATUS, SOP_DESC_C, CUST_ENAME1, 
                    CUST_COMP_ABBV1, WORD_COUNT, ATT_FILE1, ATT_FILE2, openpath, openwebpage
                ) VALUES (
                    :daily_no, :cocode, :empno, :deptno, :doc_date, :emergency, 
                    :classify, :score, :xuser, :xdate, :xtime, :status, :leader, :g_deptno, :empnamec, 
                    :deptnamec, :upload_site, :empnamec_n, :wfinbox_status, :sop_desc_c, :cust_ename1, 
                    :cust_comp_abbv1, :word_count, :att_file1, :att_file2, :openpath, :openwebpage
                )
            """)
            
            db.execute(master_sql, {
                "daily_no": daily_no,
                "cocode": cocode,
                "empno": empno,
                "deptno": deptno,
                "doc_date": doc_date,
                "emergency": None,
                "classify": None,
                "score": 0,
                "xuser": empno,
                "xdate": current_date,
                "xtime": current_time,
                "status": "N",  # N繳交
                "leader": leader,
                "g_deptno": g_deptno,
                "empnamec": empnamec,
                "deptnamec": deptnamec,
                "upload_site": "D",
                "empnamec_n": empnamec,
                "wfinbox_status": "N",
                "sop_desc_c": draft_content.get('sop_desc_c', ''),
                "cust_ename1": None,
                "cust_comp_abbv1": None,
                "word_count": word_count,
                "att_file1": None,  # TODO: 處理附件
                "att_file2": None,  # TODO: 處理附件
                "openpath": "/MyReport/",
                "openwebpage": "viewed.aspx"
            })
            
            # 2. 插入 tdr_detail1
            detail1_sql = text("""
                INSERT INTO tdr_detail1 (
                    DAILY_NO, DAILY_SUB_NOS, XUSER, XDATE, XTIME, CUNO1, COMP_SERNO1
                ) VALUES (
                    :daily_no, :daily_sub_nos, :xuser, :xdate, :xtime, :cuno1, :comp_serno1
                )
            """)
            
            db.execute(detail1_sql, {
                "daily_no": daily_no,
                "daily_sub_nos": "1",
                "xuser": empno,
                "xdate": current_date,
                "xtime": current_time,
                "cuno1": None,
                "comp_serno1": None
            })
            
            # 3. 插入 tdr_detail2 - 為每個工作項目插入一筆記錄
            work_items = draft_content.get('work_item_seq', []) or []
            if not work_items:
                # 如果沒有工作項目，插入一筆預設記錄
                work_items = [""]
            
            for i, work_item in enumerate(work_items, 1):
                detail2_sql = text("""
                    INSERT INTO tdr_detail2 (
                        DAILY_NO, DAILY_SUB_NOS, DAILY_JOB_NOS, 
                        COCODE, EMPNO, SOP_CODE, STATUS, XUSER, XDATE, XTIME, ITEMDESC1, PROD_CATE, 
                        EXETIME, ESTIMATE, ATTITUDE, PROD_NO, SOLUT_SUBJ, SOLUT_STATUS, 
                        EMPNAME1, EMPNAME2, EMPNAME3, EMPNAME4, EMPNAME5, 
                        PPS_SERVECOCODE, PPS_EMPNO, PPS_COCODE, PPS_DEPTNO, MEMO_COLLECT, MEMO, PPS_EMPNAMEC, PLANNO, SOPNO
                    ) VALUES (
                        :daily_no, :daily_sub_nos, :daily_job_nos, 
                        :cocode, :empno, :sop_code, :status, :xuser, :xdate, :xtime, :itemdesc1, :prod_cate, 
                        :exetime, :estimate, :attitude, :prod_no, :solut_subj, :solut_status, 
                        :empname1, :empname2, :empname3, :empname4, :empname5, 
                        :pps_servecocode, :pps_empno, :pps_cocode, :pps_deptno, :memo_collect, :memo, :pps_empnamec, :planno, :sopno
                    )
                """)
                
                # 計算每個工作項目的執行時間（平均分配）
                total_time = draft_content.get('execution_time_minutes', 0) or 0
                item_time = total_time // len(work_items) if work_items else 0
                
                db.execute(detail2_sql, {
                    "daily_no": daily_no,
                    "daily_sub_nos": "1",
                    "daily_job_nos": str(i),
                    "cocode": cocode,
                    "empno": empno,
                    "sop_code": work_item or draft_content.get('work_item_name', ''),
                    "status": "N",
                    "xuser": empnamec,
                    "xdate": current_date,
                    "xtime": current_time,
                    "itemdesc1": content,  # 規格細項使用內容
                    "prod_cate": "PROD_CATE",
                    "exetime": item_time,
                    "estimate": None,
                    "attitude": None,
                    "prod_no": None,
                    "solut_subj": None,
                    "solut_status": None,
                    "empname1": "0",
                    "empname2": None,
                    "empname3": None,
                    "empname4": None,
                    "empname5": None,
                    "pps_servecocode": draft_content.get('service_cocode'),
                    "pps_empno": draft_content.get('service_empno'),
                    "pps_cocode": draft_content.get('service_cocode'),
                    "pps_deptno": draft_content.get('service_deptno'),
                    "memo_collect": "1",
                    "memo": content,
                    "pps_empnamec": draft_content.get('service_empnamec'),
                    "planno": draft_content.get('planno'),
                    "sopno": draft_content.get('sopno')
                })
            
            db.commit()
            logger.info(f"Report submitted successfully: {daily_no}")
            return daily_no
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error submitting draft to final: {str(e)}")
            raise
    
    
    @staticmethod
    def save_attachment(db: Session, draft_id: str, file_name: str, file_path: str,
                       file_size: int, file_type: str, is_selected_for_ai: bool = False) -> str:
        """保存附件"""
        try:
            # 生成附件ID
            att_id = f"ATT_{draft_id}_{uuid.uuid4().hex[:8]}"
            
            # 取得目前日期時間
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 插入附件記錄
            sql = text("""
                INSERT INTO tdr_draft_attachment (
                    ATT_ID, DRAFT_ID, FILE_NAME, FILE_PATH, FILE_SIZE, FILE_TYPE,
                    IS_SELECTED_FOR_AI, UPLOAD_DATE, UPLOAD_TIME, STATUS
                ) VALUES (
                    :att_id, :draft_id, :file_name, :file_path, :file_size, :file_type,
                    :is_selected_for_ai, :upload_date, :upload_time, 'A'
                )
            """)
            
            db.execute(sql, {
                "att_id": att_id,
                "draft_id": draft_id,
                "file_name": file_name,
                "file_path": file_path,
                "file_size": file_size,
                "file_type": file_type,
                "is_selected_for_ai": "Y" if is_selected_for_ai else "N",
                "upload_date": current_date,
                "upload_time": current_time
            })
            
            db.commit()
            logger.info(f"Attachment saved successfully: {att_id}")
            return att_id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving attachment: {str(e)}")
            raise
    
    @staticmethod
    def submit_report(db: Session, daily_no: str, empno: str, cocode: str, deptno: str,
                     doc_date: str, emergency: Optional[str], classify: Optional[str],
                     leader: str, g_deptno: str, empnamec: str, deptnamec: str,
                     sop_desc_c: str, word_count: int, att_file1: Optional[str],
                     att_file2: Optional[str], work_items: List[Dict[str, Any]]) -> str:
        """正式提交日報"""
        try:
            # 取得目前日期時間
            now = datetime.now()
            current_date = now.strftime('%Y%m%d')
            current_time = now.strftime('%H:%M:%S')
            
            # 插入主檔 tdr_master
            master_sql = text("""
                INSERT INTO tdr_master (
                    DAILY_NO, COCODE, EMPNO, DEPTNO, DOC_DATE, EMERGENCY, 
                    CLASSIFY, SCORE, XUSER, XDATE, XTIME, STATUS, LEADER, G_DEPTNO, EMPNAMEC, 
                    DEPTNAMEC, UPLOAD_SITE, EMPNAMEC_N, WFINBOX_STATUS, SOP_DESC_C, CUST_ENAME1, 
                    CUST_COMP_ABBV1, WORD_COUNT, ATT_FILE1, ATT_FILE2, openpath, openwebpage
                ) VALUES (
                    :daily_no, :cocode, :empno, :deptno, :doc_date, :emergency,
                    :classify, 0, :empno, :xdate, :xtime, 'N', :leader, :g_deptno, :empnamec,
                    :deptnamec, 'D', :empnamec, 'N', :sop_desc_c, null,
                    null, :word_count, :att_file1, :att_file2, '/MyReport/', 'viewed.aspx'
                )
            """)
            
            db.execute(master_sql, {
                "daily_no": daily_no,
                "cocode": cocode,
                "empno": empno,
                "deptno": deptno,
                "doc_date": doc_date,
                "emergency": emergency,
                "classify": classify,
                "leader": leader,
                "g_deptno": g_deptno,
                "empnamec": empnamec,
                "deptnamec": deptnamec,
                "sop_desc_c": sop_desc_c,
                "word_count": word_count,
                "att_file1": att_file1,
                "att_file2": att_file2,
                "xdate": current_date,
                "xtime": current_time
            })
            
            # 插入明細檔
            for idx, work_item in enumerate(work_items, 1):
                # 插入 tdr_detail1
                detail1_sql = text("""
                    INSERT INTO tdr_detail1 (
                        DAILY_NO, DAILY_SUB_NOS, XUSER, XDATE, XTIME, CUNO1, COMP_SERNO1
                    ) VALUES (
                        :daily_no, :daily_sub_nos, :empno, :xdate, :xtime, null, null
                    )
                """)
                
                db.execute(detail1_sql, {
                    "daily_no": daily_no,
                    "daily_sub_nos": str(idx),
                    "empno": empno,
                    "xdate": current_date,
                    "xtime": current_time
                })
                
                # 插入 tdr_detail2
                detail2_sql = text("""
                    INSERT INTO tdr_detail2 (
                        DAILY_NO, DAILY_SUB_NOS, DAILY_JOB_NOS, COCODE, EMPNO, SOP_CODE, STATUS,
                        XUSER, XDATE, XTIME, ITEMDESC1, PROD_CATE, EXETIME, ESTIMATE, ATTITUDE,
                        PROD_NO, SOLUT_SUBJ, SOLUT_STATUS, EMPNAME1, EMPNAME2, EMPNAME3, EMPNAME4, EMPNAME5,
                        PPS_SERVECOCODE, PPS_EMPNO, PPS_COCODE, PPS_DEPTNO, MEMO_COLLECT, MEMO, 
                        PPS_EMPNAMEC, PLANNO, SOPNO
                    ) VALUES (
                        :daily_no, :daily_sub_nos, '1', :cocode, :empno, :sop_code, 'N',
                        :empno, :xdate, :xtime, :itemdesc1, 'PROD_CATE', :exetime, null, null,
                        null, null, null, '0', null, null, null, null,
                        :pps_servecocode, :pps_empno, :pps_cocode, :pps_deptno, '1', :memo,
                        :pps_empnamec, :planno, :sopno
                    )
                """)
                
                db.execute(detail2_sql, {
                    "daily_no": daily_no,
                    "daily_sub_nos": str(idx),
                    "cocode": cocode,
                    "empno": empno,
                    "sop_code": work_item.get('sop_code', ''),
                    "itemdesc1": work_item.get('itemdesc1', ''),
                    "exetime": work_item.get('exetime', 0),
                    "pps_servecocode": work_item.get('pps_servecocode'),
                    "pps_empno": work_item.get('pps_empno'),
                    "pps_cocode": work_item.get('pps_cocode'),
                    "pps_deptno": work_item.get('pps_deptno'),
                    "memo": work_item.get('memo', ''),
                    "pps_empnamec": work_item.get('pps_empnamec'),
                    "planno": work_item.get('planno'),
                    "sopno": work_item.get('sopno'),
                    "xdate": current_date,
                    "xtime": current_time
                })
            
            db.commit()
            logger.info(f"Report submitted successfully: {daily_no}")
            return daily_no
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error submitting report: {str(e)}")
            raise