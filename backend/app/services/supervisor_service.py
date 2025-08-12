# backend/app/services/supervisor_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import datetime

from app.models import Employee, DailyReport, ReportStatus
from app.schemas.supervisor import ReportReviewCreate

async def get_employees_with_pending_reports(db: AsyncSession) -> List[Employee]:
    query = select(Employee).options(selectinload(Employee.reports)).order_by(Employee.id)
    result = await db.execute(query)
    employees = result.scalars().unique().all()
    
    for emp in employees:
        emp.pending_reports_count = sum(1 for report in emp.reports if report.status == ReportStatus.pending)
        
    return employees

async def get_employee_details(db: AsyncSession, *, employee_id: int) -> Optional[Employee]:

    query = select(Employee).where(Employee.id == employee_id).options(
        selectinload(Employee.reports)
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()


async def review_daily_report(db: AsyncSession, *, report_id: int, review_in: ReportReviewCreate) -> Optional[DailyReport]:
    report = await db.get(DailyReport, report_id)
    if not report:
        return None
    
    report.status = ReportStatus.reviewed
    report.rating = review_in.rating
    report.feedback = review_in.feedback
    
    await db.commit()
    await db.refresh(report)
    return report

async def submit_daily_report(db: AsyncSession, *, employee_id: int, submitted_reports: List[dict]) -> DailyReport:
    """
    建立一筆新的 DailyReport，並將當天所有彙整報告存入 JSON 欄位。
    """
    today = datetime.date.today()
    query = select(DailyReport).where(
        DailyReport.employee_id == employee_id,
        DailyReport.date == today
    )
    result = await db.execute(query)
    existing_report = result.scalar_one_or_none()

    if existing_report:
        existing_report.consolidated_content = submitted_reports
        existing_report.status = ReportStatus.pending
        db_report = existing_report
    else:
        db_report = DailyReport(
            employee_id=employee_id,
            date=today,
            consolidated_content=submitted_reports,
            status=ReportStatus.pending
        )
        db.add(db_report)
    
    await db.commit()
    await db.refresh(db_report)


    final_query = select(DailyReport).where(DailyReport.id == db_report.id).options(
        selectinload(DailyReport.employee)
    )
    final_result = await db.execute(final_query)
    return final_result.scalar_one()


async def get_reports_by_date(db: AsyncSession, *, target_date: datetime.date) -> List[DailyReport]:
    """
    根據指定日期，取得當天所有的日報，並包含提交日報的員工資訊。
    """
    query = select(DailyReport).where(
        DailyReport.date == target_date
    ).options(
        selectinload(DailyReport.employee) # 同時載入關聯的員工資訊
    ).order_by(
        DailyReport.status.asc(), # 讓「待審核」的排在前面
        DailyReport.employee_id.asc()
    )
    result = await db.execute(query)
    return result.scalars().unique().all()