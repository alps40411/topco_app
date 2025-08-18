# backend/app/models/project.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # 部門關聯 (可選，如果為None表示所有部門都可使用)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    
    # 關聯
    department = relationship("Department", back_populates="projects")
    work_records = relationship("WorkRecord", back_populates="project")