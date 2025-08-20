# backend/app/services/projects_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import List

from app.models.project import Project
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.project import ProjectCreate

async def get_all_active(db: AsyncSession) -> List[Project]:
    query = select(Project).where(Project.is_active == True).order_by(Project.plan_subj_c)
    result = await db.execute(query)
    return result.scalars().all()

# backend/app/services/projects_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import List

from app.models.project import Project
from app.models.department import Department
from app.models.employee import Employee
from app.schemas.project import ProjectCreate

async def get_all_active(db: AsyncSession) -> List[Project]:
    query = select(Project).where(Project.is_active == True).order_by(Project.plan_subj_c)
    result = await db.execute(query)
    return result.scalars().all()

async def get_projects_for_employee(db: AsyncSession, employee: Employee) -> List[Project]:
    """
    (優化後) 取得員工可用的工作計畫，使用單一查詢。
    基於：
    1. 員工作為專案經理
    2. 員工是專案成員
    3. 專案屬於員工部門，或是通用專案 (無部門)
    """
    from app.models import ProjectMember

    # 建立所有可能的條件
    conditions = [
        # 條件1: 員工作為專案經理
        Project.pm_empno == employee.empno,
        # 條件2: 員工是專案成員 (透過 join 達成)
        ProjectMember.part_empno == employee.empno
    ]

    # 條件3: 如果員工有部門，則加入部門相關的專案
    if employee.department_id:
        conditions.append(
            or_(
                Project.department_id == employee.department_id,
                Project.department_id.is_(None)  # 通用專案
            )
        )

    # 建立主查詢
    query = (
        select(Project)
        # 使用 outerjoin，因為一個專案可能符合 PM 或部門條件，但不一定符合成員條件
        .outerjoin(ProjectMember, Project.planno == ProjectMember.planno)
        .where(
            Project.is_active == True,
            or_(*conditions)  # 將所有條件用 OR 組合起來
        )
        .options(selectinload(Project.department))
        .distinct()  # 確保結果唯一 (因為一個專案可能同時滿足多個條件)
        .order_by(Project.plan_subj_c)
    )

    # 執行一次查詢
    result = await db.execute(query)
    return result.scalars().all()

async def create(db: AsyncSession, *, obj_in: ProjectCreate) -> Project:
    db_obj = Project(
        planno=obj_in.planno,
        plan_subj_c=obj_in.plan_subj_c,
        pm_empno=obj_in.pm_empno,
        is_active=obj_in.is_active,
        department_id=obj_in.department_id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
