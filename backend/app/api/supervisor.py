# backend/app/api/supervisor.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import datetime
from app.core.database import get_db
from app.schemas.supervisor import EmployeeForList, DailyReportDetail, ReportReviewCreate
from app.schemas.employee import Employee as EmployeeDetailSchema
from app.schemas.work_record import ConsolidatedReport
from app.services import supervisor_service
from app.core import deps
from app.models.user import User

router = APIRouter(tags=["Supervisor"])

@router.get("/employees", response_model=List[EmployeeForList])
async def get_employees_for_supervisor(db: AsyncSession = Depends(get_db)):
    employees = await supervisor_service.get_employees_with_pending_reports(db=db)
    return employees

@router.get("/employees/{employee_id}", response_model=EmployeeDetailSchema)
async def get_employee_details_for_supervisor(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    employee = await supervisor_service.get_employee_details(db=db, employee_id=employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="找不到該員工")
    return employee

@router.put("/reports/{report_id}/review", response_model=DailyReportDetail)
async def review_report(
    report_id: int,
    review_in: ReportReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    reviewed_report = await supervisor_service.review_daily_report(db=db, report_id=report_id, review_in=review_in)
    if not reviewed_report:
        raise HTTPException(status_code=404, detail="找不到該日報")
    return reviewed_report

@router.post("/reports/submit", response_model=DailyReportDetail)
async def submit_daily_report_for_review(
    submitted_reports: List[ConsolidatedReport],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    員工提交當日的最終版日報以供審核。
    """
    employee_id = current_user.employee.id
    # 將 Pydantic 模型轉換為字典列表，以便存入 JSONB
    reports_data = [r.model_dump() for r in submitted_reports]
    
    new_daily_report = await supervisor_service.submit_daily_report(
        db=db, 
        employee_id=employee_id, 
        submitted_reports=reports_data
    )
    return new_daily_report

@router.get("/reports-by-date", response_model=List[DailyReportDetail])
async def get_daily_reports_by_date(
    date: datetime.date,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    根據指定日期，獲取當天所有已提交的日報列表。
    """
    return await supervisor_service.get_reports_by_date(db=db, target_date=date)