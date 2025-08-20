# backend/app/schemas/supervisor.py

from pydantic import BaseModel
from typing import List, Optional
from .work_record import ConsolidatedReport
import datetime

class EmployeeSummary(BaseModel):
    id: int
    empnamec: str
    department_no: Optional[str] = None
    department_name: Optional[str] = None

    class Config:
        from_attributes = True

class ReportReviewCreate(BaseModel):
    rating: Optional[float] = None  # 改為Optional，允許只設定評分不留言
    comment: Optional[str] = None   # 如果要同時留言，可以使用這個欄位

class DailyReportDetail(BaseModel):
    id: int
    date: datetime.date
    status: str
    rating: Optional[float] = None  # 保留評分功能
    consolidated_content: List[ConsolidatedReport] 
    employee: EmployeeSummary
    comments_count: Optional[int] = 0  # 該日報的留言數量

    class Config:
        from_attributes = True

class EmployeeForList(BaseModel):
    id: int
    empnamec: str
    department_no: Optional[str] = None
    department_name: Optional[str] = None
    pending_reports_count: int

    class Config:
        from_attributes = True