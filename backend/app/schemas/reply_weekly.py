# backend/app/schemas/reply_weekly.py

from pydantic import BaseModel
from typing import Optional, List


class ReplyWeeklyReportRequest(BaseModel):
    """回覆週報請求"""
    weekly_no: str  # 週報編號
    reply_memo: str  # 回覆內容
    score: Optional[int] = None  # 評分（1-5），主管評分時才有
    to_users: List[str] = []  # 回覆給誰的 empno 列表
    forward_users: List[str] = []  # 轉寄給誰的 empno 列表


class ReplyWeeklyReportResponse(BaseModel):
    """回覆週報回應"""
    ResponseCmd: str
    ResponseData: bool
    ResponseNo: str
    ResponseNa: str
