# backend/app/models/employee_position_history.py

from sqlalchemy import Column, Integer, String, ForeignKey, Date, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class EmployeePositionHistory(Base):
    __tablename__ = "employee_position_history"

    # --- 核心欄位 ---
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
    
    # --- 職位相關欄位 ---
    dclass = Column(String(50))           # 職務分類
    xlevel = Column(Numeric)              # 職級
    admin_rank = Column(String(50))       # 行政職等
    group_emp_no = Column(String(50))     # 集團員工編號
    company_code = Column(String(50))     # 公司代碼
    
    # --- 有效期間 ---
    effective_date = Column(Date, nullable=True)  # 開始生效日期
    end_date = Column(Date, nullable=True)        # 結束日期
    
    # --- 時間戳記 ---
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- SQLAlchemy 關聯 ---
    employee = relationship("Employee", back_populates="position_histories")
    department = relationship("Department", back_populates="employee_position_histories")

    # --- 索引和約束 ---
    __table_args__ = (
        # 複合索引用於快速查詢
        {'extend_existing': True}
    )