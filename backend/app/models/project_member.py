# backend/app/models/project_member.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class ProjectMember(Base):
    __tablename__ = "project_members"

    # --- 核心欄位 (基於查詢4：員工專案參與關係) ---
    id = Column(Integer, primary_key=True, index=True)
    planno = Column(String(50), ForeignKey("projects.planno"), nullable=False, index=True)  # 來自 planno
    part_empno = Column(String(50), ForeignKey("employees.empno"), nullable=False, index=True)  # 來自 part_empno (參與成員工號)
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- 唯一約束 (複合主鍵概念) ---
    __table_args__ = (
        {'extend_existing': True}
    )

    # --- SQLAlchemy 關聯 ---
    # 專案
    project = relationship("Project", back_populates="project_members")
    
    # 員工 (專案成員)
    employee = relationship("Employee", back_populates="project_memberships")