# backend/app/schemas/review_comment.py
from pydantic import BaseModel
from typing import List, Optional, ForwardRef
from datetime import datetime

# --- 為了避免循環引用，這裡定義一個簡化的 User Schema ---
class UserSummary(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

# --- 留言的基礎 Schema ---
class ReviewCommentBase(BaseModel):
    content: str

# --- 建立留言時使用的 Schema ---
class ReviewCommentCreate(ReviewCommentBase):
    parent_comment_id: Optional[int] = None
    rating: Optional[float] = None  # 審核評分（只有主管審核時會有）

# --- 不包含回覆的簡單留言 Schema ---
class ReviewCommentSimple(ReviewCommentBase):
    id: int
    created_at: datetime
    author: UserSummary
    parent_comment_id: Optional[int] = None
    rating: Optional[float] = None  # 評分（如果是審核留言）

    class Config:
        from_attributes = True

# --- 前向引用以避免循環依賴 ---
ReviewCommentRef = ForwardRef('ReviewComment')

# --- 從 API 回傳時使用的完整 Schema (包含巢狀結構) ---
class ReviewComment(ReviewCommentBase):
    id: int
    created_at: datetime
    author: UserSummary
    parent_comment_id: Optional[int] = None
    rating: Optional[float] = None  # 評分（如果是審核留言）
    replies: List[ReviewCommentRef] = []

    class Config:
        from_attributes = True

# --- 更新前向引用 ---
ReviewComment.model_rebuild()
