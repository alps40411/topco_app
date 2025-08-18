# backend/app/services/supervisor_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import datetime

from app.models import Employee, DailyReport, ReportStatus, ReviewComment
from app.models.employee import employee_supervisors
from app.schemas.supervisor import ReportReviewCreate
from app.schemas.review_comment import ReviewCommentCreate
from app.services import comment_service

async def get_direct_subordinates(db: AsyncSession, supervisor_id: int) -> List[int]:
    """使用多對多關係獲取直屬下級員工ID，排除離職員工"""
    query = (
        select(Employee.id)
        .select_from(employee_supervisors)
        .join(Employee, Employee.id == employee_supervisors.c.employee_id)
        .where(
            employee_supervisors.c.supervisor_id == supervisor_id,
            Employee.quit_date.is_(None)  # 排除離職員工
        )
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
    """獲取所有下級員工（包括多級下級）的待審核報告"""
    print(f"[INFO] 查詢主管 {supervisor_id} 的所有下級員工")
    
    # 獲取所有下級員工ID（包括多級）
    all_subordinate_ids = await get_all_subordinates(db, supervisor_id)
    print(f"[INFO] 找到 {len(all_subordinate_ids)} 個下級員工: {all_subordinate_ids}")
    
    if not all_subordinate_ids:
        return []
    
    # 查詢這些員工的信息和報告
    query = (
        select(Employee)
        .where(Employee.id.in_(all_subordinate_ids))
        .options(selectinload(Employee.reports))
        .order_by(Employee.id)
    )
    
    result = await db.execute(query)
    employees = result.scalars().unique().all()
    
    for emp in employees:
        emp.pending_reports_count = sum(1 for report in emp.reports if report.status == ReportStatus.pending)
        print(f"   [INFO] 員工 {emp.name} ({emp.id}): {emp.pending_reports_count} 個待審核報告")
        
    return employees

async def get_employee_details(db: AsyncSession, *, employee_id: int) -> Optional[Employee]:
    query = select(Employee).where(Employee.id == employee_id).options(
        selectinload(Employee.reports)
    )
    result = await db.execute(query)
    return result.scalars().unique().one_or_none()

async def can_supervisor_review_employee(db: AsyncSession, supervisor_id: int, employee_id: int) -> bool:
    """檢查主管是否有權限審核該員工的報告（多對多關係，包括直接和間接下級）"""
    # 先檢查是否為直接主管關係
    direct_query = select(employee_supervisors.c.employee_id).where(
        employee_supervisors.c.supervisor_id == supervisor_id,
        employee_supervisors.c.employee_id == employee_id
    )
    direct_result = await db.execute(direct_query)
    if direct_result.scalar_one_or_none():
        return True
    
    # 如果不是直接關係，檢查是否為間接下級
    all_subordinate_ids = await get_all_subordinates(db, supervisor_id)
    return employee_id in all_subordinate_ids


async def review_daily_report(db: AsyncSession, *, report_id: int, review_in: ReportReviewCreate, reviewer) -> Optional[DailyReport]:
    """
    審核日報：設定評分並建立對話記錄。支援多級主管評分機制。
    """
    query = select(DailyReport).where(DailyReport.id == report_id).options(
        selectinload(DailyReport.employee),
        selectinload(DailyReport.comments)
    )
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    if not report:
        return None
    
    # 檢查審核權限：確認當前用戶是該員工的主管（包括多級關係）
    if not await can_supervisor_review_employee(db, reviewer.employee.id, report.employee.id):
        print(f"[ERROR] 用戶 {reviewer.id} 沒有權限審核員工 {report.employee.id} 的報告")
        return None
    
    print(f"[SUCCESS] 用戶 {reviewer.id} 有權限審核員工 {report.employee.id} 的報告")
    
    # 檢查是否已經評分過：防止同一主管重複評分
    existing_review = None
    for comment in report.comments:
        if (comment.user_id == reviewer.id and 
            comment.rating is not None and 
            comment.rating > 0):
            existing_review = comment
            break
    
    if existing_review:
        print(f"[ERROR] 主管 {reviewer.id} 已經對此報告評分過了 (評分: {existing_review.rating})")
        raise ValueError(f"您已經對此日報評分過了，不能重複評分")
    
    print(f"[SUCCESS] 主管 {reviewer.id} 尚未評分，可以進行審核")
    
    # 如果提供評分，計算多對多主管平均評分
    if review_in.rating is not None:
        # 取得該員工的所有直接主管ID
        employee_supervisors_query = select(employee_supervisors.c.supervisor_id).where(
            employee_supervisors.c.employee_id == report.employee.id
        )
        supervisor_ids_result = await db.execute(employee_supervisors_query)
        employee_supervisor_ids = set(supervisor_ids_result.scalars().all())
        print(f"[INFO] 員工 {report.employee.id} 的所有主管: {employee_supervisor_ids}")
        
        # 取得所有主管的評分
        supervisor_ratings = []
        
        # 從現有評論中取得其他主管的評分（僅限該員工的直接主管）
        for comment in report.comments:
            if (comment.rating is not None and 
                comment.rating > 0 and 
                comment.user_id != reviewer.id):  # 排除當前主管的舊評分
                
                # 檢查該評論作者是否為此員工的直接主管
                comment_author_employee_id = comment.author.employee.id if comment.author and comment.author.employee else None
                if comment_author_employee_id in employee_supervisor_ids:
                    supervisor_ratings.append(comment.rating)
                    print(f"[INFO] 加入主管 {comment_author_employee_id} 的評分: {comment.rating}")
        
        # 加入當前主管的評分
        supervisor_ratings.append(review_in.rating)
        print(f"[INFO] 加入當前主管 {reviewer.employee.id} 的評分: {review_in.rating}")
        
        # 計算平均評分
        if supervisor_ratings:
            average_rating = sum(supervisor_ratings) / len(supervisor_ratings)
            report.rating = round(average_rating, 2)
            print(f"[INFO] 多對多主管評分計算: {supervisor_ratings} -> 平均: {report.rating}")
    
    # 更新狀態為已審核
    report.status = ReportStatus.reviewed
    
    # 建立審核對話記錄（包含評分和留言）
    if review_in.comment and review_in.comment.strip():
        comment_create = ReviewCommentCreate(
            content=review_in.comment, 
            rating=review_in.rating  # 將評分也包含在對話記錄中
        )
        await comment_service.create_comment(
            db=db,
            report_id=report_id,
            user=reviewer,
            comment_in=comment_create
        )
    elif review_in.rating is not None:
        # 如果只有評分沒有留言，建立一個評分記錄
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