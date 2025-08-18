# backend/app/models/employee.py
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Table, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

# 員工-主管多對多關係表
employee_supervisors = Table(
    'employee_supervisors',
    Base.metadata,
    Column('employee_id', Integer, ForeignKey('employees.id', ondelete='CASCADE'), primary_key=True),
    Column('supervisor_id', Integer, ForeignKey('employees.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now())
)

class Employee(Base):
    __tablename__ = "employees"

    # --- 核心欄位 ---
    id = Column(Integer, primary_key=True, index=True)
    empno = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), index=True, nullable=False)
    
    # --- 部門相關欄位 ---
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    department_no = Column(String(50), index=True)  # 來源部門編號
    department_name = Column(String(100))  # 部門名稱（冗餘存儲）
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
    company_code = Column(String(10), nullable=False, default='A', index=True)  # 公司別限制

    # --- SQLAlchemy 關聯 ---
    user = relationship("User", back_populates="employee")
    reports = relationship("DailyReport", back_populates="employee")
    
    # 部門關係（單一部門）
    department = relationship("Department", back_populates="employees")
    
    # 保留原有的單一主管關係（向後兼容）
    supervisor = relationship("Employee", remote_side=[id], back_populates="subordinates")
    subordinates = relationship("Employee", back_populates="supervisor")
    
    # 新增多對多主管關係
    supervisors = relationship(
        "Employee",
        secondary=employee_supervisors,
        primaryjoin=id == employee_supervisors.c.employee_id,
        secondaryjoin=id == employee_supervisors.c.supervisor_id,
        back_populates="supervised_employees"
    )
    
    supervised_employees = relationship(
        "Employee",
        secondary=employee_supervisors,
        primaryjoin=id == employee_supervisors.c.supervisor_id,
        secondaryjoin=id == employee_supervisors.c.employee_id,
        back_populates="supervisors"
    )
    
    # --- 歷史記錄關聯 ---
    # 部門歷史記錄
    department_histories = relationship("EmployeeDepartmentHistory", back_populates="employee")
    
    # 主管歷史記錄（作為員工）
    supervisor_histories = relationship(
        "EmployeeSupervisorHistory", 
        foreign_keys="EmployeeSupervisorHistory.employee_id",
        back_populates="employee"
    )
    
    # 主管歷史記錄（作為主管）
    supervised_histories = relationship(
        "EmployeeSupervisorHistory",
        foreign_keys="EmployeeSupervisorHistory.supervisor_id", 
        back_populates="supervisor"
    )
    
    # 職位歷史記錄
    position_histories = relationship("EmployeePositionHistory", back_populates="employee")
