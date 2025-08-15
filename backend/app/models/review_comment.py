# backend/app/models/review_comment.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rating = Column(Float, nullable=True)  # 審核評分（只有審核留言才會有）

    # Foreign Keys
    report_id = Column(Integer, ForeignKey("daily_reports.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("review_comments.id"), nullable=True)

    # Relationships
    report = relationship("DailyReport", back_populates="comments")
    author = relationship("User", back_populates="comments")
    parent = relationship("ReviewComment", remote_side=[id], back_populates="replies")
    replies = relationship("ReviewComment", back_populates="parent")
