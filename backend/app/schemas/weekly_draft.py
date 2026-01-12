# backend/app/schemas/weekly_draft.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class FileAttachment(BaseModel):
    """附件資訊"""
    filename: str
    file_path: str
    file_size: int
    file_type: str


class WeeklyDraftBase(BaseModel):
    """週報草稿基礎 Schema"""
    subject: Optional[str] = None
    job_item: str  # 營收報告/工作重點/應收帳款追蹤/原廠說明
    content: str
    files: Optional[List[FileAttachment]] = []


class WeeklyDraftCreate(WeeklyDraftBase):
    """新增週報草稿"""
    weekly_no: str
    seq: Optional[int] = None  # 更新時必填


class WeeklyDraftUpdate(WeeklyDraftBase):
    """更新週報草稿"""
    pass


class WeeklyDraftResponse(WeeklyDraftBase):
    """週報草稿回應"""
    weekly_no: str
    empno: str
    cocode: str
    doc_date: Optional[str] = None
    seq: int
    word_count: int = 0
    att_file1: Optional[str] = None
    att_file2: Optional[str] = None
    draft_type: str = "TEMP"
    status: str = "A"
    created_date: Optional[str] = None
    created_time: Optional[str] = None
    updated_date: Optional[str] = None
    updated_time: Optional[str] = None
    ai_content: Optional[str] = None
    ai_service: Optional[str] = None

    class Config:
        from_attributes = True


class WeeklyDraftListResponse(BaseModel):
    """週報草稿列表回應"""
    weekly_no: str
    year: int
    week: int
    drafts: List[WeeklyDraftResponse]


class WeeklyNoResponse(BaseModel):
    """週報編號回應"""
    weekly_no: str
    year: int
    week: int


class JobItemsResponse(BaseModel):
    """工作項目列表回應"""
    job_items: List[str]


class AIPolishRequest(BaseModel):
    """AI 潤飾請求"""
    content: str
    job_item: str


class AIPolishResponse(BaseModel):
    """AI 潤飾回應"""
    ai_content: str
    ai_service: str
    word_count: int


class FileUploadResponse(BaseModel):
    """檔案上傳回應"""
    filename: str
    file_path: str
    file_size: int
    file_type: str
