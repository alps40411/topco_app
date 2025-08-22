# backend/app/models/work_record.py
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from .base import Base

# 多對多關聯表：一個 DailyReport 可以包含多個 WorkRecord
report_work_record_association = Table(
    'report_work_record_association',
    Base.metadata,
    Column('daily_report_id', Integer, ForeignKey('daily_reports.id')),
    Column('work_record_id', Integer, ForeignKey('work_records.id'))
)

class WorkRecord(Base):
    __tablename__ = "work_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project", back_populates="work_records")
    content = Column(Text, nullable=False)
    ai_content = Column(Text, nullable=True) 
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 執行時間（以分鐘為單位存儲，便於計算）
    execution_time_minutes = Column(Integer, nullable=False, default=0)
    
    employee_id = Column(Integer, ForeignKey("employees.id"))

    files = relationship("FileAttachment", back_populates="work_record")



class FileAttachment(Base):
    __tablename__ = "file_attachments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String)
    size = Column(Integer)
    url = Column(String, nullable=False) # This will be the path on the server
    is_selected_for_ai = Column(Boolean, default=False)
    work_record_id = Column(Integer, ForeignKey("work_records.id"))
    work_record = relationship("WorkRecord", back_populates="files")