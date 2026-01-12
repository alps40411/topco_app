# backend/app/schemas/revenue.py

from pydantic import BaseModel
from typing import Optional, List


class RevenueInput(BaseModel):
    """營收達成率請求參數"""
    empno: str
    year: int
    week_no: int


class RevenueData(BaseModel):
    """營收達成率資料"""
    cocode: Optional[str] = None
    coabbv: Optional[str] = None
    year: int
    week_no: int
    DATA_DATE: Optional[str] = None
    month: Optional[str] = None
    cateno1: Optional[str] = None
    catedesc1: Optional[str] = None  # 產品類別
    last_updatetime: Optional[str] = None
    ym_bg_rev_amt: Optional[float] = None  # 年月預算營收金額
    ym_rev_amt: Optional[float] = None  # 年月營收金額（月累計營收）
    y_rev_amt: Optional[float] = None  # 年度營收金額（年度出貨）
    rev_amt: Optional[float] = None  # 營收金額
    m_rev_amt: Optional[float] = None  # 月營收金額


class RevenueOutput(BaseModel):
    """營收達成率回應"""
    ResponseCmd: str
    ResponseData: List[RevenueData]
    ResponseNo: str
    ResponseNa: str
