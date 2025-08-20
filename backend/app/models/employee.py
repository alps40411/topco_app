# backend/app/models/employee.py
from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Employee(Base):
    __tablename__ = "employees"

    # --- 核心欄位 (基於查詢1：員工主檔) ---
    id = Column(Integer, primary_key=True, index=True)
    cocode = Column(String(10), nullable=False, default='A', index=True)  # 來自 cocode
    empno = Column(String(50), unique=True, index=True, nullable=False)  # 來自 empno
    empnamec = Column(String(100), index=True, nullable=False)  # 來自 empnamec
    deptno = Column(String(50), index=True)  # 來自 deptno
    adm_rank = Column(String(50))  # 來自 adm_rank
    sop_role = Column(String(50))  # 來自 sop_role
    dutyscript = Column(String(100))  # 來自 dutyscript (職稱)
    firstnamec = Column(String(50))  # 來自 firstnamec
    lastnamec = Column(String(50))  # 來自 lastnamec
    g_deptno = Column(String(50))  # 來自 g_deptno
    tam_pass = Column(String(100))  # 來自 tam_pass
    deptabbv = Column(String(50))  # 來自 deptabbv
    workcls = Column(String(50))  # 來自 workcls

    # --- 部門關聯 ---
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    
    # --- 狀態與關聯 ---
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- SQLAlchemy 關聯 ---
    user = relationship("User", back_populates="employee")
    reports = relationship("DailyReport", back_populates="employee")
    
    # 部門關係
    department = relationship("Department", back_populates="employees")
    
    # 主管關係 (作為員工)
    supervisor_relations = relationship(
        "Supervisor", 
        foreign_keys="Supervisor.empno",
        back_populates="employee"
    )
    
    # 主管關係 (作為主管)
    supervised_relations = relationship(
        "Supervisor",
        foreign_keys="Supervisor.supervisor",
        back_populates="supervisor_employee"
    )
    
    # 專案成員關係
    project_memberships = relationship("ProjectMember", back_populates="employee")
    
    # 專案經理關係
    managed_projects = relationship("Project", back_populates="project_manager")
