# backend/app/schemas/weekly_report_detail.py

from pydantic import BaseModel
from typing import Optional, List


class WeeklyReportMaster(BaseModel):
    """週報主檔"""
    cocode: Optional[str] = None
    empno: Optional[str] = None
    doc_date: Optional[str] = None  # YYYYMMDD
    classify: Optional[str] = None
    deptno: Optional[str] = None
    DEPTABBV: Optional[str] = None  # 部門名稱（單位名稱）
    emergency: Optional[str] = None
    week_no: Optional[str] = None
    XUSER: Optional[str] = None  # 使用者名稱
    reply_status: Optional[str] = None
    JOB_ITEM: Optional[str] = None  # 工作項目
    YY: Optional[str] = None  # 年份
    Week_No: Optional[str] = None  # 週次
    xdate: Optional[str] = None  # 最後修改日期 YYYYMMDD
    xtime: Optional[str] = None  # 最後修改時間 HH:MM:SS


class WeeklyReportDetail(BaseModel):
    """週報明細"""
    weekly_no: Optional[str] = None
    yy: Optional[str] = None  # 年份
    week_no: Optional[str] = None  # 週次
    cocode_g: Optional[str] = None
    cocode: Optional[str] = None
    empno: Optional[str] = None
    doc_date: Optional[str] = None  # YYYYMMDD
    seq: Optional[str] = None  # 序號
    subject: Optional[str] = None  # 主旨
    job_item: Optional[str] = None  # 工作項目
    projno: Optional[str] = None
    planno: Optional[str] = None
    cuno: Optional[str] = None
    suno: Optional[str] = None
    cateno1: Optional[str] = None
    cateno2: Optional[str] = None
    cateno3: Optional[str] = None
    cateno4: Optional[str] = None
    content4: Optional[str] = None
    xuser: Optional[str] = None  # 建立者
    xdate: Optional[str] = None  # 建立日期 YYYYMMDD
    xtime: Optional[str] = None  # 建立時間 HH:MM:SS
    sdate: Optional[str] = None  # 開始日期 YYYYMMDD
    edate: Optional[str] = None  # 結束日期 YYYYMMDD
    deptno: Optional[str] = None
    content1: Optional[str] = None
    content2: Optional[str] = None
    content: Optional[str] = None  # 內容


class WeeklyReportReply(BaseModel):
    """週報回覆"""
    weekly_no: Optional[str] = None
    reply_nos: Optional[str] = None  # 回覆編號
    empno: Optional[str] = None
    memo: Optional[str] = None  # 回覆內容
    xuser: Optional[str] = None  # 回覆者名稱
    xdate: Optional[str] = None  # 回覆日期 YYYYMMDD
    xtime: Optional[str] = None  # 回覆時間 HH:MM:SS
    memo_1: Optional[str] = None
    memo_2: Optional[str] = None
    from_where: Optional[str] = None


class ShowWeeklyReportResponseData(BaseModel):
    """ShowWeeklyReport API 回傳的資料結構"""
    weeklyReportMaster: WeeklyReportMaster
    weeklyReportDetails: List[WeeklyReportDetail]
    weeklyReportReplies: List[WeeklyReportReply]


class ShowWeeklyReportResponse(BaseModel):
    """ShowWeeklyReport API 完整回傳結構"""
    ResponseCmd: str
    ResponseData: ShowWeeklyReportResponseData
    ResponseNo: str
    ResponseNa: str
