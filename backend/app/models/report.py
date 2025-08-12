# backend/app/models/report.py
import datetime
from sqlalchemy import Column, Integer, String, Date, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .base import Base
from .work_record import report_work_record_association
import enum

class ReportStatus(enum.Enum):
    pending = "pending"
    reviewed = "reviewed"

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today, nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.pending, nullable=False)
    rating = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    consolidated_content = Column(JSONB)
    
    employee_id = Column(Integer, ForeignKey("employees.id"))
    employee = relationship("Employee", back_populates="reports")

    # The content of the report will be consolidated into a JSON or Text field
    # For simplicity, we assume the frontend sends consolidated data to save.
    # A more robust approach would be linking work_records.
    projects = relationship(
        "WorkRecord",
        secondary=report_work_record_association,
        backref="daily_reports"
    )