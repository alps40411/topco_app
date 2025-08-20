# backend/app/models/department.py

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Department(Base):
    __tablename__ = "departments"

    # --- 核心欄位 (基於查詢1) ---
    id = Column(Integer, primary_key=True, index=True)
    deptno = Column(String(50), unique=True, index=True, nullable=False)  # 來自 deptno
    deptabbv = Column(String(100), index=True, nullable=False)  # 來自 deptabbv (部門簡稱)
    g_deptno = Column(String(50), index=True)  # 來自 g_deptno (上層部門)
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- SQLAlchemy 關聯 ---
    # 部門的員工（一對多關係）
    employees = relationship("Employee", back_populates="department")
    
    # 部門專屬的專案
    projects = relationship("Project", back_populates="department")