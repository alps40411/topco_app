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
    query = select(Project).where(Project.is_active == True).order_by(Project.name)
    result = await db.execute(query)
    return result.scalars().all()

async def get_projects_for_employee(db: AsyncSession, employee: Employee) -> List[Project]:
    """取得員工可用的工作計畫 (部門專屬 + 通用專案)"""
    
    # 如果員工有部門ID，返回該部門專案 + 通用專案
    if employee.department_id:
        query = select(Project).where(
            Project.is_active == True,
            or_(
                Project.department_id == employee.department_id,
                Project.department_id.is_(None)
            )
        ).options(selectinload(Project.department)).order_by(Project.name)
    else:
        # 如果沒有部門，只返回通用專案
        query = select(Project).where(
            Project.is_active == True,
            Project.department_id.is_(None)
        ).order_by(Project.name)
    
    result = await db.execute(query)
    return result.scalars().all()

async def create(db: AsyncSession, *, obj_in: ProjectCreate) -> Project:
    db_obj = Project(name=obj_in.name, is_active=obj_in.is_active)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj