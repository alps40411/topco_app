# backend/app/schemas/employee.py
from pydantic import BaseModel
from typing import List


class EmployeeBase(BaseModel):
    name: str
    department: str

class Employee(EmployeeBase):
    id: int
    reports: List['DailyReportDetail'] = [] # <-- 關鍵修正：使用字串前向引用

    class Config:
        from_attributes = True

# --- ↓↓↓ 在所有類別定義完畢後，才進行真正的 import 並更新模型 ↓↓↓ ---
from .supervisor import DailyReportDetail
Employee.model_rebuild()