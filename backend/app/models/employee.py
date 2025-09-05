# backend/app/models/employee.py

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    empno = Column(String, unique=True, index=True, nullable=False)
    empnamec = Column(String, index=True)
    cocode = Column(String)
    deptabbv = Column(String)
    dutyscript = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    user = relationship("User", back_populates="employee")