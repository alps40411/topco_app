# backend/app/api/reports.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json

from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..schemas.user import User

router = APIRouter(tags=["Reports"])
logger = logging.getLogger(__name__)

# ========== 日報查詢相關 ==========



@router.get("/{report_id}")
async def get_report_detail(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得單一日報詳情"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 查詢日報基本資訊
        master_sql = text("""
            SELECT daily_no, empno, empnamec, doc_date, status, sop_desc_c
            FROM jps.tdr_master
            WHERE daily_no = :daily_no
        """)
        
        master_result = db.execute(master_sql, {"daily_no": report_id}).fetchone()
        if not master_result:
            raise HTTPException(status_code=404, detail="找不到指定的日報")
        
        # 權限檢查
        report_owner_empno = master_result[1]
        if report_owner_empno != current_user.employee.empno and not current_user.is_supervisor:
            raise HTTPException(status_code=403, detail="無權限查看此日報")
        
        # 查詢員工資訊
        employee_sql = text("""
            SELECT empno, empnamec, cocode, deptno
            FROM jps.dcd003$master
            WHERE empno = :empno
        """)
        emp_result = db.execute(employee_sql, {"empno": report_owner_empno}).fetchone()
        
        # 查詢詳細內容
        content = await _get_report_content(db, report_id)
        
        # 格式化日期
        doc_date_str = master_result[3]
        formatted_date = f"{doc_date_str[:4]}-{doc_date_str[4:6]}-{doc_date_str[6:8]}"
        
        return {
            "success": True,
            "data": {
                "id": int(report_id),
                "employee": {
                    "id": int(report_owner_empno),
                    "name": master_result[2] or (emp_result[1] if emp_result else ""),
                    "department_no": emp_result[3] if emp_result else "",
                    "empno": report_owner_empno
                },
                "date": formatted_date,
                "status": "submitted",
                "sop_desc_c": master_result[5] or "",
                "consolidated_content": content,
                "rating": 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report detail: {str(e)}")
        raise HTTPException(status_code=500, detail="取得日報詳情失敗")

async def _get_report_content(db: Session, daily_no: str):
    """取得日報的詳細內容"""
    try:
        details_sql = text("""
            SELECT b.daily_sub_nos, b.sopno, b.sop_code, b.prod_cate,
                   b.exetime, b.estimate, b.attitude, b.memo_collect,
                   b.cuno_subj, b.cuno_msg, b.comp_desc, b.ques_desc, b.solut_desc,
                   b.planno, b.memo, b.finish_rate
            FROM jps.tdr_detail1 a
            JOIN jps.tdr_detail2 b ON b.daily_no = a.daily_no AND b.daily_sub_nos = a.daily_sub_nos
            WHERE a.daily_no = :daily_no
            ORDER BY a.daily_sub_nos
        """)
        
        details_result = db.execute(details_sql, {"daily_no": daily_no})
        
        consolidated_content = []
        for detail_row in details_result.fetchall():
            # 處理工作項目名稱
            work_item_name = ""
            if detail_row[2]:  # sop_code
                work_item_sql = text("SELECT name FROM jps.tpm_sop_detail WHERE sopno = :sopno AND seq = :seq")
                work_item_result = db.execute(work_item_sql, {
                    "sopno": str(detail_row[1]),
                    "seq": str(detail_row[2])
                })
                work_item_row = work_item_result.fetchone()
                if work_item_row:
                    work_item_name = work_item_row[0]
            
            # 取得執行工作名稱
            execution_work_name = ""
            if detail_row[1]:  # sopno
                exec_work_sql = text("SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno")
                exec_work_result = db.execute(exec_work_sql, {"sopno": str(detail_row[1])})
                exec_work_row = exec_work_result.fetchone()
                if exec_work_row:
                    execution_work_name = exec_work_row[0]
            
            content_item = {
                "project": {
                    "plan_subj_c": "基本工作項目",  # 簡化處理
                    "planno": detail_row[13] or ""
                },
                "content": detail_row[14] or "",  # memo
                "execution_work_name": execution_work_name,
                "work_item_name": work_item_name,
                "total_execution_time_minutes": int(detail_row[4] or 0),  # exetime
                "finish_rate": detail_row[15] or 0,
                "cuno_subj": detail_row[8] or "",
                "cuno_msg": detail_row[9] or "",
                "comp_desc": detail_row[10] or "",
                "ques_desc": detail_row[11] or "",
                "solut_desc": detail_row[12] or ""
            }
            consolidated_content.append(content_item)
        
        return consolidated_content
        
    except Exception as e:
        logger.error(f"Error getting report content: {str(e)}")
        return []

# ========== 日報留言相關 ==========

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

@router.post("/{report_id}/comments")
async def create_report_comment(
    report_id: str,
    comment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """發表日報留言"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        content = comment_data.get("content", "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="留言內容不能為空")

        # 取得日報的 doc_date 和 empno
        report_info_sql = text("""
            SELECT doc_date, empno
            FROM jps.tdr_master
            WHERE daily_no = :daily_no
        """)
        report_info = db.execute(report_info_sql, {"daily_no": report_id}).fetchone()
        if not report_info:
            raise HTTPException(status_code=404, detail="找不到指定的日報")

        doc_date = report_info[0]
        report_empno = report_info[1]

        # 取得下一個回應編號
        max_reply_sql = text("""
            SELECT COALESCE(MAX(reply_nos), 0) + 1
            FROM jps.tdr_reply
            WHERE daily_no = :daily_no
        """)
        reply_nos = db.execute(max_reply_sql, {"daily_no": report_id}).scalar()

        # 插入回應記錄
        now = datetime.now()
        current_date = now.strftime('%Y%m%d')
        current_time = now.strftime('%H:%M:%S')

        insert_reply_sql = text("""
            INSERT INTO jps.tdr_reply (
                daily_no, reply_nos, empno, memo, xuser, xdate, xtime, memo1, from_where
            ) VALUES (
                :daily_no, :reply_nos, :empno, :memo, :xuser, :xdate, :xtime, '', 0
            )
        """)

        db.execute(insert_reply_sql, {
            "daily_no": report_id,
            "reply_nos": reply_nos,
            "empno": current_user.employee.empno,
            "memo": content,
            "xuser": current_user.employee.empnamec,
            "xdate": current_date,
            "xtime": current_time
        })

        # 檢查是否為罐頭訊息，如果不是則記錄為特殊訊息
        is_general_sql = text("""
            SELECT COUNT(*) FROM jps.TDR_REPLY_GENERAL_COMMENT
            WHERE memo = :memo
        """)
        is_general_count = db.execute(is_general_sql, {"memo": content}).scalar()

        # 如果不是罐頭訊息，則插入特殊訊息記錄
        if is_general_count == 0:
            insert_special_sql = text("""
                INSERT INTO jps.TDR_REPLY_SPECIAL_COMMENT
                (DAILY_NO, DOC_DATE, EMPNO, UPDATETIME)
                VALUES (:daily_no, :doc_date, :empno, SYSDATE)
            """)

            db.execute(insert_special_sql, {
                "daily_no": report_id,
                "doc_date": doc_date,
                "empno": report_empno
            })

        db.commit()
        
        return {
            "success": True,
            "message": "留言發表成功",
            "data": {
                "id": reply_nos,
                "content": content,
                "created_at": f"{current_date} {current_time}",
                "author": {
                    "id": 0,
                    "name": current_user.employee.empnamec,
                    "empno": current_user.employee.empno
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating report comment: {str(e)}")
        raise HTTPException(status_code=500, detail="發表留言失敗")

# ========== 日報審核相關 ==========

@router.get("/{report_id}/approvals")
async def get_report_approvals(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得日報的審核記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 這個功能與現有的 supervisor API 一致
        # 查詢可能的審核主管清單
        employee_sql = text("""
            SELECT d.empno, d.empnamec
            FROM jps.tdr_master d
            WHERE d.daily_no = :daily_no
        """)
        
        emp_result = db.execute(employee_sql, {"daily_no": report_id}).fetchone()
        if not emp_result:
            raise HTTPException(status_code=404, detail="找不到指定的日報")
        
        # 查詢該員工的上級主管列表
        supervisor_sql = text("""
            SELECT DISTINCT g.supervisor, e.empnamec
            FROM jps.groupfoodchn g
            LEFT JOIN jps.dcd003$master e ON g.supervisor = e.empno
            WHERE g.empno = :empno AND g.cocode = 'A'
              AND e.quitdate IS NULL
        """)
        
        sup_result = db.execute(supervisor_sql, {"empno": emp_result[0]})
        supervisors = sup_result.fetchall()
        
        # 查詢回覆和評分資訊
        reply_sql = text("""
            SELECT r.empno, r.memo, r.xdate, r.xtime, e.empnamec as supervisor_name
            FROM jps.tdr_reply r
            LEFT JOIN jps.dcd003$master e ON r.empno = e.empno
            WHERE r.daily_no = :daily_no
        """)
        
        reply_result = db.execute(reply_sql, {"daily_no": report_id})
        replies_dict = {}
        for reply_row in reply_result.fetchall():
            empno = reply_row[0]
            replies_dict[empno] = {
                "feedback": reply_row[1],
                "approved_at": f"{reply_row[2]} {reply_row[3]}",
                "supervisor_name": reply_row[4] or "主管"
            }
        
        # 查詢評分資訊
        score_sql = text("""
            SELECT s.reply_empno, s.score, s.xdate, s.xtime, e.empnamec as supervisor_name
            FROM jps.tdr_score s
            LEFT JOIN jps.dcd003$master e ON s.reply_empno = e.empno
            WHERE s.daily_no = :daily_no
        """)
        
        score_result = db.execute(score_sql, {"daily_no": report_id})
        scores_dict = {}
        for score_row in score_result.fetchall():
            empno = score_row[0]
            scores_dict[empno] = {
                "rating": score_row[1],
                "approved_at": f"{score_row[2]} {score_row[3]}",
                "supervisor_name": score_row[4] or "主管"
            }
        
        # 建構審核資訊列表
        approvals = []
        for sup_row in supervisors:
            supervisor_empno = sup_row[0]
            supervisor_name = sup_row[1] or "主管"
            
            has_reply = supervisor_empno in replies_dict
            has_score = supervisor_empno in scores_dict
            
            approval_info = {
                "supervisor_id": int(supervisor_empno) if supervisor_empno.isdigit() else 0,
                "supervisor_name": supervisor_name,
                "supervisor_empno": supervisor_empno,
                "status": "approved" if (has_reply or has_score) else "pending"
            }
            
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
        
        return {
            "success": True,
            "data": approvals
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report approvals: {str(e)}")
        raise HTTPException(status_code=500, detail="取得審核記錄失敗")

# ========== 日報刪除相關 ==========

@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    刪除日報
    - 只有作者本人可以刪除
    - 如果已有留言則不能刪除
    - 刪除時會刪除 detail1、detail2、master
    - 並插入 del_inbox 到 eai_source 通知系統
    """
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        # 查詢日報基本資訊
        master_sql = text("""
            SELECT daily_no, empno, empnamec, doc_date, cocode
            FROM jps.tdr_master
            WHERE daily_no = :daily_no
        """)

        master_result = db.execute(master_sql, {"daily_no": report_id}).fetchone()
        if not master_result:
            raise HTTPException(status_code=404, detail="找不到指定的日報")

        daily_no, report_empno, empnamec, doc_date, cocode = master_result

        # 權限檢查：只有作者本人可以刪除
        if report_empno != current_user.employee.empno:
            raise HTTPException(status_code=403, detail="只有作者本人可以刪除日報")

        # 檢查是否有留言
        reply_count_sql = text("""
            SELECT COUNT(*) FROM jps.tdr_reply WHERE daily_no = :daily_no
        """)
        reply_count = db.execute(reply_count_sql, {"daily_no": report_id}).scalar()

        if reply_count > 0:
            raise HTTPException(status_code=400, detail="此日報已有留言，無法刪除")

        # 開始刪除流程
        now = datetime.now()
        current_date = now.strftime('%Y/%m/%d')
        current_time = now.strftime('%H:%M:%S')

        # 1. 刪除 tdr_detail2
        delete_detail2_sql = text("DELETE FROM jps.tdr_detail2 WHERE daily_no = :daily_no")
        detail2_deleted = db.execute(delete_detail2_sql, {"daily_no": report_id}).rowcount
        logger.info(f"刪除 {detail2_deleted} 筆 tdr_detail2 記錄")

        # 2. 刪除 tdr_detail1
        delete_detail1_sql = text("DELETE FROM jps.tdr_detail1 WHERE daily_no = :daily_no")
        detail1_deleted = db.execute(delete_detail1_sql, {"daily_no": report_id}).rowcount
        logger.info(f"刪除 {detail1_deleted} 筆 tdr_detail1 記錄")

        # 3. 刪除 tdr_master
        delete_master_sql = text("DELETE FROM jps.tdr_master WHERE daily_no = :daily_no")
        master_deleted = db.execute(delete_master_sql, {"daily_no": report_id}).rowcount
        logger.info(f"刪除 {master_deleted} 筆 tdr_master 記錄")

        # 4. 插入 del_inbox 到 eai_source
        eai_seq = db.execute(text("SELECT jps.seq_eai_source.nextval FROM dual")).scalar_one()

        doc_bady = (
            f"Source=JpsReportDailyDelete^|Action=Del_inbox^|cocode=Del_inbox^|xuser={report_empno}^|"
            f"doc_date={current_date}^|doc_time={current_time}^|Key={daily_no}^|Subject=Daily_Dele_Report"
        )

        insert_eai_sql = text("""
            INSERT INTO jps.eai_source
            (eai_seq, source, subject, cocode, xuser, touser, doc_date, doc_time, key, action, doc_bady, status, planno)
            VALUES (:eai_seq, 'JpsReportDailyDelete', 'Daily_Dele_Report', :cocode, :xuser, '', :doc_date, :doc_time, :key, 'Del_inbox', :doc_bady, 'N', NULL)
        """)

        db.execute(insert_eai_sql, {
            "eai_seq": eai_seq,
            "cocode": cocode,
            "xuser": report_empno,
            "doc_date": current_date,
            "doc_time": current_time,
            "key": daily_no,
            "doc_bady": doc_bady
        })

        logger.info(f"成功插入 del_inbox 記錄到 eai_source, eai_seq: {eai_seq}")

        db.commit()

        return {
            "success": True,
            "message": "日報刪除成功",
            "deleted_items": {
                "detail1": detail1_deleted,
                "detail2": detail2_deleted,
                "master": master_deleted
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除日報失敗: {str(e)}")