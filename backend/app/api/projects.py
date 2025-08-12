# backend/app/api/projects.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.project import Project, ProjectCreate
from app.services import projects_service
from app.core import deps
from app.models.user import User

# --- ↓↓↓ 確保這一段程式碼存在 ↓↓↓ ---
router = APIRouter(tags=["Projects"])
# --- ↑↑↑ 確保結束 ↑↑↑ ---

@router.get("/", response_model=List[Project])
async def get_active_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    取得所有啟用中的工作計畫列表 (用於下拉選單)。
    """
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