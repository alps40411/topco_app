# backend/app/schemas/project.py

from pydantic import BaseModel
from typing import List, Optional
from .base_schema import BaseSchema

# 我們需要先宣告 WorkRecordInList，但只宣告它的存在
# 這樣 Project 才知道它的型別，但又不會真的去 import 它
class WorkRecordInList(BaseSchema):
    id: int
    content: str

class ProjectBase(BaseModel):
    planno: str
    plan_subj_c: str
    pm_empno: str
    is_active: bool = True
    department_id: Optional[int] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(ProjectBase):
    pass

class Project(ProjectBase):
    id: int

    class Config:
        from_attributes = True