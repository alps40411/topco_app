# backend/app/models/department.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Department(Base):
    __tablename__ = "departments"

    # --- 核心欄位 ---
    id = Column(Integer, primary_key=True, index=True)
    dept_no = Column(String(50), unique=True, index=True, nullable=False)
    dept_name = Column(String(200), index=True, nullable=False)
    dept_abbr = Column(String(100))
    group_dept_no = Column(String(50))
    company_code = Column(String(50))
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- SQLAlchemy 關聯 ---
    # 部門的員工（一對多關係）
    employees = relationship("Employee", back_populates="department")
    
    # 部門的員工歷史記錄
    employee_department_histories = relationship("EmployeeDepartmentHistory", back_populates="department")
    
    # 部門的職位歷史記錄
    employee_position_histories = relationship("EmployeePositionHistory", back_populates="department")
    
    # 部門專屬的專案
    projects = relationship("Project", back_populates="department")