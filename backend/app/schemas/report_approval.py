# backend/app/schemas/report_approval.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"

class ReportApprovalBase(BaseModel):
    rating: Optional[float] = None
    feedback: Optional[str] = None

class ReportApprovalCreate(ReportApprovalBase):
    status: ApprovalStatus

class ReportApprovalUpdate(ReportApprovalBase):
    status: ApprovalStatus

class ReportApproval(ReportApprovalBase):
    id: int
    report_id: int
    supervisor_id: int
    status: ApprovalStatus
    approved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class SupervisorApprovalInfo(BaseModel):
    """主管審核信息，用於前端顯示"""
    supervisor_id: int
    supervisor_name: str
    supervisor_empno: str
    status: ApprovalStatus
    approved_at: Optional[datetime] = None
    rating: Optional[float] = None
    feedback: Optional[str] = None