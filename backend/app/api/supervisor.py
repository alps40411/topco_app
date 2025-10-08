# backend/app/api/supervisor.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Any
import logging
import os
from pathlib import Path
from datetime import datetime


from app.core.legacy_database import get_legacy_db
from app.core.deps import get_current_user
from app.schemas.user import User
from app.core.config import settings

router = APIRouter(tags=["Supervisor"])
logger = logging.getLogger(__name__)

@router.get("/has-subordinates")
async def check_has_subordinates(
    current_user: User = Depends(get_current_user)
):
    """檢查當前用戶是否有下屬 - 使用 JPS Legacy 資料庫"""
    try:
        if not current_user.employee:
            return {"has_subordinates": False}
        
        # 取得 legacy 資料庫連接
        legacy_db_gen = get_legacy_db()
        legacy_db = next(legacy_db_gen)
        
        # 從 JPS 查詢是否有下屬（使用 groupfoodchn 表）
        subordinates_sql = text("""
            SELECT COUNT(*) as subordinate_count
            FROM jps.groupfoodchn 
            WHERE supervisor = :empno AND cocode = 'A'
        """)
        
        result = legacy_db.execute(subordinates_sql, {"empno": current_user.employee.empno})
        row = result.fetchone()
        
        has_subordinates = row[0] > 0 if row else False
        return {"has_subordinates": has_subordinates}
        
    except Exception as e:
        logger.error(f"Error checking subordinates: {str(e)}")
        return {"has_subordinates": False}


