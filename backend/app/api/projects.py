# backend/app/api/projects.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.schemas.project import Project, ProjectCreate
from app.services import projects_service
from app.core import deps
from app.models.user import User
from app.models.employee import Employee

# --- ↓↓↓ 確保這一段程式碼存在 ↓↓↓ ---
router = APIRouter(tags=["Projects"])
# --- ↑↑↑ 確保結束 ↑↑↑ ---

@router.get("/", response_model=List[Project])
async def get_active_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    取得當前用戶可用的工作計畫列表 (根據部門過濾)。
    僅限公司別A的員工。
    """
    # 如果用戶有關聯員工且為公司別A
    if current_user.employee and current_user.employee.company_code == 'A':
        return await projects_service.get_projects_for_employee(db=db, employee=current_user.employee)
    
    # 如果沒有員工資訊或非公司別A，返回所有通用專案
    return await projects_service.get_all_active(db=db)

@router.post("/", response_model=Project, status_code=201)
async def create_project(
    *,
    db: AsyncSession = Depends(get_db),
    project_in: ProjectCreate,
    current_user: User = Depends(deps.get_current_user)
):
    """
    新增一個工作計畫。
    """
    return await projects_service.create(db=db, obj_in=project_in)