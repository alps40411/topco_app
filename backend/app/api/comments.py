# backend/app/api/comments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core import deps
from app.models import User, DailyReport, Employee
from app.schemas.review_comment import ReviewComment, ReviewCommentCreate
from app.services import comment_service, supervisor_service

router = APIRouter(tags=["Comments"])

async def check_report_access(
    report_id: int, 
    current_user: User, 
    db: AsyncSession
) -> DailyReport:
    """
    檢查用戶是否有權限存取指定的日報。
    回傳日報物件或拋出HTTPException。
    """
    # 查詢日報
    stmt = select(DailyReport).where(DailyReport.id == report_id)
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily report not found"
        )
    
    # 如果是主管，檢查是否有權限審核該報告的員工
    if current_user.is_supervisor and current_user.employee:
        can_review = await supervisor_service.can_supervisor_review_employee(
            db, current_user.employee.id, report.employee_id
        )
        if can_review:
            return report
    
    # 如果是員工，只能存取自己的日報
    if hasattr(current_user, 'employee') and current_user.employee:
        if current_user.employee.id == report.employee_id:
            return report
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No permission to access this report"
    )

@router.post("/reports/{report_id}/comments")
async def create_new_comment(
    report_id: int,
    comment_in: ReviewCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    為指定的日報新增一則留言或回覆。
    """
    # 檢查權限
    await check_report_access(report_id, current_user, db)
    
    try:
        comment = await comment_service.create_comment(
            db=db, report_id=report_id, user=current_user, comment_in=comment_in
        )
        # 返回字典格式以避免序列化問題
        return {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at,
            "user_id": comment.user_id,
            "report_id": comment.report_id,
            "parent_comment_id": comment.parent_comment_id,
            "rating": comment.rating,
            "author": {
                "id": current_user.id,
                "name": current_user.name,
                "email": current_user.email
            },
            "replies": []
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment"
        )

@router.get("/reports/{report_id}/comments")
async def list_comments_for_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    獲取指定日報的所有留言（巢狀結構）。
    """
    # 檢查權限
    await check_report_access(report_id, current_user, db)
    
    try:
        comments = await comment_service.get_comments_for_report(db=db, report_id=report_id)
        return comments
    except Exception as e:
        print(f"Error in get_comments_for_report: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve comments: {str(e)}"
        )

@router.get("/reports/{report_id}/comments/all", response_model=List[ReviewComment])
async def list_all_comments_for_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    獲取指定日報的所有留言（平面結構）。
    """
    # 檢查權限
    await check_report_access(report_id, current_user, db)
    
    try:
        comments = await comment_service.get_all_comments_for_report(db=db, report_id=report_id)
        return comments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve comments"
        )
