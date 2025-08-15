# backend/app/models/employee.py
from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from .base import Base

class Employee(Base):
    __tablename__ = "employees"

    # --- 核心欄位 ---
    id = Column(Integer, primary_key=True, index=True)
    empno = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), index=True, nullable=False)
    
    # --- 部門相關欄位 ---
    department_no = Column(String(50), index=True)
    department_name = Column(String(100))
    department_abbr = Column(String(50))
    group_dept_no = Column(String(50))

    # --- 職級與分類 ---
    dclass = Column(String(50))
    xlevel = Column(String(50))
    admin_rank = Column(String(50))

    # --- 公司與群組資訊 ---
    company_code = Column(String(50))
    group_emp_no = Column(String(50))

    # --- 狀態與關聯 ---
    quit_date = Column(Date, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    supervisor_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # --- SQLAlchemy 關聯 ---
    user = relationship("User", back_populates="employee")
    reports = relationship("DailyReport", back_populates="employee")
    supervisor = relationship("Employee", remote_side=[id], back_populates="subordinates")
    subordinates = relationship("Employee", back_populates="supervisor")
