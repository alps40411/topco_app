# backend/app/services/supervisor_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import datetime

from app.models import Employee, DailyReport, ReportStatus, ReviewComment, ReportApproval, ApprovalStatus, Supervisor
from app.schemas.supervisor import ReportReviewCreate
from app.schemas.review_comment import ReviewCommentCreate
from app.schemas.report_approval import SupervisorApprovalInfo
from app.services import comment_service

async def get_direct_subordinates(db: AsyncSession, supervisor_id: int) -> List[int]:
    """使用新的主管關係表獲取直屬下級員工ID"""
    # 首先獲取主管的 empno
    supervisor_query = select(Employee.empno).where(Employee.id == supervisor_id)
    supervisor_result = await db.execute(supervisor_query)
    supervisor_empno = supervisor_result.scalar_one_or_none()
    
    if not supervisor_empno:
        return []
    
    # 查詢主管關係表
    query = (
        select(Employee.id)
        .join(Supervisor, Employee.empno == Supervisor.empno)
        .where(Supervisor.supervisor == supervisor_empno)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_all_subordinates(db: AsyncSession, supervisor_id: int, visited_ids: set = None) -> List[int]:
    """遞歸獲取所有下級員工ID（包括間接下級），排除離職員工"""
    if visited_ids is None:
        visited_ids = set()
    
    # 防止無限遞歸
    if supervisor_id in visited_ids:
        return []
    
    visited_ids.add(supervisor_id)
    subordinate_ids = []
    
    # 使用多對多關係獲取直屬下級
    direct_subordinates = await get_direct_subordinates(db, supervisor_id)
    
    for subordinate_id in direct_subordinates:
        subordinate_ids.append(subordinate_id)
        # 遞歸獲取下級的下級
        indirect_subordinates = await get_all_subordinates(db, subordinate_id, visited_ids.copy())
        subordinate_ids.extend(indirect_subordinates)
    
    return subordinate_ids

async def get_employees_with_pending_reports(db: AsyncSession, *, supervisor_id: int) -> List[Employee]:
    """獲取所有下級員工（包括多級下級）有待該主管審核的報告"""
    print(f"[INFO] 查詢主管 {supervisor_id} 的所有下級員工")
    
    # 獲取所有下級員工ID（包括多級）
    all_subordinate_ids = await get_all_subordinates(db, supervisor_id)
    print(f"[INFO] 找到 {len(all_subordinate_ids)} 個下級員工: {all_subordinate_ids}")
    
    if not all_subordinate_ids:
        return []
    
    # 查詢這些員工的信息
    query = (
        select(Employee)
        .where(Employee.id.in_(all_subordinate_ids))
        .order_by(Employee.id)
    )
    
    result = await db.execute(query)
    employees = result.scalars().unique().all()
    
    # 為每個員工計算該主管未審核的報告數量
    for emp in employees:
        # 查詢該員工的所有報告，並檢查該主管是否已審核
        reports_query = (
            select(DailyReport)
            .where(DailyReport.employee_id == emp.id)
            .options(selectinload(DailyReport.approvals))
        )
        reports_result = await db.execute(reports_query)
        reports = reports_result.scalars().unique().all()
        
        pending_count = 0
        for report in reports:
            # 檢查該主管是否已審核此報告
            supervisor_approval = None
            for approval in report.approvals:
                if approval.supervisor_id == supervisor_id:
                    supervisor_approval = approval
                    break
            
            # 如果沒有審核記錄或狀態為pending，則計入待審核
            if supervisor_approval is None or supervisor_approval.status == ApprovalStatus.pending:
                pending_count += 1
        
        emp.pending_reports_count = pending_count
        print(f"   [INFO] 員工 {emp.empnamec} ({emp.id}): {emp.pending_reports_count} 個待主管{supervisor_id}審核的報告")
        
    return employees

async def get_employee_details(db: AsyncSession, *, employee_id: int) -> Optional[Employee]:
    query = select(Employee).where(Employee.id == employee_id).options(
        selectinload(Employee.reports)
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()

async def can_supervisor_review_employee(db: AsyncSession, supervisor_id: int, employee_id: int) -> bool:
    """檢查主管是否有權限審核該員工的報告（基於新的主管關係表，包括直接和間接下級）"""
    # 獲取主管和員工的 empno
    supervisor_query = select(Employee.empno).where(Employee.id == supervisor_id)
    supervisor_result = await db.execute(supervisor_query)
    supervisor_empno = supervisor_result.scalar_one_or_none()
    
    employee_query = select(Employee.empno).where(Employee.id == employee_id)
    employee_result = await db.execute(employee_query)
    employee_empno = employee_result.scalar_one_or_none()
    
    if not supervisor_empno or not employee_empno:
        return False
    
    # 檢查直接主管關係
    direct_query = select(Supervisor).where(
        Supervisor.supervisor == supervisor_empno,
        Supervisor.empno == employee_empno
    )
    direct_result = await db.execute(direct_query)
    if direct_result.scalar_one_or_none():
        return True
    
    # 如果不是直接關係，檢查是否為間接下級
    all_subordinate_ids = await get_all_subordinates(db, supervisor_id)
    return employee_id in all_subordinate_ids


async def review_daily_report(db: AsyncSession, *, report_id: int, review_in: ReportReviewCreate, reviewer) -> Optional[DailyReport]:
    """
    新的多主管獨立審核機制：每個主管都有獨立的審核狀態
    """
    query = select(DailyReport).where(DailyReport.id == report_id).options(
        selectinload(DailyReport.employee),
        selectinload(DailyReport.approvals)
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    if not report:
        return None
    
    supervisor_id = reviewer.employee.id
    
    # 檢查審核權限
    if not await can_supervisor_review_employee(db, supervisor_id, report.employee.id):
        print(f"[ERROR] 主管 {supervisor_id} 沒有權限審核員工 {report.employee.id} 的報告")
        return None
    
    # 檢查是否已經審核過
    existing_approval = None
    for approval in report.approvals:
        if approval.supervisor_id == supervisor_id:
            existing_approval = approval
            break
    
    if existing_approval and existing_approval.status != ApprovalStatus.pending:
        print(f"[ERROR] 主管 {supervisor_id} 已經審核過此報告 (狀態: {existing_approval.status})")
        raise ValueError(f"您已經審核過此日報，不能重複審核")
    
    # 建立或更新審核記錄
    if existing_approval:
        # 更新現有記錄
        #有評分就是已經審核過
        existing_approval.status = ApprovalStatus.approved if review_in.rating else ApprovalStatus.pending
        existing_approval.rating = review_in.rating
        existing_approval.feedback = review_in.comment
        existing_approval.approved_at = datetime.datetime.utcnow()
        approval_record = existing_approval
    else:
        # 建立新記錄
        approval_record = ReportApproval(
            report_id=report_id,
            supervisor_id=supervisor_id,
            status=ApprovalStatus.approved if review_in.rating else ApprovalStatus.pending,
            rating=review_in.rating,
            feedback=review_in.comment,
            approved_at=datetime.datetime.utcnow()
        )
        db.add(approval_record)
    
    # 為相容性，仍然建立評論記錄
    if review_in.comment and review_in.comment.strip():
        comment_create = ReviewCommentCreate(
            content=review_in.comment,
            rating=review_in.rating
        )
        await comment_service.create_comment(
            db=db,
            report_id=report_id,
            user=reviewer,
            comment_in=comment_create
        )
    elif review_in.rating is not None:
        rating_text = f"評分：{review_in.rating} 分"
        comment_create = ReviewCommentCreate(
            content=rating_text,
            rating=review_in.rating
        )
        await comment_service.create_comment(
            db=db,
            report_id=report_id,
            user=reviewer,
            comment_in=comment_create
        )
    
    await db.commit()
    await db.refresh(report)
    return report

async def create_approval_records_for_supervisors(db: AsyncSession, report_id: int, employee_id: int):
    """為所有主管建立初始的審核記錄"""
    # 獲取員工的 empno
    employee_query = select(Employee.empno).where(Employee.id == employee_id)
    employee_result = await db.execute(employee_query)
    employee_empno = employee_result.scalar_one_or_none()
    
    if not employee_empno:
        return
    
    # 從主管關係表獲取該員工的所有主管
    supervisors_query = (
        select(Employee.id)
        .join(Supervisor, Employee.empno == Supervisor.supervisor)
        .where(Supervisor.empno == employee_empno)
    )
    result = await db.execute(supervisors_query)
    supervisor_ids = result.scalars().all()
    
    # 為每個主管建立審核記錄
    for supervisor_id in supervisor_ids:
        # 檢查是否已存在記錄
        existing_query = select(ReportApproval).where(
            ReportApproval.report_id == report_id,
            ReportApproval.supervisor_id == supervisor_id
        )
        existing_result = await db.execute(existing_query)
        if not existing_result.scalar_one_or_none():
            approval = ReportApproval(
                report_id=report_id,
                supervisor_id=supervisor_id,
                status=ApprovalStatus.pending
            )
            db.add(approval)
    
    await db.commit()

async def submit_daily_report(db: AsyncSession, *, employee_id: int, submitted_reports: List[dict]) -> DailyReport:
    """
    建立一筆新的 DailyReport，並為所有主管建立審核記錄。
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
    
    # 為所有主管建立審核記錄
    await create_approval_records_for_supervisors(db, db_report.id, employee_id)

    final_query = select(DailyReport).where(DailyReport.id == db_report.id).options(
        selectinload(DailyReport.employee)
    )
    final_result = await db.execute(final_query)
    return final_result.scalar_one()


async def get_reports_by_date(db: AsyncSession, *, target_date: datetime.date) -> List[DailyReport]:
    """
    根據指定日期，取得當天所有的日報，並包含提交日報的員工資訊和留言數量。
    """
    query = select(DailyReport).where(
        DailyReport.date == target_date
    ).options(
        selectinload(DailyReport.employee),  # 同時載入關聯的員工資訊
        selectinload(DailyReport.comments)   # 載入留言以計算數量
    ).order_by(
        DailyReport.status.asc(),  # 讓「待審核」的排在前面
        DailyReport.employee_id.asc()
    )
    result = await db.execute(query)
    reports = result.scalars().unique().all()
    
    # 為每個日報計算留言數量
    for report in reports:
        report.comments_count = len(report.comments) if report.comments else 0
    
    return reports

async def get_report_approval_status(db: AsyncSession, report_id: int) -> List[SupervisorApprovalInfo]:
    """獲取報告的所有主管審核狀態"""
    query = (
        select(ReportApproval, Employee)
        .join(Employee, ReportApproval.supervisor_id == Employee.id)
        .where(ReportApproval.report_id == report_id)
        .order_by(Employee.empnamec)
    )
    
    result = await db.execute(query)
    approval_data = result.all()
    
    approval_info = []
    for approval, supervisor in approval_data:
        approval_info.append(SupervisorApprovalInfo(
            supervisor_id=supervisor.id,
            supervisor_name=supervisor.empnamec,
            supervisor_empno=supervisor.empno,
            status=approval.status,
            approved_at=approval.approved_at,
            rating=approval.rating,
            feedback=approval.feedback
        ))
    
    return approval_info