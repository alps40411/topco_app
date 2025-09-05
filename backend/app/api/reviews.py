# backend/app/api/reviews.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from sqlalchemy import text

from ..core.deps import get_current_user
from ..core.legacy_database import get_legacy_db
from ..models.user import User
from ..services.review_service import ReviewService
from ..schemas.review_schemas import (
    ReviewSubmitRequest, 
    ReviewSubmitResponse, 
    ReviewStatusResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/reviews/submit", response_model=ReviewSubmitResponse)
async def submit_review(
    request: ReviewSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """提交主管審閱（評分和回復）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 驗證評分範圍
        if request.score is not None and (request.score < 1 or request.score > 5):
            raise HTTPException(status_code=400, detail="評分必須在 1-5 分之間")
        
        # 檢查是否至少有評分或回應其中一項
        if request.score is None and not request.reply_memo:
            raise HTTPException(status_code=400, detail="必須提供評分或回應內容")
        
        logger.info(f"提交審閱 daily_no={request.daily_no}, reviewer={current_user.employee.empno}")
        
        result = ReviewService.submit_review(
            db=db,
            daily_no=request.daily_no,
            reviewer_empno=current_user.employee.empno,
            reviewer_empname=current_user.employee.empnamec,
            reviewer_cocode=current_user.employee.cocode,
            score=request.score,
            reply_memo=request.reply_memo,
            forward_users=request.forward_users
        )
        
        return ReviewSubmitResponse(
            success=result["success"],
            message=result["message"],
            reply_nos=result.get("reply_nos")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交審閱失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交審閱失敗: {str(e)}")

@router.get("/reviews/{daily_no}/status", response_model=ReviewStatusResponse)
async def get_review_status(
    daily_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得指定日報的審閱狀態"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        status = ReviewService.get_review_status(
            db=db,
            daily_no=daily_no,
            reviewer_empno=current_user.employee.empno
        )
        
        return ReviewStatusResponse(
            daily_no=status["daily_no"],
            has_replied=status["has_replied"],
            has_scored=status["has_scored"],
            reply_records=status["reply_records"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得審閱狀態失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得審閱狀態失敗: {str(e)}")

@router.post("/reviews/{daily_no}/score")
async def submit_score_only(
    daily_no: str,
    score: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """僅提交評分（快速評分）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        if score < 1 or score > 5:
            raise HTTPException(status_code=400, detail="評分必須在 1-5 分之間")
        
        result = ReviewService.submit_review(
            db=db,
            daily_no=daily_no,
            reviewer_empno=current_user.employee.empno,
            reviewer_empname=current_user.employee.empnamec,
            reviewer_cocode=current_user.employee.cocode,
            score=score
        )
        
        return {
            "success": True,
            "message": "評分提交成功",
            "score": score,
            "daily_no": daily_no
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交評分失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交評分失敗: {str(e)}")

@router.post("/reviews/{daily_no}/reply")
async def submit_reply_only(
    daily_no: str,
    reply_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """僅提交回應（不含評分）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        reply_memo = reply_data.get("reply_memo")
        forward_users = reply_data.get("forward_users", [])
        
        if not reply_memo:
            raise HTTPException(status_code=400, detail="回應內容不能為空")
        
        result = ReviewService.submit_review(
            db=db,
            daily_no=daily_no,
            reviewer_empno=current_user.employee.empno,
            reviewer_empname=current_user.employee.empnamec,
            reviewer_cocode=current_user.employee.cocode,
            reply_memo=reply_memo,
            forward_users=forward_users
        )
        
        return {
            "success": True,
            "message": "回應提交成功",
            "daily_no": daily_no,
            "reply_nos": result.get("reply_nos")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交回應失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交回應失敗: {str(e)}")

@router.get("/reviews/{daily_no}/replies")
async def get_all_replies(
    daily_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得指定日報的所有回應記錄"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        status = ReviewService.get_review_status(
            db=db,
            daily_no=daily_no,
            reviewer_empno=current_user.employee.empno
        )
        
        return {
            "daily_no": daily_no,
            "replies": status["reply_records"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得回應記錄失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得回應記錄失敗: {str(e)}")

@router.delete("/reviews/{daily_no}/score")
async def delete_score(
    daily_no: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """刪除評分（如果需要重新評分）"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        from sqlalchemy import text
        
        # 刪除評分記錄
        delete_score_sql = text("""
            DELETE FROM jps.tdr_score 
            WHERE daily_no = :daily_no AND reply_empno = :reply_empno
        """)
        
        result = db.execute(delete_score_sql, {
            "daily_no": daily_no,
            "reply_empno": current_user.employee.empno
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="找不到要刪除的評分記錄")
        
        db.commit()
        
        return {
            "success": True,
            "message": "評分已刪除，可以重新評分",
            "daily_no": daily_no
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"刪除評分失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除評分失敗: {str(e)}")

@router.get("/forward/visors")
async def get_forward_visors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得轉寄職稱名單"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 日報轉寄(職稱)
        visor_sql = text("""
            SELECT a.empno, a.empname 
            FROM jps.tdr_forward_visor a 
            LEFT JOIN jps.dcd003$master b ON a.empno = b.empno 
                AND b.estatus <> '3' 
                AND (b.RIGHT_STOP_DATE IS NULL OR b.RIGHT_STOP_DATE > TO_CHAR(CURRENT_DATE, 'yyyyMMdd')) 
                AND cocode IN (
                    SELECT cocode 
                    FROM jps.dcd001$master 
                    WHERE eip_active = 'Y'
                ) 
            ORDER BY a.sorting
        """)
        
        result = db.execute(visor_sql).fetchall()
        
        visors = []
        for row in result:
            visors.append({
                "empno": row[0],
                "empname": row[1]
            })
        
        return {
            "success": True,
            "data": visors
        }
        
    except Exception as e:
        logger.error(f"取得轉寄職稱名單失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得轉寄職稱名單失敗: {str(e)}")

@router.get("/forward/employees")
async def get_forward_employees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得轉寄員工名單(按部門分組)"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        # 日報轉寄名單(下半部, 分部門)
        employee_sql = text("""
            SELECT t.*,
                (
                    CASE
                    WHEN t.cocode = 'G' THEN 'ZG'
                    WHEN t.cocode = 'G01' THEN 'ZG01'
                    WHEN t.cocode = 'J09'  THEN 'J009'
                    ELSE t.cocode
                    END
                ) AS sort_cocode, 
                (
                    CASE
                    WHEN sort_order IS NULL THEN '99999'
                    ELSE sort_order::text
                    END
                ) AS sort_customize, 
                (
                    CASE
                    WHEN t.cocode = 'H' AND t.g_deptno = '00A00' THEN '0'
                    WHEN t.cocode = 'J07' AND t.g_deptno = '00010' THEN '0'
                    WHEN t.cocode = 'J10' AND t.g_deptno = '00010' THEN '0'
                    WHEN t.cocode = 'J17' AND t.g_deptno = '03000' THEN '0'
                    WHEN t.cocode = 'M' AND t.g_deptno = '00000' THEN '0'
                    WHEN t.cocode = 'P' AND t.g_deptno = '00010' THEN '0'
                    WHEN t.cocode = 'T' AND t.g_deptno = 'S0000' THEN '0'
                    WHEN t.cocode = 'X' AND t.g_deptno = '05000' THEN '0'
                    ELSE '1'
                    END
                ) AS sort_gmDept, 
                (
                    CASE
                    WHEN t.sbu = 1 AND t.cocode = 'T' THEN SUBSTR(t.g_deptno, 1, 3) || '00'
                    WHEN t.sbu = 1 AND t.cocode = 'A' AND SUBSTR(t.g_deptno, 1, 2) = '00' THEN '99' || SUBSTR(t.g_deptno, 3, 3)
                    WHEN t.sbu = 1 AND t.cocode = 'A' THEN SUBSTR(t.g_deptno, 1, 2) || '000'
                    WHEN t.sbu = 2 AND t.cocode = 'A' AND t.g_deptno = '00521' THEN t.g_deptno 
                    WHEN t.sbu = 2 AND t.cocode = 'A' AND ( t.g_deptno NOT LIKE '00G7%' AND t.g_deptno NOT LIKE '00G1%' AND t.g_deptno NOT LIKE '00G3%' AND t.g_deptno NOT LIKE '00B4%' ) THEN SUBSTR(t.g_deptno, 1, 4) || '0'
                    ELSE t.g_deptno
                    END
                ) AS g_deptno1
            FROM (
                SELECT
                (
                    CASE
                    WHEN b.cocode = '003' AND (b.deptno = '00000' OR b.deptno = '00281') THEN 'A'
                    WHEN b.practice_cocode IS NULL THEN b.cocode
                    WHEN b.practice_cocode <> b.cocode THEN b.cocode
                    ELSE b.practice_cocode
                    END
                ) AS cocode,
                a.empno, b.empnamec,
                (
                    CASE
                    WHEN b.practice_cocode IS NULL THEN b.deptno
                    WHEN b.practice_cocode <> b.cocode THEN b.deptno
                    ELSE b.practice_deptno
                    END
                ) AS deptno,
                (
                    CASE
                    WHEN f.duty IS NULL THEN '其他'
                    ELSE f.duty
                    END
                ) AS dutyscript, 
                c.sbu, d.coabbv, 
                (
                    CASE
                    WHEN c.sbu = 2 AND c.cocode = 'A' AND c.g_deptno LIKE '00A2%' THEN '資訊處'
                    WHEN c.sbu = 2 AND c.cocode = 'A' AND c.g_deptno LIKE '00B3%' THEN '資材處'
                    ELSE c.deptabbv
                    END
                ) AS deptabbv, 
                (
                    CASE
                    WHEN b.cocode = '003' AND (b.deptno = '00000' OR b.deptno = '00281') THEN '00G10'
                    ELSE c.g_deptno
                    END
                ) AS g_deptno, b.dclass, b.adm_rank, g.sort_order 
                FROM jps.TDR_FORWARDLIST a
                JOIN jps.DCD003$MASTER b ON a.cocode = b.cocode AND a.empno = b.EMPNO
                JOIN jps.DCD002$MASTER c ON a.cocode = c.cocode AND b.deptno = c.DEPTNO
                JOIN jps.DCD001$MASTER d ON a.cocode = d.COCODE
                LEFT JOIN jps.DCD004$MASTER e ON a.cocode = e.cocode AND b.dutyno = e.dutyno AND e.ducode = 'O'
                LEFT JOIN jps.tdr_forward_duty f ON e.DUTYNAME = f.DUTYNAME 
                LEFT JOIN jps.tdr_forward_dept_sort g ON d.cocode = g.cocode AND c.g_deptno = g.deptno
                WHERE b.quitdate IS NULL 
                AND (b.RIGHT_STOP_DATE IS NULL OR b.RIGHT_STOP_DATE > TO_CHAR(CURRENT_DATE, 'yyyyMMdd'))
            ) t
            ORDER BY sort_cocode, sort_customize, sort_gmDept, sbu, g_deptno1, dclass DESC, adm_rank
        """)
        
        result = db.execute(employee_sql).fetchall()
        
        # 按公司和部門分組
        grouped_data = {}
        for row in result:
            coabbv = row[5]  # coabbv
            deptabbv = row[6]  # deptabbv
            
            if coabbv not in grouped_data:
                grouped_data[coabbv] = {}
            
            if deptabbv not in grouped_data[coabbv]:
                grouped_data[coabbv][deptabbv] = []
            
            grouped_data[coabbv][deptabbv].append({
                "empno": row[1],  # empno
                "empname": row[2],  # empnamec
                "cocode": row[0],  # cocode
                "deptno": row[3],  # deptno
                "duty": row[4],   # dutyscript
                "dclass": row[9], # dclass
                "adm_rank": row[10] # adm_rank
            })
        
        return {
            "success": True,
            "data": grouped_data
        }
        
    except Exception as e:
        logger.error(f"取得轉寄員工名單失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得轉寄員工名單失敗: {str(e)}")