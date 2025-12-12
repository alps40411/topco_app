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
from app.services.supervisor_service import SupervisorService

router = APIRouter(tags=["Supervisor"])
logger = logging.getLogger(__name__)

# ✅ REMOVED: /has-subordinates - 已移至 /api/users/has-subordinates

@router.get("/{report_id}/comments")
async def get_report_comments(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得日報的所有留言"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        # 查詢回應記錄（包含轉寄資訊）
        comments_sql = text("""
            SELECT r.reply_nos, r.empno, r.xuser, r.memo, r.xdate, r.xtime,
                   s.score,
                   (SELECT LISTAGG(g.empnamec, ', ') WITHIN GROUP (ORDER BY g.empnamec)
                    FROM (
                        SELECT DISTINCT m.to_empno
                        FROM jps.tdr_msg_send_log m
                        WHERE m.daily_no = r.daily_no AND m.reply_nos = r.reply_nos
                    ) m
                    JOIN jps.groupmember g ON m.to_empno = g.empno
                   ) as forwarded_to_names
            FROM jps.tdr_reply r
            LEFT JOIN jps.tdr_score s ON r.daily_no = s.daily_no AND r.reply_nos = s.reply_nos
            WHERE r.daily_no = :daily_no
            ORDER BY r.reply_nos ASC
        """)

        result = db.execute(comments_sql, {"daily_no": report_id})

        comments = []
        for row in result.fetchall():
            comments.append({
                "id": row[0],  # reply_nos
                "content": row[3] or "",  # memo
                "created_at": f"{row[4]} {row[5]}" if row[4] and row[5] else "",
                "user_id": row[1],  # empno
                "author": {
                    "id": row[1],  # empno
                    "name": row[2] or row[1],  # xuser 或 empno
                },
                "rating": row[6],  # score
                "forwarded_to": row[7],  # 轉寄給誰的姓名列表
                "replies": []
            })

        return {
            "success": True,
            "data": comments
        }

    except Exception as e:
        logger.error(f"Error getting report comments: {str(e)}")
        raise HTTPException(status_code=500, detail="取得留言失敗")

@router.get("/{daily_no}/approvals")
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
            WHERE g.empno = :empno AND g.cocode = 'A' and g.cocode = e.cocode
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

# ✅ REMOVED: /reports/{report_id}/approvals - 前端已改用 /{daily_no}/approvals

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


# ✅ REMOVED: GET /reports/{report_id} - 已移至 reports.py，避免重複

# my-reports-by-date API已移除，因為已廢除「我的日報」功能

@router.get("/reports/{report_id}")  # TODO: 應該移除，使用 reports.py 的端點
async def get_report_detail_deprecated(
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
                filepath = file_row[0] or ""  # 從資料庫取得的檔案路徑 (格式: YYYYMM/filename.ext)
                file_ext = filename.lower().split('.')[-1] if '.' in filename else ""
                if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                    file_type = f"image/{file_ext}"
                else:
                    file_type = "application/octet-stream"

                # ✅ 使用 CommonApiFileService 生成完整的下載 URL
                # filepath 是相對路徑 (例如: 202510/xxxxx.png)
                # 需要轉換為完整的 CommonAPI URL
                from app.services.commonapi_file_service import CommonApiFileService
                file_url = CommonApiFileService.generate_download_url(
                    file_id=filepath,  # 使用相對路徑作為 FileId
                    filename=filename,
                    cocode=cocode
                )

                files.append({
                    "id": file_id,
                    "name": filename,
                    "type": file_type,
                    "size": 0,  # 檔案大小暫時設為 0，因為資料庫中沒有這個欄位
                    "url": file_url,  # 完整的 CommonAPI 下載 URL
                    "filepath": filepath  # 保留原始路徑供後端使用
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
                "files": files,  # 新增檔案列表
                "xdate": detail_row[23] or "",  # xdate - 最後修改日期
                "xtime": detail_row[24] or ""   # xtime - 最後修改時間
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
    request_body: dict,
    current_user: User = Depends(get_current_user)
):
    """生成 AI 建議"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="該用戶不是員工")

        # 從 request body 取得評分
        rating = request_body.get('rating') if request_body else None
        
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
                employee_name=employee_name,
                rating=rating
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
    current_user: User = Depends(get_current_user),
    legacy_db: Session = Depends(get_legacy_db)
):
    """新的日報首頁 - 取得登入者可能看到的所有日報列表 (包含下屬日報與轉寄日報)"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=404, detail="該用戶不是員工")

        doc_date = date.replace("-", "")
        empno = current_user.employee.empno
        cocode = current_user.employee.cocode or 'A'
        deptno = current_user.employee.deptno or ''

        logger.info(f"Fetching reports for empno={empno}, date={doc_date}, cocode={cocode}, deptno={deptno}")

        # ✅ 優化: 權限檢查已整合到 SQL 中，無需 Python 迴圈
        # 1. 取得下屬日報列表 (can_view_detail 已在 SQL 層計算)
        subordinate_reports = SupervisorService.get_daily_homepage_reports(
            db=legacy_db,
            empno=empno,
            cocode=cocode,
            deptno=deptno,
            doc_date=doc_date
        )

        # 2. 取得轉寄日報列表 (can_view_detail 固定為 True)
        forwarded_reports = SupervisorService.get_forwarded_reports(
            db=legacy_db,
            empno=empno,
            doc_date=doc_date
        )

        logger.info(f"Fetched {len(subordinate_reports)} subordinate reports and {len(forwarded_reports)} forwarded reports for user {empno} on date {doc_date}")

        return {
            "subordinate_reports": subordinate_reports,
            "forwarded_reports": forwarded_reports
        }

    except Exception as e:
        logger.error(f"Error getting daily homepage reports: {str(e)}")
        raise HTTPException(status_code=500, detail="取得日報首頁失敗")

# ✅ REMOVED: 權限檢查輔助函數已遷移到 SupervisorService

@router.get("/resolve-report/{daily_no}")
async def resolve_report_url(
    daily_no: str,
    legacy_db: Session = Depends(get_legacy_db)
):
    """
    根據 daily_no 解析出 employee ID，用於信件連結跳轉
    從信件URL格式: ?web_type=EIP&cocode=A&daily_no=8855978
    轉換為應用URL格式: ?tab=supervisor&employee=02975&report=8855978
    """
    try:
        # 查詢日報對應的員工資訊
        employee_sql = text("""
            SELECT d.empno, d.empnamec
            FROM jps.tdr_master d
            WHERE d.daily_no = :daily_no
        """)

        emp_result = legacy_db.execute(employee_sql, {"daily_no": daily_no})
        emp_row = emp_result.fetchone()

        if not emp_row:
            raise HTTPException(status_code=404, detail="找不到指定的日報")

        return {
            "daily_no": daily_no,
            "employee_id": emp_row[0],
            "employee_name": emp_row[1]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving report URL for daily_no={daily_no}: {str(e)}")
        raise HTTPException(status_code=500, detail="解析日報連結失敗")

