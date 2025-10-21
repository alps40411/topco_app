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
    ReviewStatusResponse,
    ReportAcknowledgeRequest,
    ReportAcknowledgeResponse
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
        
        result = await ReviewService.submit_review(
            db=db,
            daily_no=request.daily_no,
            reviewer_empno=current_user.employee.empno,
            reviewer_empname=current_user.employee.empnamec,
            reviewer_cocode=current_user.employee.cocode,
            score=request.score,
            reply_memo=request.reply_memo,
            to_users=request.to_users,
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
    # current_user: User = Depends(get_current_user),  # 暫時註解掉認證
    db: Session = Depends(get_legacy_db)
):
    """取得轉寄員工名單(使用 CorpEmployeeService.loadForward)"""
    try:
        # if not current_user.employee:
        #     raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        # 使用 CorpEmployeeService
        from ..services.corp_employee_service import CorpEmployeeService

        # 取得職稱列表 - 從 tdr_forward_duty 表取得
        duty_sql = text("""
            SELECT DISTINCT dutyname
            FROM jps.tdr_forward_duty
            ORDER BY dutyname
        """)

        duty_result = db.execute(duty_sql).fetchall()
        ls_forward_duty = [row[0] for row in duty_result]

        if not ls_forward_duty:
            logger.warning("沒有找到有效的職稱列表")
            ls_forward_duty = ["總經理", "協理", "處長", "副處長", "經理", "副理"]  # 預設職稱

        # 調用 CorpEmployeeService.loadForward
        corp_service = CorpEmployeeService()
        forward_data = corp_service.load_forward(
            ls_forward_duty=ls_forward_duty,
            table_name="tdr_forward_employees"
        )

        return {
            "success": True,
            "data": forward_data
        }

    except Exception as e:
        logger.error(f"取得轉寄員工名單失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得轉寄員工名單失敗: {str(e)}")

@router.post("/reports/acknowledge", response_model=ReportAcknowledgeResponse)
async def acknowledge_report(
    request: ReportAcknowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """確認已讀日報並從信箱移除通知"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")

        logger.info(f"確認日報請求 daily_no={request.daily_no}, user={current_user.employee.empno}")

        result = await ReviewService.acknowledge_report(
            db=db,
            daily_no=request.daily_no,
            user_empno=current_user.employee.empno,
            user_empname=current_user.employee.empnamec,
            user_cocode=current_user.employee.cocode
        )

        return ReportAcknowledgeResponse(
            success=result["success"],
            message=result["message"],
            eai_seq=result.get("eai_seq")
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"確認日報失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"確認日報失敗: {str(e)}")

