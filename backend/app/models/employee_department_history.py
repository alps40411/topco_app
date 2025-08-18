# backend/app/models/employee_department_history.py

from sqlalchemy import Column, Integer, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class EmployeeDepartmentHistory(Base):
    __tablename__ = "employee_department_history"

    # --- 核心欄位 ---
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    
    # --- 有效期間 ---
    effective_date = Column(Date, nullable=True)  # 開始生效日期
    end_date = Column(Date, nullable=True)        # 結束日期
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- SQLAlchemy 關聯 ---
    employee = relationship("Employee", back_populates="department_histories")
    department = relationship("Department", back_populates="employee_department_histories")

    # --- 索引和約束 ---
    __table_args__ = (
        # 複合索引用於快速查詢
        {'extend_existing': True}
    )