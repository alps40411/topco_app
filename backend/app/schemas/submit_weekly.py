# backend/app/schemas/submit_weekly.py

from pydantic import BaseModel
from typing import Optional, List


class WeeklyContentItem(BaseModel):
    """單筆週報內容"""
    m_attfile1: str = ""
    m_attfile2: str = ""
    planno: str = ""
    SUBJECT: str = ""
    JOB_ITEM: str = ""
    PROJNO: str = ""
    CUNO: str = ""
    SUNO: str = ""
    CATENO1: str = ""
    CATENO2: str = ""
    CATENO3: str = ""
    CATENO4: str = ""
    CONTENT4: str = ""
    CONTENT1: str = ""
    CONTENT2: str = ""
    CONTENT: str = ""


class SubmitWeeklyReportInput(BaseModel):
    """週報提交請求參數"""
    cocode: str
    deptno: str
    g_deptno: str
    deptname: str
    empno: str
    empname: str
    status: str
    change: str
    oldWeeklyNo: float
    varWeeklyNo: float
    year: str
    sdate: str
    edate: str
    end_date: str
    week_no: str
    details: List[WeeklyContentItem]  # 改為陣列，支援多筆 draft


class SubmitWeeklyReportOutput(BaseModel):
    """週報提交回應"""
    ResponseCmd: str
    ResponseData: bool
    ResponseNo: str
    ResponseNa: str
