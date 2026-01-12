# backend/app/schemas/overdue_ar.py

from pydantic import BaseModel
from typing import Optional, List


class OverdueARInput(BaseModel):
    """逾期應收帳款請求參數"""
    empno: str
    deptno: str
    year: int
    week_no: int


class OverdueARData(BaseModel):
    """逾期應收帳款資料"""
    empno: str
    deptno: str
    year: int
    week_no: int
    data_date: Optional[str] = None
    last_updatetime: Optional[str] = None
    cocode: Optional[str] = None
    coabbv: Optional[str] = None
    abbv_c: Optional[str] = None  # 客戶簡稱
    doc_type: Optional[str] = None
    doc_no: Optional[str] = None  # 銷貨單號
    invoice: Optional[str] = None  # 發票號碼
    doc_date: Optional[str] = None  # 銷貨日
    ppay_date: Optional[str] = None  # 預計付款日
    curr: Optional[str] = None  # 幣別
    curramt2: Optional[float] = None  # 原幣餘額


class OverdueAROutput(BaseModel):
    """逾期應收帳款回應"""
    ResponseCmd: str
    ResponseData: List[OverdueARData]
    ResponseNo: str
    ResponseNa: str
