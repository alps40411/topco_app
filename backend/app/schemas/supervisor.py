# backend/app/schemas/supervisor.py

from pydantic import BaseModel
from typing import List, Optional
from .work_record import ConsolidatedReport
import datetime

class EmployeeSummary(BaseModel):
    id: int
    name: str
    department: str
    class Config:
        from_attributes = True

class ReportReviewCreate(BaseModel):
    rating: int
    feedback: str

class DailyReportDetail(BaseModel):
    id: int
    date: datetime.date
    status: str
    rating: Optional[int] = None
    feedback: Optional[str] = None
    consolidated_content: List[ConsolidatedReport] 
    employee: EmployeeSummary # <-- 新增 employee 摘要

    class Config:
        from_attributes = True

class EmployeeForList(BaseModel):
    id: int
    name: str
    department: str
    pending_reports_count: int

    class Config:
        from_attributes = True