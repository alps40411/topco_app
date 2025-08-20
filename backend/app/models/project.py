# backend/app/models/project.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Project(Base):
    __tablename__ = "projects"

    # --- 核心欄位 (基於查詢3：專案主檔) ---
    id = Column(Integer, primary_key=True, index=True)
    planno = Column(String(50), unique=True, index=True, nullable=False)  # 來自 planno
    plan_subj_c = Column(String(200), index=True, nullable=False)  # 來自 plan_subj_c (專案名稱)
    pm_empno = Column(String(50), ForeignKey("employees.empno"), nullable=False, index=True)  # 來自 pm_empno (專案經理)
    
    # --- 狀態欄位 ---
    is_active = Column(Boolean, default=True)
    
    # --- 部門關聯 (可選，如果為None表示所有部門都可使用) ---
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # --- SQLAlchemy 關聯 ---
    department = relationship("Department", back_populates="projects")
    work_records = relationship("WorkRecord", back_populates="project")
    
    # --- 屬性別名 ---
    @property
    def name(self):
        """為了與現有代碼兼容，提供 name 屬性作為 plan_subj_c 的別名"""
        return self.plan_subj_c
    
    # 專案經理關係
    project_manager = relationship("Employee", back_populates="managed_projects")
    
    # 專案成員關係
    project_members = relationship("ProjectMember", back_populates="project")