@router.get("/reports/{daily_no}/approvals")
async def get_daily_report_approvals(
    daily_no: str,
    current_user: User = Depends(get_current_user),
    legacy_db: Session = Depends(get_legacy_db)
):
    """取得日報審核資訊 - 返回前端期望的 SupervisorApprovalInfo[] 格式"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="該用戶不是員工")
        
        # 查詢可能的審核主管清單（基於該員工的上級關係）
        # 先查詢日報的員工資訊
        employee_sql = text("""
            SELECT d.empno, d.empnamec
            FROM jps.tdr_master d
            WHERE d.daily_no = :daily_no
        """)
        
        emp_result = legacy_db.execute(employee_sql, {"daily_no": daily_no})
        emp_row = emp_result.fetchone()
        
        if not emp_row:
            raise HTTPException(status_code=404, detail="找不到指定的日報")
        
        # 查詢該員工的上級主管列表
        supervisor_sql = text("""
            SELECT DISTINCT g.supervisor, e.empnamec
            FROM jps.groupfoodchn g
            LEFT JOIN jps.dcd003$master e ON g.supervisor = e.empno
            WHERE g.empno = :empno AND g.cocode = 'A'
              AND e.quitdate IS NULL
        """)
        
        sup_result = legacy_db.execute(supervisor_sql, {"empno": emp_row[0]})
        supervisors = sup_result.fetchall()
        
        # 查詢回覆和評分資訊，用來判斷審核狀態
        reply_sql = text("""
            SELECT r.empno, r.memo, r.xdate, r.xtime,
                   e.empnamec as supervisor_name
            FROM jps.tdr_reply r
            LEFT JOIN jps.dcd003$master e ON r.empno = e.empno
            WHERE r.daily_no = :daily_no
        """)
        
        reply_result = legacy_db.execute(reply_sql, {"daily_no": daily_no})
        replies_dict = {}
        for reply_row in reply_result.fetchall():
            empno = reply_row[0]
            if empno not in replies_dict:
                replies_dict[empno] = {
                    "feedback": reply_row[1],
                    "approved_at": f"{reply_row[2]} {reply_row[3]}",
                    "supervisor_name": reply_row[4] or "主管"
                }
        
        # 查詢評分資訊
        score_sql = text("""
            SELECT s.reply_empno, s.score, s.xdate, s.xtime,
                   e.empnamec as supervisor_name
            FROM jps.tdr_score s
            LEFT JOIN jps.dcd003$master e ON s.reply_empno = e.empno
            WHERE s.daily_no = :daily_no
        """)
        
        score_result = legacy_db.execute(score_sql, {"daily_no": daily_no})
        scores_dict = {}
        for score_row in score_result.fetchall():
            empno = score_row[0]
            scores_dict[empno] = {
                "rating": score_row[1],
                "approved_at": f"{score_row[2]} {score_row[3]}",
                "supervisor_name": score_row[4] or "主管"
            }
        
        # 建構 SupervisorApprovalInfo 列表
        approvals = []
        for sup_row in supervisors:
            supervisor_empno = sup_row[0]
            supervisor_name = sup_row[1] or "主管"
            
            # 檢查是否有回覆或評分來判斷狀態
            has_reply = supervisor_empno in replies_dict
            has_score = supervisor_empno in scores_dict
            
            approval_info = {
                "supervisor_id": int(supervisor_empno) if supervisor_empno.isdigit() else 0,
                "supervisor_name": supervisor_name,
                "supervisor_empno": supervisor_empno,
                "status": "approved" if (has_reply or has_score) else "pending"
            }
            
            # 添加評分和回饋資訊
            if has_score:
                score_info = scores_dict[supervisor_empno]
                approval_info["rating"] = score_info.get("rating")
                approval_info["approved_at"] = score_info.get("approved_at")
            
            if has_reply:
                reply_info = replies_dict[supervisor_empno]
                approval_info["feedback"] = reply_info.get("feedback")
                if not approval_info.get("approved_at"):
                    approval_info["approved_at"] = reply_info.get("approved_at")
            
            approvals.append(approval_info)
        
        return approvals
        
    except Exception as e:
        logger.error(f"Error getting daily report approvals: {str(e)}")
        raise HTTPException(status_code=500, detail="取得日報審核資訊失敗")

@router.get("/forward/candidates")
async def get_forward_candidates(
    current_user: User = Depends(get_current_user)
):
    """取得轉寄名單 - 根據用戶 adm_rank 權限決定"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="該用戶不是員工")

        db = next(get_legacy_db())
        
        # 查詢當前用戶的 adm_rank
        user_rank_sql = text("""
            SELECT adm_rank FROM jps.dcd003$master 
            WHERE empno = :empno AND cocode = :cocode
        """)
        rank_result = db.execute(user_rank_sql, {
            "empno": current_user.employee.empno,
            "cocode": current_user.employee.cocode
        })
        rank_row = rank_result.fetchone()
        
        if not rank_row:
            raise HTTPException(status_code=404, detail="找不到用戶資料")
        
        adm_rank = int(rank_row[0]) if rank_row[0] else 99
        candidates = []
        
        # 基礎職稱轉寄名單（所有人都能用）
        title_sql = text("""
            SELECT a.empno, a.empname, 'title' AS type
            FROM tdr_forward_visor a 
            left join dcd003$master b on a.empno = b.empno and b.estatus<> '3' 
            and (b.RIGHT_STOP_DATE is not null AND b.RIGHT_STOP_DATE <= TO_CHAR(sysdate, 'yyyyMMdd')) and cocode in (select cocode from dcd001$master where eip_active = 'Y') ORDER BY a.sorting
        """)
        title_rows = db.execute(title_sql).fetchall()
        candidates.extend([{"empno": r[0], "empname": r[1], "type": r[2]} for r in title_rows])
        
        # 如果 adm_rank <= 5，增加部門轉寄選項
        if adm_rank <= 5:
            dept_sql = text("""
                SELECT t.*,
                    (CASE
                        WHEN t.cocode = 'G' THEN 'ZG'
                        WHEN t.cocode = 'G01' THEN 'ZG01'
                        WHEN t.cocode = 'J09' THEN 'J009'
                        ELSE t.cocode
                    END) AS sort_cocode,
                    (CASE
                        WHEN sort_order IS NULL THEN '99999'
                        ELSE sort_order
                    END) AS sort_customize,
                    (CASE
                        WHEN t.cocode = 'H' AND g_deptno = '00A00' THEN '0'
                        WHEN t.cocode = 'J07' AND g_deptno = '00010' THEN '0'
                        WHEN t.cocode = 'J10' AND g_deptno = '00010' THEN '0'
                        WHEN t.cocode = 'J17' AND g_deptno = '03000' THEN '0'
                        WHEN t.cocode = 'M' AND g_deptno = '00000' THEN '0'
                        WHEN t.cocode = 'P' AND g_deptno = '00010' THEN '0'
                        WHEN t.cocode = 'T' AND g_deptno = 'S0000' THEN '0'
                        WHEN t.cocode = 'X' AND g_deptno = '05000' THEN '0'
                        ELSE '1'
                    END) AS sort_gmDept,
                    (CASE
                        WHEN t.sbu = 1 AND t.cocode = 'T' THEN SUBSTR(t.g_deptno, 1, 3) || '00'
                        WHEN t.sbu = 1 AND t.cocode = 'A' AND SUBSTR(t.g_deptno, 1, 2) = '00' THEN '99' || SUBSTR(t.g_deptno, 3, 3)
                        WHEN t.sbu = 1 AND t.cocode = 'A' THEN SUBSTR(t.g_deptno, 1, 2) || '000'
                        WHEN t.sbu = 2 AND t.cocode = 'A' AND t.g_deptno = '00521' THEN t.g_deptno
                        WHEN t.sbu = 2 AND t.cocode = 'A' AND (
                            t.g_deptno NOT LIKE '00G7%' AND t.g_deptno NOT LIKE '00G1%' AND 
                            t.g_deptno NOT LIKE '00G3%' AND t.g_deptno NOT LIKE '00B4%'
                        ) THEN SUBSTR(t.g_deptno, 1, 4) || '0'
                        ELSE t.g_deptno
                    END) AS g_deptno1
                FROM (
                    SELECT
                        (CASE
                            WHEN b.cocode = '003' AND (b.deptno = '00000' OR b.deptno = '00281') THEN 'A'
                            WHEN b.practice_cocode IS NULL THEN b.cocode
                            WHEN b.practice_cocode <> b.cocode THEN b.cocode
                            ELSE b.practice_cocode
                        END) AS cocode,
                        a.empno, b.empnamec,
                        (CASE
                            WHEN b.practice_cocode IS NULL THEN b.deptno
                            WHEN b.practice_cocode <> b.cocode THEN b.deptno
                            ELSE b.practice_deptno
                        END) AS deptno,
                        (CASE
                            WHEN f.duty IS NULL THEN '其他'
                            ELSE f.duty
                        END) AS dutyscript,
                        c.sbu, d.coabbv,
                        (CASE
                            WHEN c.sbu = 2 AND c.cocode = 'A' AND c.g_deptno LIKE '00A2%' THEN '資訊處'
                            WHEN c.sbu = 2 AND c.cocode = 'A' AND c.g_deptno LIKE '00B3%' THEN '資材處'
                            ELSE c.deptabbv
                        END) AS deptabbv,
                        (CASE
                            WHEN b.cocode = '003' AND (b.deptno = '00000' OR b.deptno = '00281') THEN '00G10'
                            ELSE c.g_deptno
                        END) AS g_deptno,
                        b.dclass, b.adm_rank, g.sort_order
                    FROM jps.TDR_FORWARDLIST a
                    JOIN jps.DCD003$MASTER b ON a.cocode = b.cocode AND a.empno = b.empno
                    JOIN jps.DCD002$MASTER c ON a.cocode = c.cocode AND b.deptno = c.deptno
                    JOIN jps.DCD001$MASTER d ON a.cocode = d.cocode
                    LEFT JOIN jps.DCD004$MASTER e ON a.cocode = e.cocode AND b.dutyno = e.dutyno AND e.ducode = 'O'
                    LEFT JOIN jps.tdr_forward_duty f ON e.dutyname = f.dutyname
                    LEFT JOIN jps.tdr_forward_dept_sort g ON d.cocode = g.cocode AND c.g_deptno = g.deptno
                    WHERE b.quitdate IS NULL
                      AND (b.right_stop_date IS NULL OR b.right_stop_date > TO_CHAR(sysdate, 'YYYYMMDD'))
                ) t
                ORDER BY sort_cocode, sort_customize, sort_gmDept, sbu, g_deptno1, dclass DESC, adm_rank
            """)
            dept_rows = db.execute(dept_sql).fetchall()
            candidates.extend([{
                "empno": r[1], 
                "empname": r[2], 
                "type": "department",
                "cocode": r[0],
                "deptabbv": r[6],
                "dutyscript": r[4]
            } for r in dept_rows])
        
        return {
            "user_adm_rank": adm_rank,
            "candidates": candidates
        }
        
    except Exception as e:
        logger.error(f"Error get_forward_candidates: {e}")
        raise HTTPException(status_code=500, detail="取得轉寄名單失敗")


