# backend/app/services/supervisor_service.py

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

logger = logging.getLogger(__name__)

class SupervisorService:
    """專門處理主管相關的服務邏輯"""

    @staticmethod
    def get_daily_homepage_reports(
        db: Session,
        empno: str,
        cocode: str,
        deptno: str,
        doc_date: str
    ) -> List[Dict[str, Any]]:
        """取得日報首頁 - 所有下屬的日報列表"""
        try:
            # ✅ 優化: 整合 can_view_detail 到主查詢中，消除 N+1 問題
            main_reports_sql = text("""
                SELECT
                    daily_no, cocode, empno, empnamec, emergency, classify, att_file1,
                    att_file2, att_file3, cust_ename1, cust_ename2, cust_ename3,
                    cust_comp_abbv1, cust_comp_abbv2, cust_comp_abbv3, sop_desc_c,
                    reply_status, memo_status, doc_date, proj_status, openpath,
                    openwebpage, sort_cocode, g_deptno, deptnamec, reply_count,
                    replier_count, my_ask, other_ask, isForwarded, LASTDATETIME,
                    practice_cocode, coabbv, can_view_detail
                FROM (
                    SELECT
                        a.daily_no, a.cocode, a.empno, a.empnamec, a.emergency, a.classify,
                        a.att_file1, a.att_file2, a.att_file3, a.cust_ename1, a.cust_ename2,
                        a.cust_ename3, a.cust_comp_abbv1, a.cust_comp_abbv2, a.cust_comp_abbv3,
                        a.sop_desc_c, a.reply_status, a.memo_status, a.doc_date, a.proj_status,
                        a.openpath, a.openwebpage, d.g_deptno AS gdeptno,
                        DECODE(
                            NVL(e.practice_cocode, a.cocode),
                            N'J10', N'J071',
                            N'J17', N'J072',
                            NVL(e.practice_cocode, a.cocode)
                        ) AS sort_cocode,
                        (CASE
                            WHEN e.practice_cocode IS NULL AND e.practice_deptno IS NULL THEN d.g_deptno
                            ELSE (SELECT g_deptno FROM dcd002$master g WHERE g.cocode = e.practice_cocode AND g.deptno = e.practice_deptno)
                        END) AS g_deptno,
                        (CASE
                            WHEN e.practice_cocode IS NULL AND e.practice_deptno IS NULL THEN
                                DECODE(
                                    a.cocode, 'A', d.deptnamec,
                                    (SELECT c1.coabbv FROM dcd001$master c1 WHERE c1.cocode = a.cocode) || '-' ||
                                    (SELECT c2.deptnamec FROM dcd002$master c2 WHERE c2.cocode = a.cocode AND c2.deptno = d.deptno AND d.deptno <> '00000')
                                )
                            ELSE
                                DECODE(e.practice_cocode, 'A', '', (SELECT c1.coabbv FROM dcd001$master c1 WHERE c1.cocode = e.practice_cocode) || '-') ||
                                (SELECT c2.deptnamec FROM dcd002$master c2 WHERE c2.cocode = e.practice_cocode AND c2.deptno = e.practice_deptno)
                        END) AS deptnamec,
                        (SELECT COUNT(daily_no) FROM tdr_reply WHERE daily_no = a.daily_no) AS reply_count,
                        (SELECT COUNT(daily_no) FROM tdr_reply WHERE daily_no = a.daily_no AND empno = :empno) AS replier_count,
                        (SELECT CASE WHEN COUNT(*) > 0 THEN 'true' ELSE '' END
                         FROM TDR_REPLY_SPECIAL_COMMENT sc
                         WHERE sc.daily_no = a.daily_no
                         AND sc.empno = a.empno
                         AND sc.doc_date = a.doc_date
                         AND EXISTS (SELECT 1 FROM tdr_reply r WHERE r.daily_no = a.daily_no AND r.empno = :empno AND r.memo NOT LIKE '電子表單%' AND r.memo NOT IN (SELECT memo FROM TDR_REPLY_GENERAL_COMMENT))) AS my_ask,
                        (SELECT CASE WHEN COUNT(*) > 0 THEN 'true' ELSE '' END
                         FROM TDR_REPLY_SPECIAL_COMMENT sc
                         WHERE sc.daily_no = a.daily_no
                         AND sc.empno = a.empno
                         AND sc.doc_date = a.doc_date
                         AND EXISTS (SELECT 1 FROM tdr_reply r WHERE r.daily_no = a.daily_no AND r.empno <> :empno AND r.memo NOT LIKE '電子表單%' AND r.memo NOT IN (SELECT memo FROM TDR_REPLY_GENERAL_COMMENT))) AS other_ask,
                        (SELECT CASE WHEN COUNT(daily_no) > 0 THEN 'true' ELSE 'false' END FROM tdr_msg_send_log WHERE daily_no = a.daily_no AND from_empno = :empno) AS isForwarded,
                        a.LASTDATETIME, e.practice_cocode, f.coabbv,
                        (CASE
                            WHEN :empno IN ('00002','01174','01376','02970','Z0005') THEN 'Y'
                            WHEN LPAD(a.empno, 5, '0') = LPAD(:empno, 5, '0') THEN 'Y'
                            WHEN EXISTS (
                                SELECT 1 FROM groupfoodchn gfc
                                WHERE gfc.cocode = a.cocode
                                  AND LPAD(gfc.empno, 5, '0') = LPAD(a.empno, 5, '0')
                                  AND LPAD(gfc.supervisor, 5, '0') = LPAD(:empno, 5, '0')
                            ) THEN 'Y'
                            ELSE 'N'
                        END) AS can_view_detail
                    FROM tdr_master a
                    LEFT JOIN dcd003$master e ON a.cocode = e.cocode AND a.empno = e.empno
                    LEFT JOIN dcd002$master d ON e.cocode = d.cocode AND e.deptno = d.deptno
                    LEFT JOIN dcd001$master f ON e.cocode = f.cocode
                    WHERE
                        a.status = 'N'
                        AND a.doc_date = :doc_date
                        AND (e.QUITDATE IS NULL OR e.QUITDATE >= a.DOC_DATE)
                        AND (e.RIGHT_STOP_DATE IS NULL OR e.RIGHT_STOP_DATE > a.DOC_DATE)
                        AND a.empno <> '01188'
                        AND (a.cocode, a.empno) IN (
                            SELECT cocode, empno FROM groupfoodchn WHERE supervisor = :empno AND empno NOT IN ('?0002', '?0003') OR :empno IN ('00002','01174','01376','02970','Z0005')
                            UNION ALL
                            SELECT s1.cocode, s1.empno FROM dcd003$master s1 JOIN dcd002$master s2 ON s1.cocode = s2.cocode AND s2.deptno = s1.deptno
                            WHERE s1.cocode = :cocode AND (
                                s1.empno = :empno
                                OR (
                                    ((s1.PRACTICE_COCODE IS NULL OR s1.PRACTICE_DEPTNO IS NULL) AND s1.cocode = :cocode AND (s1.deptno IN (SELECT DISTINCT deptno FROM GROUPDEPTCHN WHERE cocode = 'A' AND (leader=:empno OR pleader=:empno)) OR s1.deptno = :deptno))
                                    OR (s1.PRACTICE_COCODE IS NOT NULL AND s1.PRACTICE_DEPTNO IS NOT NULL AND s1.PRACTICE_COCODE = :cocode AND (s1.PRACTICE_DEPTNO IN (SELECT DISTINCT deptno FROM GROUPDEPTCHN WHERE cocode = 'A' AND (leader=:empno OR pleader=:empno)) OR s1.deptno = :deptno))
                                    OR (s1.PRACTICE_COCODE IS NOT NULL AND s1.PRACTICE_DEPTNO IS NOT NULL AND (s1.PRACTICE_COCODE, s1.PRACTICE_DEPTNO) IN (SELECT practice_cocode, practice_deptno FROM dcd003$master WHERE (cocode, empno) IN ((:cocode, :empno))))
                                )
                            )
                            UNION ALL
                            SELECT e_cocode AS cocode, empno FROM diarysupers WHERE cmark IS NULL AND (VALID_DATE IS NULL OR VALID_DATE > :doc_date) AND supervisor = :empno
                        )
                )
                GROUP BY
                    daily_no, cocode, empno, empnamec, emergency, classify, att_file1,
                    att_file2, att_file3, cust_ename1, cust_ename2, cust_ename3,
                    cust_comp_abbv1, cust_comp_abbv2, cust_comp_abbv3, sop_desc_c,
                    reply_status, memo_status, doc_date, proj_status, openpath,
                    openwebpage, gdeptno, sort_cocode, g_deptno, deptnamec, reply_count,
                    replier_count, my_ask, other_ask, isForwarded, LASTDATETIME,
                    practice_cocode, coabbv, can_view_detail
                ORDER BY
                    sort_cocode,
                    DECODE(SUBSTR(g_deptno, 1, 2), '00', '99', g_deptno),
                    deptnamec,
                    empno,
                    daily_no
            """)

            result = db.execute(main_reports_sql, {
                "empno": empno,
                "doc_date": doc_date,
                "cocode": cocode,
                "deptno": deptno
            })

            reports = []
            for row in result.fetchall():
                report = {
                    "id": int(row[0]),
                    "employee": {
                        "id": str(row[2] or "").zfill(5),
                        "empno": str(row[2] or "").zfill(5),
                        "name": row[3] or "",
                        "department_no": row[23] or "",  # ✅ 修正索引 (新增 can_view_detail 欄位後位移)
                        "department_name": row[24] or "",  # ✅ 修正索引
                        "company_code": row[1] or "",
                    },
                    "date": row[18],
                    "status": "pending" if row[16] != 'Y' else "reviewed",  # ✅ 修正索引
                    "emergency": row[4] or "",
                    "classify": row[5] or "",
                    "sop_desc_c": row[15] or "",
                    "reply_count": row[25] or 0,
                    "replier_count": row[26] or 0,
                    "my_ask": row[27] == 'true',
                    "other_ask": row[28] == 'true',
                    "is_forwarded": row[29] == 'true',
                    "attachments": [f for f in [row[6], row[7], row[8]] if f],
                    "has_attachments": any(f for f in [row[6], row[7], row[8]] if f),
                    "customers": [
                        {"name": row[9], "company": row[12]} if row[9] else None,
                        {"name": row[10], "company": row[13]} if row[10] else None,
                        {"name": row[11], "company": row[14]} if row[11] else None,
                    ],
                    "last_update": row[30] if row[30] else None,
                    "can_view_detail": row[33] == 'Y'  # ✅ 從 SQL 直接取得權限值 (新增的欄位)
                }
                reports.append(report)

            return reports

        except Exception as e:
            logger.error(f"Error getting daily homepage reports: {str(e)}")
            raise

    @staticmethod
    def get_boss_daily_homepage_reports(
        db: Session,
        doc_date: str
    ) -> List[Dict[str, Any]]:
        """取得集團董事長（99988）日報首頁 - 從 tdr_boss_daily 撈取"""
        try:
            sql = text("""
                SELECT
                    daily_no, doc_date, cocode, empno, empnamec, emergency, classify,
                    att_file1, att_file2, att_file3,
                    cust_ename1, cust_ename2, cust_ename3,
                    cust_comp_abbv1, cust_comp_abbv2, cust_comp_abbv3,
                    sop_desc_c, reply_status, memo_status, proj_status,
                    openpath, openwebpage, sort_cocode, g_deptno, deptnamec,
                    reply_count, replier_count, isforwarded,
                    case_reply, case_classify, case_emergency,
                    category_no, deptno, case_forward, lastdatetime,
                    special_sort, general_sort, my_ask, other_ask
                FROM jps.tdr_boss_daily
                WHERE doc_date = :doc_date
                ORDER BY special_sort, general_sort, sort_cocode, g_deptno, deptnamec, empno, daily_no
            """)

            result = db.execute(sql, {"doc_date": doc_date})

            reports = []
            for row in result.fetchall():
                report = {
                    "id": int(row[0]),
                    "employee": {
                        "id": str(row[3] or "").zfill(5),
                        "empno": str(row[3] or "").zfill(5),
                        "name": row[4] or "",
                        "department_no": row[23] or "",
                        "department_name": row[24] or "",
                        "company_code": row[2] or "",
                    },
                    "date": row[1],
                    "status": "pending" if row[17] != 'Y' else "reviewed",
                    "emergency": row[5] or "",
                    "classify": row[6] or "",
                    "sop_desc_c": row[16] or "",
                    "reply_count": int(row[25] or 0),
                    "replier_count": int(row[26] or 0),
                    "my_ask": (row[37] or "") == "true",
                    "other_ask": (row[38] or "") == "true",
                    "is_forwarded": (row[27] or "") == "true",
                    "attachments": [f for f in [row[7], row[8], row[9]] if f],
                    "has_attachments": any(f for f in [row[7], row[8], row[9]] if f),
                    "customers": [
                        {"name": row[10], "company": row[13]} if row[10] else None,
                        {"name": row[11], "company": row[14]} if row[11] else None,
                        {"name": row[12], "company": row[15]} if row[12] else None,
                    ],
                    "last_update": row[34] if row[34] else None,
                    "can_view_detail": True,
                }
                reports.append(report)

            return reports

        except Exception as e:
            logger.error(f"Error getting boss daily homepage reports: {str(e)}")
            raise

    @staticmethod
    def get_report_navigation(
        db: Session,
        current_daily_no: str,
        cocode: str,
        empno: str
    ) -> Dict[str, Optional[int]]:
        """獲取日報的上一篇/下一篇導航信息

        Args:
            db: 資料庫 Session
            current_daily_no: 當前日報編號
            cocode: 公司代碼
            empno: 員工編號

        Returns:
            {"previous_report_id": int|None, "next_report_id": int|None}
        """
        try:
            navigation_sql = text("""
                WITH navigation AS (
                    SELECT
                        daily_no,
                        LAG(daily_no) OVER (ORDER BY doc_date, daily_no) AS prev_id,
                        LEAD(daily_no) OVER (ORDER BY doc_date, daily_no) AS next_id
                    FROM tdr_master
                    WHERE cocode = :cocode
                      AND empno = :empno
                      AND status = 'N'
                      AND leave_hr IS NULL
                )
                SELECT prev_id, next_id
                FROM navigation
                WHERE daily_no = :current_daily_no
            """)

            result = db.execute(navigation_sql, {
                "current_daily_no": current_daily_no,
                "cocode": cocode,
                "empno": empno
            }).fetchone()

            if result:
                return {
                    "previous_report_id": int(result[0]) if result[0] else None,
                    "next_report_id": int(result[1]) if result[1] else None
                }
            return {"previous_report_id": None, "next_report_id": None}

        except Exception as e:
            logger.error(f"Error getting navigation: {str(e)}")
            return {"previous_report_id": None, "next_report_id": None}

    @staticmethod
    def get_forwarded_reports(
        db: Session,
        empno: str,
        doc_date: str
    ) -> List[Dict[str, Any]]:
        """取得被轉寄給登入者的日報 - 這些日報使用者一定有權限查看"""
        try:
            # 查詢被轉寄的日報
            forwarded_sql = text("""
                SELECT daily_no
                     ,reply_nos
                     ,cocode
                     ,empno
                     ,empnamec
                     ,emergency
                     ,classify
                     ,att_file1
                     ,att_file2
                     ,att_file3
                     ,cust_ename1
                     ,cust_ename2
                     ,cust_ename3
                     ,cust_comp_abbv1
                     ,cust_comp_abbv2
                     ,cust_comp_abbv3
                     ,sop_desc_c
                     ,reply_status
                     ,memo_status
                     ,proj_status
                     ,openpath
                     ,openwebpage
                     ,sort_cocode
                     ,g_deptno
                     ,deptnamec
                     ,practice_cocode
                     ,coabbv
                     ,my_ask
                     ,other_ask
                     ,doc_date
                     ,reply_count
                     ,replier_count
                     ,LASTDATETIME
                 FROM (
                        SELECT a.daily_no
                    ,b.reply_nos
                    ,a.cocode
                    ,a.empno
                    ,a.empnamec
                    ,a.emergency
                    ,a.classify
                    ,a.att_file1
                    ,a.att_file2
                    ,a.att_file3
                    ,a.cust_ename1
                    ,a.cust_ename2
                    ,a.cust_ename3
                    ,a.cust_comp_abbv1
                    ,a.cust_comp_abbv2
                    ,a.cust_comp_abbv3
                    ,a.sop_desc_c
                    ,a.reply_status
                    ,a.memo_status
                    ,a.proj_status
                    ,a.openpath
                    ,a.openwebpage
                    ,d.g_deptno AS gdeptno
                    ,DECODE(NVL(e.practice_cocode, a.cocode), N'J10', N'J071', N'J17', N'J072', NVL(e.practice_cocode, a.cocode)) AS sort_cocode
                    ,(
                        CASE
                            WHEN e.practice_cocode IS NULL
                                AND e.practice_deptno IS NULL
                                THEN d.g_deptno
                            ELSE (
                                    SELECT g_deptno
                                    FROM dcd002$master g
                                    WHERE g.cocode = e.practice_cocode
                                        AND g.deptno = e.practice_deptno
                                    )
                            END
                        ) AS g_deptno
                    ,(
                        CASE
                            WHEN e.practice_cocode IS NULL
                                AND e.practice_deptno IS NULL
                                THEN DECODE(a.cocode, 'A', d.deptnamec, (
                                            SELECT c1.coabbv
                                            FROM dcd001$master c1
                                            WHERE c1.cocode = a.cocode
                                            ) || '-' || (
                                            SELECT c2.deptnamec
                                            FROM dcd002$master c2
                                            WHERE c2.cocode = a.cocode
                                                AND c2.deptno = d.deptno
                                                AND d.deptno <> '00000'
                                            ))
                            ELSE DECODE(e.practice_cocode, 'A', '', (
                                        SELECT c1.coabbv
                                        FROM dcd001$master c1
                                        WHERE c1.cocode = e.practice_cocode
                                        ) || '-') || (
                                    SELECT c2.deptnamec
                                    FROM dcd002$master c2
                                    WHERE c2.cocode = e.practice_cocode
                                        AND c2.deptno = e.practice_deptno
                                    )
                            END
                        ) AS deptnamec
                    ,e.practice_cocode
                    ,f.coabbv
                    ,(SELECT case when COUNT(daily_no) > 0 then 'true' else '' end AS cnt FROM tdr_reply WHERE daily_no = a.daily_no AND empno = :empno and memo not like '電子表單%' and memo not in (select memo from TDR_REPLY_GENERAL_COMMENT)) as my_ask
                    ,(SELECT case when COUNT(daily_no) > 0 then 'true' else '' end AS cnt FROM tdr_reply WHERE daily_no = a.daily_no AND empno <> :empno and memo not like '電子表單%' and memo not in (select memo from TDR_REPLY_GENERAL_COMMENT)) as other_ask
                    ,a.doc_date
                    ,(SELECT COUNT(daily_no) FROM tdr_reply WHERE daily_no = a.daily_no) AS reply_count
                    ,(SELECT COUNT(daily_no) FROM tdr_reply WHERE daily_no = a.daily_no AND empno = :empno) AS replier_count
                    ,a.LASTDATETIME
                    FROM tdr_master a
                    LEFT JOIN dcd003$master e ON a.cocode = e.cocode
                    AND a.empno = e.empno
                    LEFT JOIN dcd002$master d ON e.cocode = d.cocode
                    AND e.deptno = d.deptno
                    LEFT JOIN dcd001$master f ON e.cocode = f.cocode
                    JOIN tdr_msg_send_log b ON b.daily_no = a.daily_no
                    WHERE a.status = 'N'
                    AND a.cocode IN ( select cocode from dcd001$master where eip_active = 'Y')
                    AND a.doc_date = :doc_date
                    AND b.to_empno = :empno
                    AND (e.RIGHT_STOP_DATE is null or e.RIGHT_STOP_DATE > a.doc_date)
                  )
                 GROUP BY daily_no
                     ,reply_nos
                     ,cocode
                     ,empno
                     ,empnamec
                     ,emergency
                     ,classify
                     ,att_file1
                     ,att_file2
                     ,att_file3
                     ,cust_ename1
                     ,cust_ename2
                     ,cust_ename3
                     ,cust_comp_abbv1
                     ,cust_comp_abbv2
                     ,cust_comp_abbv3
                     ,sop_desc_c
                     ,reply_status
                     ,memo_status
                     ,proj_status
                     ,openpath
                     ,openwebpage
                     ,sort_cocode
                     ,g_deptno
                     ,deptnamec
                     ,gdeptno
                     ,practice_cocode
                     ,coabbv
                     ,my_ask
                     ,other_ask
                     ,doc_date
                     ,reply_count
                     ,replier_count
                     ,LASTDATETIME
                 ORDER BY sort_cocode
                     ,DECODE(SUBSTR(gdeptno, 1, 2), '00', '99', gdeptno)
                     ,deptnamec
                     ,empno
                     ,daily_no
            """)

            result = db.execute(forwarded_sql, {
                "empno": empno,
                "doc_date": doc_date
            })

            reports = []
            for row in result.fetchall():
                report = {
                    "id": int(row[0]),
                    "employee": {
                        "id": str(row[3] or "").zfill(5),
                        "empno": str(row[3] or "").zfill(5),
                        "name": row[4] or "",
                        "department_no": row[23] or "",
                        "department_name": row[24] or "",
                        "company_code": row[2] or "",
                    },
                    "date": row[29],
                    "status": "pending" if row[18] != 'Y' else "reviewed",
                    "emergency": row[5] or "",
                    "classify": row[6] or "",
                    "sop_desc_c": row[16] or "",
                    "reply_count": row[30] or 0,
                    "replier_count": row[31] or 0,
                    "my_ask": row[27] == 'true',
                    "other_ask": row[28] == 'true',
                    "is_forwarded": True,  # 轉寄的日報固定為 True
                    "attachments": [f for f in [row[7], row[8], row[9]] if f],
                    "has_attachments": any(f for f in [row[7], row[8], row[9]] if f),
                    "customers": [
                        {"name": row[10], "company": row[13]} if row[10] else None,
                        {"name": row[11], "company": row[14]} if row[11] else None,
                        {"name": row[12], "company": row[15]} if row[12] else None,
                    ],
                    "last_update": row[32] if row[32] else None,
                    "can_view_detail": True  # ✅ 轉寄的日報一定可以查看
                }
                reports.append(report)

            return reports

        except Exception as e:
            logger.error(f"Error getting forwarded reports: {str(e)}")
            raise

    # ✅ 已移除 check_view_permission_for_detail - 權限檢查已整合到 SQL 中
    # ✅ 已移除 check_supervision_status - 前端未使用此功能
