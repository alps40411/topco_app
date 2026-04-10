# backend/app/services/week_service.py
"""
週次服務 - 集中管理所有 CommonAPI 週次相關呼叫

設計原則：
1. 完全依賴 CommonAPI（不本地計算週次/日期）
2. 記憶體快取避免重複呼叫
3. 不依賴 DB session（HTTP 呼叫不會佔用 connection pool）

快取策略：
- GetWeeklyPeriod(year, week) → 永久快取（結果不會變）
- GetLatestSubmitWeeklyNo(cocode, empno, date) → 30 秒快取
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import asyncio
import logging
import httpx
import pytz

from app.core.config import settings

logger = logging.getLogger(__name__)


class WeekInfo:
    """週次資訊，包含年份、週次、日期範圍（YYYYMMDD 格式）"""
    def __init__(self, year: int, weekly_no: int, start_date: str, end_date: str):
        self.year = year
        self.weekly_no = weekly_no
        self.start_date = start_date  # YYYYMMDD
        self.end_date = end_date      # YYYYMMDD

    def to_dict(self):
        return {
            "year": self.year,
            "weekly_no": self.weekly_no,
            "startdate": self.start_date,
            "enddate": self.end_date,
        }


class LatestSubmitInfo:
    """員工應交週次資訊"""
    def __init__(self, year: int, weekly_no: int, can_send: bool, start_date: str, end_date: str):
        self.year = year
        self.weekly_no = weekly_no
        self.can_send = can_send
        self.start_date = start_date  # YYYYMMDD
        self.end_date = end_date      # YYYYMMDD

    def to_dict(self):
        return {
            "year": self.year,
            "weekly_no": self.weekly_no,
            "can_send": self.can_send,
            "startdate": self.start_date,
            "enddate": self.end_date,
        }


# ============== 快取 ==============
# Period 永久快取：(year, week) -> WeekInfo
_period_cache: Dict[Tuple[int, int], WeekInfo] = {}
_period_cache_lock = asyncio.Lock()

# Latest submit 30 秒快取：(cocode, empno, date_str) -> (LatestSubmitInfo, expires_at)
_latest_cache: Dict[Tuple[str, str, str], Tuple[LatestSubmitInfo, datetime]] = {}
_latest_cache_lock = asyncio.Lock()
LATEST_CACHE_TTL = timedelta(seconds=30)


def _today_taiwan() -> str:
    """取得台灣時區的今天日期，格式 YYYY/MM/DD"""
    taiwan_tz = pytz.timezone('Asia/Taipei')
    return datetime.now(taiwan_tz).strftime("%Y/%m/%d")


def _mmdd_to_yyyymmdd(year: int, mmdd: str) -> str:
    """將 'MM/DD' 轉為 'YYYYMMDD'"""
    parts = mmdd.split("/")
    return f"{year}{parts[0].zfill(2)}{parts[1].zfill(2)}"


async def get_week_by_date(date_str: Optional[str] = None) -> WeekInfo:
    """
    根據日期取得該日所屬的週次資訊

    Args:
        date_str: 日期字串 YYYY/MM/DD，預設為今天（台灣時區）

    Returns:
        WeekInfo (year, weekly_no, start_date, end_date)
    """
    if not date_str:
        date_str = _today_taiwan()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.GET_WEEKLY_NO_BY_DATE_URL,
            json={"date": date_str}
        )
        data = response.json()

    if data.get("ResponseNo") != "0000":
        raise Exception(f"GetWeeklyNoByDate 失敗: {data.get('ResponseNa')}")

    year = int(data.get("year"))
    weekly_no = int(data.get("weekly_no"))

    # GetWeeklyNoByDate 已經回傳 startdate/enddate (YYYY/MM/DD 完整格式)
    # 轉成 YYYYMMDD
    def _yyyy_mm_dd_to_compact(s: str) -> str:
        return s.replace("/", "")

    start_date = _yyyy_mm_dd_to_compact(data.get("startdate", ""))
    end_date = _yyyy_mm_dd_to_compact(data.get("enddate", ""))

    info = WeekInfo(year=year, weekly_no=weekly_no, start_date=start_date, end_date=end_date)
    # 同時寫入 period cache（既然拿到了就順便快取）
    _period_cache[(year, weekly_no)] = info
    return info


async def get_week_period(year: int, weekly_no: int) -> WeekInfo:
    """
    取得指定週次的日期範圍（永久快取）

    Args:
        year: 年份
        weekly_no: 週次

    Returns:
        WeekInfo 物件，包含 YYYYMMDD 格式的日期範圍

    Raises:
        Exception: CommonAPI 呼叫失敗或回傳錯誤
    """
    cache_key = (year, weekly_no)

    # 快取命中
    if cache_key in _period_cache:
        return _period_cache[cache_key]

    async with _period_cache_lock:
        # double-check
        if cache_key in _period_cache:
            return _period_cache[cache_key]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.GET_WEEKLY_PERIOD_URL,
                json={"year": str(year), "weeklyNo": str(weekly_no)}
            )
            data = response.json()

        if data.get("ResponseNo") != "0000":
            raise Exception(f"GetWeeklyPeriod 失敗: {data.get('ResponseNa')}")

        startdate = data.get("startdate")  # MM/DD
        enddate = data.get("enddate")      # MM/DD

        if not startdate or not enddate:
            raise Exception("GetWeeklyPeriod 回傳缺少日期")

        info = WeekInfo(
            year=year,
            weekly_no=weekly_no,
            start_date=_mmdd_to_yyyymmdd(year, startdate),
            end_date=_mmdd_to_yyyymmdd(year, enddate),
        )
        _period_cache[cache_key] = info
        logger.info(f"WeekPeriod cache miss → 寫入: ({year}, {weekly_no}) = {info.start_date}~{info.end_date}")
        return info


async def get_latest_submit_week(cocode: str, empno: str) -> LatestSubmitInfo:
    """
    取得員工目前應交的週次（含補交邏輯與 can_send 判斷）

    Args:
        cocode: 公司代碼（會自動轉大寫）
        empno: 員工編號

    Returns:
        LatestSubmitInfo，包含應交週次、能否送出、日期範圍
    """
    cocode = (cocode or "A").upper()
    today_str = _today_taiwan()
    cache_key = (cocode, empno, today_str)

    # 快取命中且未過期
    now = datetime.now()
    if cache_key in _latest_cache:
        info, expires_at = _latest_cache[cache_key]
        if now < expires_at:
            return info

    async with _latest_cache_lock:
        # double-check
        if cache_key in _latest_cache:
            info, expires_at = _latest_cache[cache_key]
            if now < expires_at:
                return info

        # 1. 呼叫 GetLatestSubmitWeeklyNo
        async with httpx.AsyncClient(timeout=30.0) as client:
            submit_response = await client.post(
                settings.GET_LATEST_SUBMIT_WEEKLY_NO_URL,
                json={"cocode": cocode, "empno": empno, "docdate": today_str}
            )
            submit_data = submit_response.json()

        if submit_data.get("ResponseNo") != "0000":
            raise Exception(f"GetLatestSubmitWeeklyNo 失敗: {submit_data.get('ResponseNa')}")

        weekly_no_str = submit_data.get("weekly_no")
        can_send = bool(submit_data.get("can_send", False))

        if not weekly_no_str:
            raise Exception("GetLatestSubmitWeeklyNo 未回傳 weekly_no")

        weekly_no = int(weekly_no_str)

        # 2. 用 GetWeeklyNoByDate 取得當前年份（CommonAPI 沒在 GetLatestSubmit 回傳 year）
        async with httpx.AsyncClient(timeout=30.0) as client:
            date_response = await client.post(
                settings.GET_WEEKLY_NO_BY_DATE_URL,
                json={"date": today_str}
            )
            date_data = date_response.json()

        if date_data.get("ResponseNo") != "0000":
            raise Exception(f"GetWeeklyNoByDate 失敗: {date_data.get('ResponseNa')}")

        year = int(date_data.get("year"))

        # 3. 取得該週次的日期範圍（會走 cache）
        period = await get_week_period(year, weekly_no)

        info = LatestSubmitInfo(
            year=year,
            weekly_no=weekly_no,
            can_send=can_send,
            start_date=period.start_date,
            end_date=period.end_date,
        )
        _latest_cache[cache_key] = (info, now + LATEST_CACHE_TTL)
        logger.info(f"LatestSubmit cache miss → 寫入: cocode={cocode}, empno={empno}, week={weekly_no}, can_send={can_send}")
        return info


def invalidate_latest_submit_cache(cocode: Optional[str] = None, empno: Optional[str] = None):
    """
    清除 latest submit 快取
    - 不帶參數：清空全部
    - 帶 cocode/empno：只清該員工的快取
    用於提交週報後需要立即看到最新狀態
    """
    if not cocode and not empno:
        _latest_cache.clear()
        return

    cocode = (cocode or "").upper()
    keys_to_remove = [
        key for key in _latest_cache.keys()
        if (not cocode or key[0] == cocode) and (not empno or key[1] == empno)
    ]
    for key in keys_to_remove:
        _latest_cache.pop(key, None)
