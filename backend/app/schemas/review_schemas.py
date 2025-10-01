# backend/app/schemas/review_schemas.py

from typing import List, Optional
from pydantic import BaseModel

class ReviewSubmitRequest(BaseModel):
    """主管審閱提交請求"""
    daily_no: str
    score: Optional[int] = None  # 1-5分
    reply_memo: Optional[str] = None  # 回應內容
    to_users: List[str] = []  # 回應目標用戶的工號列表（必填，支持預設值和"全部"選項）
    forward_users: Optional[List[str]] = []  # 轉寄給其他用戶的工號列表
    
class ReviewSubmitResponse(BaseModel):
    """主管審閱提交回應"""
    success: bool
    message: str
    reply_nos: Optional[int] = None
    
class ReplyRecord(BaseModel):
    """回應記錄"""
    daily_no: str
    reply_nos: int
    empno: str
    empname: str
    memo: str
    reply_date: str
    reply_time: str
    score: Optional[int] = None
    
class ReviewStatusResponse(BaseModel):
    """審閱狀態回應"""
    daily_no: str
    has_replied: bool
    has_scored: bool
    reply_records: List[ReplyRecord] = []

class ReportAcknowledgeRequest(BaseModel):
    """日報確認已讀請求"""
    daily_no: str

class ReportAcknowledgeResponse(BaseModel):
    """日報確認已讀回應"""
    success: bool
    message: str
    eai_seq: Optional[int] = None