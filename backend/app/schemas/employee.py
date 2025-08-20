# backend/app/schemas/employee.py
from pydantic import BaseModel
from typing import List, Optional
import datetime

# --- Base Schema --- 
class EmployeeBase(BaseModel):
    empno: str
    name: str
    department_no: Optional[str] = None
    department_name: Optional[str] = None
    department_abbr: Optional[str] = None
    group_dept_no: Optional[str] = None
    dclass: Optional[str] = None
    xlevel: Optional[str] = None
    admin_rank: Optional[str] = None
    company_code: Optional[str] = None
    group_emp_no: Optional[str] = None
    quit_date: Optional[datetime.date] = None
    supervisor_id: Optional[int] = None

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

    class Config:
        from_attributes = True

# --- Schema for User object --- 
class EmployeeForUser(BaseModel):
    id: int

    class Config:
        from_attributes = True