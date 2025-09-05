# backend/app/schemas/project.py
from pydantic import BaseModel
from typing import Optional

class Project(BaseModel):
    id: int
    planno: Optional[str] = None
    plan_subj_c: str
    pm_empno: Optional[str] = None
    is_active: bool = True
    department_id: Optional[int] = None

    class Config:
        from_attributes = True

