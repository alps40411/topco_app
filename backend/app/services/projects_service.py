# backend/app/services/projects_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.models.project import Project
from app.schemas.project import ProjectCreate

async def get_all_active(db: AsyncSession) -> List[Project]:
    query = select(Project).where(Project.is_active == True).order_by(Project.name)
    result = await db.execute(query)
    return result.scalars().all()

async def create(db: AsyncSession, *, obj_in: ProjectCreate) -> Project:
    db_obj = Project(name=obj_in.name, is_active=obj_in.is_active)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj