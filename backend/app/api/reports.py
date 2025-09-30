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

@router.get("")
@router.get("/")
async def get_reports(
    date: Optional[str] = Query(None, description="查詢日期 YYYY-MM-DD"),
    empno: Optional[str] = Query(None, description="員工編號"),
    status: Optional[str] = Query(None, description="日報狀態"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """
    取得日報列表
    - 支援按日期、員工、狀態查詢
    - 主管可查看下屬日報
    - 員工只能查看自己的日報
    """
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 如果沒有指定員工編號，使用當前用戶
        target_empno = empno if empno else current_user.employee.empno
        
        # 權限檢查：只有主管可以查看其他人的日報
        if target_empno != current_user.employee.empno and not current_user.is_supervisor:
            raise HTTPException(status_code=403, detail="無權限查看其他人的日報")
        
        # 如果有指定日期，查詢該日期的日報
        if date:
            return await _get_reports_by_date(db, target_empno, date, current_user)
        else:
            # 沒有指定日期，返回最近的日報
            return await _get_recent_reports(db, target_empno, current_user)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        raise HTTPException(status_code=500, detail="取得日報列表失敗")

async def _get_reports_by_date(db: Session, empno: str, date: str, current_user: User):
    """按日期查詢日報"""
    # 轉換日期格式
    doc_date = date.replace("-", "")
    
    # 查詢員工基本資訊
    employee_sql = text("""
        SELECT empno, empnamec, cocode, deptno
        FROM jps.dcd003$master
        WHERE empno = :empno
    """)
    emp_result = db.execute(employee_sql, {"empno": empno}).fetchone()
    
    if not emp_result:
        raise HTTPException(status_code=404, detail="找不到指定員工")
    
    # 查詢已提交的日報
    reports_sql = text("""
        SELECT daily_no, empnamec, emergency, classify, reply_status, 
               doc_date, sop_desc_c, cocode
        FROM jps.tdr_master
        WHERE empno = :empno AND doc_date = :doc_date AND status = 'N'
        ORDER BY daily_no DESC
    """)
    
    reports_result = db.execute(reports_sql, {
        "empno": empno,
        "doc_date": doc_date
    })
    
    reports = []
    for row in reports_result.fetchall():
        daily_no = row[0]
        
        # 查詢日報詳細內容
        content = await _get_report_content(db, daily_no)
        
        reports.append({
            "id": int(daily_no),
            "employee": {
                "id": int(empno),
                "name": row[1] or emp_result[1],
                "department_no": emp_result[3],
                "empno": empno
            },
            "date": date,  # 返回標準格式的日期
            "status": "reviewed" if row[4] == 'Y' else "pending",
            "emergency": row[2] or "",
            "classify": row[3] or "",
            "sop_desc_c": row[6] or "",
            "consolidated_content": content,
            "rating": 0  # 後續可以加入評分查詢
        })
    
    return {
        "success": True,
        "data": reports,
        "total": len(reports)
    }

async def _get_recent_reports(db: Session, empno: str, current_user: User):
    """取得最近的日報"""
    # 查詢最近7天的日報
    reports_sql = text("""
        SELECT daily_no, empnamec, emergency, classify, reply_status, 
               doc_date, sop_desc_c, cocode
        FROM jps.tdr_master
        WHERE empno = :empno AND status = 'N'
        AND doc_date >= TO_CHAR(CURRENT_DATE - 7, 'YYYYMMDD')
        ORDER BY doc_date DESC, daily_no DESC
        LIMIT 20
    """)
    
    reports_result = db.execute(reports_sql, {"empno": empno})
    reports = []
    
    for row in reports_result.fetchall():
        # 格式化日期
        doc_date_str = row[5]
        formatted_date = f"{doc_date_str[:4]}-{doc_date_str[4:6]}-{doc_date_str[6:8]}"
        
        reports.append({
            "id": int(row[0]),
            "employee": {
                "id": int(empno),
                "name": row[1],
                "empno": empno
            },
            "date": formatted_date,
            "status": "reviewed" if row[4] == 'Y' else "pending",
            "emergency": row[2] or "",
            "classify": row[3] or "",
            "sop_desc_c": row[6] or "",
        })
    
    return {
        "success": True,
        "data": reports,
        "total": len(reports)
    }

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
        
        # 查詢回應記錄
        comments_sql = text("""
            SELECT r.reply_nos, r.empno, r.xuser, r.memo, r.xdate, r.xtime,
                   s.score
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