# my-reports-by-date API已移除，因為已廢除「我的日報」功能

@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """取得單一日報詳情"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="該用戶不是員工")
        
        legacy_db = next(get_legacy_db())
        
        # 查詢 master 基本資訊
        master_sql = text("""
            SELECT daily_no, empno, sop_desc_c, empnamec,
                   xdate, xtime, status, doc_date
            FROM jps.tdr_master
            WHERE daily_no = :daily_no
        """)
        
        master_result = legacy_db.execute(master_sql, {"daily_no": report_id})
        master_row = master_result.fetchone()
        
        if not master_row:
            raise HTTPException(status_code=404, detail="找不到指定的日報")
        
        # 查詢員工資訊，包含中文部門名稱
        employee_sql = text("""
            SELECT e.empno, e.empnamec, e.cocode, e.deptno, d.deptnamec
            FROM jps."dcd003$master" e
            LEFT JOIN jps."dcd002$master" d ON e.cocode = d.cocode AND e.deptno = d.deptno
            WHERE e.empno = :empno
        """)
        emp_result = legacy_db.execute(employee_sql, {"empno": master_row[1]})
        emp_row = emp_result.fetchone()
        
        # 查詢詳細內容（按照您提供的標準查詢）
        details_sql = text("""
            SELECT a.cuno1, b.daily_sub_nos, b.sopno, b.sop_code, b.prod_cate,
                   b.itemdesc1, b.exetime, b.estimate, b.attitude, b.memo_collect,
                   b.cuno_subj, b.cuno_msg, b.cuno_collect, b.comp_inf, b.comp_desc,
                   b.comp_collect, b.ques_subj, b.ques_desc, b.solut_subj, b.solut_desc,
                   b.solut_status, b.att_file3, b.xuser, b.xdate, b.xtime,
                   b.empname1, b.empname2, b.empname3, b.prod_no, b.create_msg,
                   b.comp_serno, b.cuno_comp_serno, b.cocode, b.empno, b.status,
                   b.planno, b.memo, b.empname4, b.empname5, b.cuno_infcont,
                   b.comp_infcont, b.ques_infcont, b.solut_infcont, b.finish_rate,
                   b.pps_cocode, b.pps_empno, b.pps_deptno, b.pps_empnamec,
                   b.ship_log, b.cuno_msg1, b.ques_desc1, b.solut_desc1, b.memo1,
                   b.cuno_msg2, b.ques_desc2, b.solut_desc2, b.memo2, b.reply,
                   b.pps_servecocode, b.projno, b.proj_cocode, b.memo_collect
            FROM jps.tdr_detail1 a
            JOIN jps.tdr_detail2 b ON b.daily_no = a.daily_no AND b.daily_sub_nos = a.daily_sub_nos
            WHERE a.daily_no = :daily_no
            ORDER BY a.daily_sub_nos, b.daily_job_nos
        """)
        
        details_result = legacy_db.execute(details_sql, {"daily_no": report_id})
        
        # 處理詳細內容
        consolidated_content = []
        for detail_row in details_result.fetchall():
            # 處理 sop_code 可能包含多個工作項目的情況（如 "1/2"）
            sop_code_str = str(detail_row[3]) if detail_row[3] else ""
            work_items = []
            
            if sop_code_str and '/' in sop_code_str:
                # 分割多個工作項目序號（如 "1/2" -> ["1", "2"]）
                work_item_seqs = sop_code_str.split('/')
                
                # 為每個序號查找中文名稱，使用現有的 legacy_db 連接
                for seq in work_item_seqs:
                    seq = seq.strip()
                    if seq and seq.isdigit():  # 只處理數字序號
                        work_item_sql = text("SELECT name FROM jps.tpm_sop_detail WHERE sopno = :sopno AND seq = :seq")
                        work_item_result = legacy_db.execute(work_item_sql, {
                            "sopno": str(detail_row[2]),  # sopno
                            "seq": seq
                        })
                        work_item_row = work_item_result.fetchone()
                        if work_item_row and work_item_row[0]:
                            try:
                                test_name = str(work_item_row[0])
                                # 如果有正常中文字符則使用
                                if any('\u4e00' <= c <= '\u9fff' for c in test_name) and '�' not in test_name:
                                    work_items.append(test_name)
                                else:
                                    work_items.append(f"工作項目{seq}")
                            except:
                                work_items.append(f"工作項目{seq}")
                        else:
                            work_items.append(f"工作項目{seq}")
                    else:
                        # 非數字序號，直接使用
                        work_items.append(seq)
                
                work_item_display = " / ".join(work_items) if work_items else sop_code_str
            else:
                # 單一工作項目或無工作項目
                if sop_code_str and sop_code_str.isdigit():
                    # 如果是數字序號，嘗試查詢中文名稱
                    work_item_sql = text("SELECT name FROM jps.tpm_sop_detail WHERE sopno = :sopno AND seq = :seq")
                    work_item_result = legacy_db.execute(work_item_sql, {
                        "sopno": str(detail_row[2]),  # sopno
                        "seq": sop_code_str
                    })
                    work_item_row = work_item_result.fetchone()
                    if work_item_row and work_item_row[0]:
                        try:
                            test_name = str(work_item_row[0])
                            if any('\u4e00' <= c <= '\u9fff' for c in test_name) and '' not in test_name:
                                work_item_display = test_name
                            else:
                                work_item_display = f"工作項目{sop_code_str}"
                        except:
                            work_item_display = f"工作項目{sop_code_str}"
                    else:
                        work_item_display = f"工作項目{sop_code_str}"
                else:
                    # 非數字序號，直接使用
                    work_item_display = sop_code_str or ""
            
            # 查詢執行工作的中文名稱
            execution_work_name_c = ""
            if detail_row[2]:  # sopno
                exec_work_sql = text("SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno")
                exec_work_result = legacy_db.execute(exec_work_sql, {"sopno": str(detail_row[2])})
                exec_work_row = exec_work_result.fetchone()
                if exec_work_row:
                    execution_work_name_c = exec_work_row[0]
            
            # 處理工作計畫名稱，如果有編碼問題則使用預設值
            plan_name = "基本工作項目"  # 初始化預設值

            if detail_row[35]:
                try:
                    plan_sql = text("SELECT plan_subj_c FROM jps.tjp_master WHERE planno = :planno")
                    plan_result = legacy_db.execute(plan_sql, {"planno": detail_row[35]}).fetchone()
                    # 檢查中文字是否正常顯示
                    test_str = str(plan_result[0])
                    # 如果包含亂碼字符則使用預設值
                    if not any(c in test_str for c in ['？', '�', '?']) and len(test_str) > 0:
                        plan_name = test_str
                    else:
                        plan_name = "基本工作項目"
                except:
                    plan_name = "基本工作項目"
            
            # 查詢該 daily_sub_nos 對應的檔案
            daily_sub_nos = detail_row[1]  # daily_sub_nos
            cocode = detail_row[32]  # cocode - 修正索引
            empno = detail_row[33]  # empno - 修正索引
            doc_date = master_row[7]  # doc_date 來自 master (原始日報日期，不是 xdate)
            
            # 調試日誌
            logger.info(f"檔案查詢參數: daily_sub_nos={daily_sub_nos}, cocode={cocode}, empno={empno}, doc_date={doc_date}")
            logger.info(f"Master row indices: master_row[7]={master_row[7] if len(master_row) > 7 else 'INDEX_ERROR'}")
            logger.info(f"Detail row indices: detail_row[32]={detail_row[32] if len(detail_row) > 32 else 'INDEX_ERROR'}, detail_row[33]={detail_row[33] if len(detail_row) > 33 else 'INDEX_ERROR'}")
            
            # 計算檔案 ID 範圍，避免整數溢位
            daily_no_int = int(report_id)
            daily_sub_nos_int = int(daily_sub_nos) if daily_sub_nos else 1
            
            # 使用字符串格式計算，避免 Python 整數溢位
            id_start = daily_no_int * 1000000 + daily_sub_nos_int * 1000
            id_end = daily_no_int * 1000000 + (daily_sub_nos_int + 1) * 1000 - 1
            
            logger.info(f"檔案 ID 範圍: {id_start} - {id_end}")
            
            files_sql = text("""
                SELECT filepath, filename
                FROM jps.tdr_upload_file
                WHERE id >= CAST(:id_start AS BIGINT) AND id <= CAST(:id_end AS BIGINT)
                  AND (:cocode IS NULL OR cocode = :cocode)
                  AND (:empno IS NULL OR empno = :empno)
                  AND docdate = :doc_date
                  AND status = 'Online'
                ORDER BY id
            """)
            
            files_result = legacy_db.execute(files_sql, {
                "id_start": id_start,
                "id_end": id_end,
                "cocode": cocode,
                "empno": empno,
                "doc_date": doc_date
            })

            files = []
            file_index = 1
            file_rows = files_result.fetchall()
            logger.info(f"Files query result: found {len(file_rows)} files for daily_sub_nos={daily_sub_nos}")
            for file_row in file_rows:
                file_id = daily_no_int * 1000000 + daily_sub_nos_int * 1000 + file_index
                # 根據檔案副檔名判斷類型
                filename = file_row[1] or ""
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ""
                if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                    file_type = f"image/{file_ext}"
                else:
                    file_type = "application/octet-stream"
                
                files.append({
                    "id": file_id,
                    "name": filename,
                    "type": file_type,
                    "size": 0,  # 檔案大小暫時設為 0，因為資料庫中沒有這個欄位
                    "url": f"/api/supervisor/files/download/{file_id}",  # 檔案下載 URL
                    "filepath": file_row[0]  # 保留原始路徑供後端使用
                })
                file_index += 1

            # 構建服務公司和對象資訊
            service_cocode = detail_row[58] or ""  # pps_servecocode - 服務公司別
            service_empno = detail_row[45] or ""   # pps_empno - 服務對象工號
            service_empnamec = detail_row[47] or "" # pps_empnamec - 服務對象姓名

            # 查詢服務公司中文名稱
            service_company_name = service_cocode
            if service_cocode:
                company_sql = text("""
                    SELECT coabbv FROM jps.dcd001$master
                    WHERE cocode = :cocode AND eip_active = 'Y'
                """)
                company_result = legacy_db.execute(company_sql, {"cocode": service_cocode}).fetchone()
                if company_result:
                    service_company_name = company_result[0]

            # 構建服務對象名稱
            service_target_name = ""
            if service_empnamec and service_empno:
                service_target_name = f"{service_empnamec}"

            content_item = {
                "project": {
                    "plan_subj_c": plan_name,  # 處理後的工作計畫中文名稱
                    "planno": detail_row[35] or ""  # planno
                },
                "content": detail_row[36] or "",  # memo - 工作內容
                "execution_work_name": execution_work_name_c or detail_row[62] or f"執行工作 {detail_row[2] or ''}",  # 中文執行工作名稱
                "work_item_name": work_item_display,  # 處理後的工作項目名稱
                "service_company_name": service_company_name,  # 服務公司
                "service_target_name": service_target_name,  # 服務對象
                "total_execution_time_minutes": float(detail_row[6] or 0),  # exetime - 執行時間
                "daily_sub_nos": detail_row[1],  # daily_sub_nos
                "prod_cate": detail_row[4] or "",  # prod_cate
                "estimate": detail_row[7] or "",  # estimate
                "attitude": detail_row[8] or "",  # attitude
                "finish_rate": detail_row[39] or 0,  # finish_rate
                "cuno_subj": detail_row[10] or "",  # cuno_subj
                "cuno_msg": detail_row[11] or "",  # cuno_msg
                "comp_desc": detail_row[14] or "",  # comp_desc
                "ques_desc": detail_row[17] or "",  # ques_desc
                "solut_desc": detail_row[19] or "",  # solut_desc
                "files": files  # 新增檔案列表
            }
            consolidated_content.append(content_item)
        
        return {
            "id": int(report_id),
            "employee": {
                "id": str(master_row[1] or "").zfill(5),  # empno 保持字串格式並補齊5位數
                "empno": str(master_row[1] or "").zfill(5),  # 新增empno欄位
                "name": master_row[3] or (emp_row[1] if emp_row else "未知"),  # empnamec
                "department_no": emp_row[3] if emp_row else "",  # deptno
                "department_name": emp_row[4] if emp_row else ""  # deptnamec
            },
            "date": master_row[7],  # doc_date
            "status": "submitted",
            "consolidated_content": consolidated_content if consolidated_content else [{
                "project": {
                    "plan_subj_c": master_row[2] or "基本工作項目"  # sop_desc_c
                },
                "content": "已提交的日報",
                "execution_work_name": "",
                "work_item_name": "",
                "total_execution_time_minutes": 0
            }],
            "rating": 0
        }
        
    except Exception as e:
        logger.error(f"Error getting report detail: {str(e)}")
        raise HTTPException(status_code=500, detail="取得日報詳情失敗")
        
        

@router.post("/reports/{report_id}/ai-suggestions")
async def get_ai_suggestions(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """生成 AI 建議"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="該用戶不是員工")
        
        # 取得 legacy 資料庫連接
        legacy_db_gen = get_legacy_db()
        legacy_db = next(legacy_db_gen)
        
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
        
        report_results = legacy_db.execute(report_sql, {"daily_no": report_id}).fetchall()
        
        if not report_results:
            raise HTTPException(status_code=404, detail="找不到該日報")
        
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
        
        if not report_content.strip():
            # 如果沒有具體內容，返回通用建議
            from app.services.ai_suggestion_service import _get_fallback_suggestions
            suggestions = _get_fallback_suggestions()
        else:
            # 使用 AI 服務生成建議
            from app.services.ai_suggestion_service import generate_supervisor_reply_suggestions
            suggestions = await generate_supervisor_reply_suggestions(
                report_content=report_content,
                employee_name=employee_name
            )
        
        return {"suggestions": suggestions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail="生成 AI 建議失敗")

