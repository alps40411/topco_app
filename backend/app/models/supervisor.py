# backend/app/models/supervisor.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Supervisor(Base):
    __tablename__ = "supervisors"

    # --- 核心欄位 (基於查詢2：員工主管層級關係) ---
    id = Column(Integer, primary_key=True, index=True)
    supervisor = Column(String(50), ForeignKey("employees.empno"), nullable=False, index=True)  # 來自 supervisor
    empno = Column(String(50), ForeignKey("employees.empno"), nullable=False, index=True)  # 來自 empno
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- 唯一約束 (複合主鍵概念) ---
    __table_args__ = (
        {'extend_existing': True}
    )

    # --- SQLAlchemy 關聯 ---
    # 員工 (被管理者)
    employee = relationship(
        "Employee", 
        foreign_keys=[empno],
        back_populates="supervisor_relations"
    )
    
    # 主管 (管理者)
    supervisor_employee = relationship(
        "Employee",
        foreign_keys=[supervisor], 
        back_populates="supervised_relations"
    )