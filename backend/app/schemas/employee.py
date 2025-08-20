# backend/app/schemas/employee.py
from pydantic import BaseModel
from typing import List, Optional
import datetime

# --- Base Schema --- 
class EmployeeBase(BaseModel):
    empno: str
    empnamec: str
    cocode: Optional[str] = 'A'
    deptno: Optional[str] = None
    adm_rank: Optional[str] = None
    sop_role: Optional[str] = None
    dutyscript: Optional[str] = None  # 職稱
    firstnamec: Optional[str] = None
    lastnamec: Optional[str] = None
    g_deptno: Optional[str] = None
    tam_pass: Optional[str] = None
    deptabbv: Optional[str] = None
    workcls: Optional[str] = None
    department_id: Optional[int] = None

# --- Create Schema --- 
class EmployeeCreate(EmployeeBase):
    pass

# --- Update Schema --- 
class EmployeeUpdate(EmployeeBase):
    pass

# --- Full Schema (from DB) --- 
class Employee(EmployeeBase):
    id: int
    user_id: Optional[int] = None
    reports: List['DailyReportDetail'] = []

    class Config:
        from_attributes = True

# --- Forward Reference Resolution --- 
from .supervisor import DailyReportDetail
Employee.model_rebuild()

# --- Schema for User object --- 
class EmployeeForUser(BaseModel):
    id: int
    empno: str
    empnamec: str # Made empnamec optional
    dutyscript: Optional[str] = None  # 職稱
    deptabbv: Optional[str] = None    # 部門簡稱

    class Config:
        from_attributes = True