# 舊的提交端點已移除，請使用 /api/legacy/upload-daily-report 端點

@router.get("/daily-homepage")
async def get_daily_homepage_reports(
    date: str = Query(..., description="查詢日期 (YYYY-MM-DD)"),
    empno: str = Query(None, description="測試用工號，若未提供則使用當前用戶"),
    current_user: User = Depends(get_current_user)
):
    """新的日報首頁 - 取得登入者可能看到的所有日報列表"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="該用戶不是員工")
        
        legacy_db_gen = get_legacy_db()
        legacy_db = next(legacy_db_gen)
        
        doc_date = date.replace("-", "")
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or 'A'
        deptno = current_user.employee.deptno or ''
        print(doc_date, empno, cocode, deptno)
        # 使用用戶提供的完整正確查詢 - 轉換為PostgreSQL語法
        main_reports_sql = text("""
                        SELECT
                daily_no, cocode, empno, empnamec, emergency, classify, att_file1,
                att_file2, att_file3, cust_ename1, cust_ename2, cust_ename3,
                cust_comp_abbv1, cust_comp_abbv2, cust_comp_abbv3, sop_desc_c,
                reply_status, memo_status, doc_date, proj_status, openpath,
                openwebpage, sort_cocode, g_deptno, deptnamec, reply_count,
                replier_count, my_ask, other_ask, isForwarded, LASTDATETIME,
                practice_cocode, coabbv
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
                    a.LASTDATETIME, e.practice_cocode, f.coabbv
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
                practice_cocode, coabbv
            ORDER BY
                sort_cocode,
                DECODE(SUBSTR(g_deptno, 1, 2), '00', '99', g_deptno),
                deptnamec,
                empno,
                daily_no
        """)
        
        result = legacy_db.execute(main_reports_sql, {
            "empno": empno,
            "doc_date": doc_date,
            "cocode": cocode,
            "deptno": deptno
        })
        
        reports = []
        for row in result.fetchall():
            # 基本日報資訊
            report = {
                "id": int(row[0]),  # daily_no
                "employee": {
                    "id": str(row[2] or "").zfill(5),  # empno 保持字串格式並補齊5位數
                    "empno": str(row[2] or "").zfill(5),  # 新增empno欄位
                    "name": row[3] or "",  # empnamec
                    "department_no": row[22] or "",  # g_deptno
                    "department_name": row[23] or "",  # deptnamec
                    "company_code": row[1] or "",  # cocode
                },
                "date": row[18],  # doc_date
                "status": "pending" if row[15] != 'Y' else "reviewed",  # reply_status
                "emergency": row[4] or "",  # emergency
                "classify": row[5] or "",  # classify
                "sop_desc_c": row[15] or "",  # sop_desc_c
                "reply_count": row[25] or 0,  # reply_count
                "replier_count": row[26] or 0,  # replier_count"
                "my_ask": row[27] == 'true',  # my_ask
                "other_ask": row[28] == 'true',  # other_ask
                "is_forwarded": row[29] == 'true',  # isForwarded
                "attachments": [f for f in [row[6], row[7], row[8]] if f],  # att_file1-3
                "has_attachments": any(f for f in [row[6], row[7], row[8]] if f),  # 判斷是否有附件
                "customers": [
                    {"name": row[9], "company": row[12]} if row[9] else None,  # cust_ename1, cust_comp_abbv1
                    {"name": row[10], "company": row[13]} if row[10] else None,  # cust_ename2, cust_comp_abbv2
                    {"name": row[11], "company": row[14]} if row[11] else None,  # cust_ename3, cust_comp_abbv3
                ],
                "last_update": row[30] if row[30] else None,  # LASTDATETIME

                # 新增字段 - 權限相關
                "can_view_detail": False,  # 稍後會通過權限檢查更新
                "supervision_status": "no_permission"  # pending, approved, no_permission
            }
            reports.append(report)
        print(f"Fetched {len(reports)} reports for user {empno} on date {doc_date}")
        # 為每個報告執行權限檢查並更新權限標記
        for report in reports:
            report_empno = str(report["employee"]["id"])
            report_cocode = report["employee"]["company_code"]
            
            # 詳情查看權限檢查：使用四項權限檢查
            can_view_detail = await _check_view_permission_for_detail(legacy_db, empno, report_empno, report_cocode)
            report["can_view_detail"] = can_view_detail
            
            # 檢查主管審核狀態 - 簡化版本，避免複雜的子查詢
            if report_empno == empno:
                # 自己的日報不能審核
                report["supervision_status"] = "no_permission"
            else:
                # 檢查是否為主管（使用 groupfoodchn 檢查）
                try:
                    # 確保工號格式一致，都加上前導零
                    formatted_report_empno = f"{int(report_empno):05d}"
                    formatted_empno = f"{int(empno):05d}"
                    
                    supervisor_sql = text("""
                        SELECT COUNT(*) FROM jps.groupfoodchn 
                        WHERE cocode = :cocode AND empno = :report_empno AND supervisor = :viewer_empno
                    """)
                    supervisor_result = legacy_db.execute(supervisor_sql, {
                        "cocode": report_cocode,
                        "report_empno": formatted_report_empno,
                        "viewer_empno": formatted_empno
                    })
                    supervisor_row = supervisor_result.fetchone()
                    
                    if supervisor_row and supervisor_row[0] > 0:
                        # 檢查是否已經審核過
                        approval_sql = text("""
                            SELECT 
                                (SELECT COUNT(*) FROM jps.tdr_reply WHERE daily_no = :report_id AND empno = :viewer_empno) as reply_count,
                                (SELECT COUNT(*) FROM jps.tdr_score WHERE daily_no = :report_id AND reply_empno = :viewer_empno) as score_count
                        """)
                        approval_result = legacy_db.execute(approval_sql, {
                            "report_id": report["id"],
                            "viewer_empno": empno
                        })
                        approval_row = approval_result.fetchone()
                        
                        if approval_row and (approval_row[0] > 0 or approval_row[1] > 0):
                            report["supervision_status"] = "approved"
                        else:
                            report["supervision_status"] = "pending"
                    else:
                        # 檢查是否為Chairman權限
                        if empno in ['00002','01174','01376','02970','Z0005']:
                            # 檢查是否已經審核過
                            approval_sql = text("""
                                SELECT 
                                    (SELECT COUNT(*) FROM jps.tdr_reply WHERE daily_no = :report_id AND empno = :viewer_empno) as reply_count,
                                    (SELECT COUNT(*) FROM jps.tdr_score WHERE daily_no = :report_id AND reply_empno = :viewer_empno) as score_count
                            """)
                            approval_result = legacy_db.execute(approval_sql, {
                                "report_id": report["id"],
                                "viewer_empno": empno
                            })
                            approval_row = approval_result.fetchone()
                            
                            if approval_row and (approval_row[0] > 0 or approval_row[1] > 0):
                                report["supervision_status"] = "approved"
                            else:
                                report["supervision_status"] = "pending"
                        else:
                            report["supervision_status"] = "no_permission"
                except Exception as e:
                    logger.error(f"Error checking supervision status for report {report['id']}: {e}")
                    report["supervision_status"] = "no_permission"
        
        return reports
        
    except Exception as e:
        logger.error(f"Error getting daily homepage reports: {str(e)}")
        raise HTTPException(status_code=500, detail="取得日報首頁失敗")

# Part 2: 權限檢查輔助函數
async def _check_view_permission_for_detail(legacy_db: Session, viewer_empno: str, report_empno: str, report_cocode: str) -> bool:
    """檢查詳情查看權限 - 簡化版本避免事務錯誤"""
    
    # 檢查條件 5: 是否為自己的日報（最優先）
    if viewer_empno == report_empno or f"{int(viewer_empno):05d}" == f"{int(report_empno):05d}":
        return True
    
    # 檢查條件 1: Chairman權限（硬編碼避免表不存在問題）
    if viewer_empno in ['00002','01174','01376','02970','Z0005']:
        return True
    
    # 檢查條件 2: 簽核組織規則 (GROUPFOODCHN) - 直接查詢，避免事務問題
    try:
        # 創建新的資料庫連接避免事務問題
        new_db = next(get_legacy_db())
        
        formatted_report_empno = f"{int(report_empno):05d}"
        formatted_viewer_empno = f"{int(viewer_empno):05d}"
        
        groupfood_sql = text("""
            SELECT empno FROM jps.groupfoodchn 
            WHERE cocode = :cocode AND empno = :report_empno AND supervisor = :viewer_empno
        """)
        groupfood_result = new_db.execute(groupfood_sql, {
            "cocode": report_cocode,
            "report_empno": formatted_report_empno,
            "viewer_empno": formatted_viewer_empno
        })
        if groupfood_result.fetchone():
            return True
    except Exception as e:
        logger.error(f"GROUPFOODCHN check error: {e}")
        pass
    
    return False
async def _check_view_permission(legacy_db: Session, viewer_empno: str, report_empno: str, report_cocode: str) -> bool:
    """檢查查看權限 - 四項檢查任一成立即可查看詳情"""
    
    # 檢查條件 1: Chairman權限
    chairman_sql = text("""
        SELECT * FROM jps.JPS_CommonSetting 
        WHERE JPS_KEY = 'Chairman_Daily' AND Value1 = :empno
    """)
    chairman_result = legacy_db.execute(chairman_sql, {"empno": viewer_empno})
    if chairman_result.fetchone():
        return True
    
    # 檢查條件 2: 簽核組織規則 (GROUPFOODCHN)
    groupfood_sql = text("""
        SELECT empno FROM jps.groupfoodchn 
        WHERE cocode = :cocode AND empno = :report_empno AND supervisor = :viewer_empno
    """)
    groupfood_result = legacy_db.execute(groupfood_sql, {
        "cocode": report_cocode,
        "report_empno": report_empno,
        "viewer_empno": viewer_empno
    })
    if groupfood_result.fetchone():
        return True
    
    # 檢查條件 3: 日報訂閱規則 (DIARYSUPERS)
    diary_sql = text("""
        SELECT empno FROM jps.diarysupers 
        WHERE cmark IS NULL AND supervisor = :viewer_empno AND empno = :report_empno
    """)
    diary_result = legacy_db.execute(diary_sql, {
        "viewer_empno": viewer_empno,
        "report_empno": report_empno
    })
    if diary_result.fetchone():
        return True
    
    # 檢查條件 4: 特殊授權規則 (TDR_AUTHENTICATION)
    auth_sql = text("""
        SELECT COUNT(*) FROM jps.tdr_authentication 
        WHERE empno = :report_empno 
            AND status = 'Active' 
            AND auth_empno = :viewer_empno 
            AND report_Type = 'Daily' 
            AND SYSDATE BETWEEN start_date AND end_date
    """)
    auth_result = legacy_db.execute(auth_sql, {
        "report_empno": report_empno,
        "viewer_empno": viewer_empno
    })
    auth_row = auth_result.fetchone()
    if auth_row and auth_row[0] > 0:
        return True
    
    return False

async def _check_supervision_status(legacy_db: Session, viewer_empno: str, report_id: int) -> str:
    """檢查主管審核狀態"""
    
    # 首先檢查是否有權限進行審核（使用現有的主管檢查邏輯）
    # 查詢該日報的撰寫者
    report_sql = text("""
        SELECT empno, cocode FROM jps.tdr_master WHERE daily_no = :report_id
    """)
    report_result = legacy_db.execute(report_sql, {"report_id": report_id})
    report_row = report_result.fetchone()
    
    if not report_row:
        return "no_permission"
    
    report_empno = report_row[0]
    report_cocode = report_row[1]
    
    # 檢查是否為該員工的主管（使用 groupfoodchn 檢查）
    supervisor_sql = text("""
        SELECT COUNT(*) FROM jps.groupfoodchn 
        WHERE cocode = :cocode AND empno = :report_empno AND supervisor = :viewer_empno
    """)
    supervisor_result = legacy_db.execute(supervisor_sql, {
        "cocode": report_cocode,
        "report_empno": report_empno,
        "viewer_empno": viewer_empno
    })
    supervisor_row = supervisor_result.fetchone()
    
    # 如果不是主管，檢查是否為最高權限者
    has_supervisor_permission = False
    if supervisor_row and supervisor_row[0] > 0:
        has_supervisor_permission = True
    else:
        # 檢查Chairman權限 - 暫時使用硬編碼列表，表不存在時跳過
        try:
            chairman_sql = text("""
                SELECT * FROM jps.JPS_CommonSetting 
                WHERE JPS_KEY = 'Chairman_Daily' AND Value1 = :empno
            """)
            chairman_result = legacy_db.execute(chairman_sql, {"empno": viewer_empno})
            chairman_row = chairman_result.fetchone()
            if chairman_row:  # 如果有記錄就表示有Chairman權限
                has_supervisor_permission = True
        except Exception:
            # 表不存在時，使用硬編碼的Chairman列表作為備選
            if viewer_empno in ['00002','01174','01376','02970','Z0005']:
                has_supervisor_permission = True
    
    if not has_supervisor_permission:
        return "no_permission"
    
    # 檢查是否已經審核過（查看是否有回覆或評分記錄）
    approval_sql = text("""
        SELECT 
            (SELECT COUNT(*) FROM jps.tdr_reply WHERE daily_no = :report_id AND empno = :viewer_empno) as reply_count,
            (SELECT COUNT(*) FROM jps.tdr_score WHERE daily_no = :report_id AND reply_empno = :viewer_empno) as score_count
    """)
    approval_result = legacy_db.execute(approval_sql, {
        "report_id": report_id,
        "viewer_empno": viewer_empno
    })
    approval_row = approval_result.fetchone()
    
    if approval_row and (approval_row[0] > 0 or approval_row[1] > 0):
        return "approved"
    else:
        return "pending"

