# backend/app/services/comment_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select
from typing import List

from app.models import ReviewComment, DailyReport, User
from app.schemas.review_comment import ReviewCommentCreate

async def create_comment(
    db: AsyncSession, 
    *, 
    report_id: int, 
    user: User, 
    comment_in: ReviewCommentCreate
) -> ReviewComment:
    """
    建立一則新的審核留言或回覆。
    """
    # 驗證parent_comment_id是否存在且屬於同一份日報
    if comment_in.parent_comment_id:
        parent_stmt = select(ReviewComment).where(
            ReviewComment.id == comment_in.parent_comment_id,
            ReviewComment.report_id == report_id
        )
        parent_result = await db.execute(parent_stmt)
        parent_comment = parent_result.scalar_one_or_none()
        if not parent_comment:
            raise ValueError("Parent comment not found or belongs to different report")
    
    db_comment = ReviewComment(
        content=comment_in.content,
        report_id=report_id,
        user_id=user.id,
        parent_comment_id=comment_in.parent_comment_id,
        rating=comment_in.rating  # 包含評分（如果有的話）
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment

async def get_comments_for_report(db: AsyncSession, *, report_id: int) -> List[dict]:
    """
    獲取指定日報的所有留言，並將其組織成巢狀結構。
    """
    # 獲取所有留言
    comments_stmt = (
        select(ReviewComment)
        .where(ReviewComment.report_id == report_id)
        .order_by(ReviewComment.created_at.asc())
    )
    comments_result = await db.execute(comments_stmt)
    all_comments = comments_result.scalars().all()
    
    # 獲取所有相關的 user
    user_ids = {comment.user_id for comment in all_comments}
    users_map = {}
    if user_ids:
        users_stmt = select(User).where(User.id.in_(user_ids))
        users_result = await db.execute(users_stmt)
        users = users_result.scalars().all()
        users_map = {user.id: user for user in users}
    
    # 轉換為字典格式並包含 author 信息
    comment_dict_map = {}
    root_comments = []
    
    # 首先創建所有評論的字典
    for comment in all_comments:
        author = users_map.get(comment.user_id)
        comment_dict = {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at,
            "user_id": comment.user_id,
            "report_id": comment.report_id,
            "parent_comment_id": comment.parent_comment_id,
            "rating": comment.rating,
            "author": {
                "id": author.id,
                "name": author.name,
                "email": author.email
            } if author else None,
            "replies": []
        }
        comment_dict_map[comment.id] = comment_dict
    
    # 組織巢狀結構
    for comment in all_comments:
        comment_dict = comment_dict_map[comment.id]
        if comment.parent_comment_id and comment.parent_comment_id in comment_dict_map:
            parent_dict = comment_dict_map[comment.parent_comment_id]
            parent_dict["replies"].append(comment_dict)
        else:
            root_comments.append(comment_dict)
    
    return root_comments

async def get_all_comments_for_report(db: AsyncSession, *, report_id: int) -> List[ReviewComment]:
    """
    獲取指定日報的所有留言（平面結構，不做巢狀組織）。
    """
    stmt = (
        select(ReviewComment)
        .where(ReviewComment.report_id == report_id)
        .order_by(ReviewComment.created_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().unique().all()
