# backend/app/models/report_approval.py
import datetime
import enum
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, UniqueConstraint, Float, Text
from sqlalchemy.orm import relationship
from .base import Base

class ApprovalStatus(enum.Enum):
    pending = "pending"
    approved = "approved"


class ReportApproval(Base):
    """每個主管對每個日報的獨立審核記錄"""
    __tablename__ = "report_approvals"

    id = Column(Integer, primary_key=True, index=True)
    
    # 外鍵關聯
    report_id = Column(Integer, ForeignKey("daily_reports.id"), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # 審核狀態和時間
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.pending, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    
    # 評分和意見 (可選)
    rating = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    
    # 關聯
    report = relationship("DailyReport", backref="approvals")
    supervisor = relationship("Employee", foreign_keys=[supervisor_id])
    
    # 確保每個主管對每個日報只能有一個審核記錄
    __table_args__ = (
        UniqueConstraint('report_id', 'supervisor_id', name='unique_report_supervisor_approval'),
    )