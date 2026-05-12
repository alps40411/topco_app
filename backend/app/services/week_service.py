# backend/app/services/week_service.py
"""
週次服務 - 集中管理所有 CommonAPI 週次相關呼叫

設計原則：
1. 完全依賴 CommonAPI（不本地計算週次/日期）
2. 記憶體快取避免重複呼叫
3. 不依賴 DB session（HTTP 呼叫不會佔用 connection pool）

快取策略：
- GetWeeklyPeriod(year, week) → 永久快取（結果不會變，給「指定週次」查詢用）
- GetWeeklyNoByDate(cocode, empno, date+time) → 30 秒快取（含 user-aware can_send / workweek_*）
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
    """
    週次資訊（YYYYMMDD 內部格式）

    - 基本欄位（year, weekly_no, start_date, end_date）永遠有值
    - user-aware 欄位（can_send, workweek_monday, workweek_friday）僅 get_week_by_date 取得
      時才會帶值；get_week_period 取得時為 None
    """

    def __init__(
        self,
        year: int,
        weekly_no: int,
        start_date: str,
        end_date: str,
        can_send: Optional[bool] = None,
        workweek_monday: Optional[str] = None,
        workweek_friday: Optional[str] = None,
    ):
        self.year = year
        self.weekly_no = weekly_no
        self.start_date = start_date            # YYYYMMDD（週日）
        self.end_date = end_date                # YYYYMMDD（週六）
        self.can_send = can_send
        self.workweek_monday = workweek_monday  # YYYYMMDD（週一）or None
        self.workweek_friday = workweek_friday  # YYYYMMDD（週五）or None

    def to_dict(self):
        d = {
            "year": self.year,
            "weekly_no": self.weekly_no,
            "startdate": self.start_date,
            "enddate": self.end_date,
        }
        if self.can_send is not None:
            d["can_send"] = self.can_send
        if self.workweek_monday:
            d["workweek_monday"] = self.workweek_monday
        if self.workweek_friday:
            d["workweek_friday"] = self.workweek_friday
        return d


def compute_auto_submit_times(end_date: str) -> Tuple[str, str]:
    """
    依週次結束日（YYYYMMDD，週六）計算自動繳交相關時間點。

    - cutoff: 週日 24:00（= 隔週一 00:00）。之後使用者不可再勾選自動繳交
    - execution: 隔週一 08:00。batch 程式執行自動繳交的時間
    回傳台北時區 ISO 8601 字串。
    """
    tw = pytz.timezone("Asia/Taipei")
    naive_end = datetime.strptime(end_date, "%Y%m%d")       # 週六 00:00（naive）
    cutoff_naive = naive_end + timedelta(days=2)            # 週一 00:00
    execution_naive = cutoff_naive + timedelta(hours=8)     # 週一 08:00
    cutoff = tw.localize(cutoff_naive)
    execution = tw.localize(execution_naive)
    return cutoff.isoformat(), execution.isoformat()


# ============== 快取 ==============
# Period 永久快取：(year, week) -> WeekInfo（不含 user-aware 欄位）
_period_cache: Dict[Tuple[int, int], WeekInfo] = {}
_period_cache_lock = asyncio.Lock()

# 使用者本次應交週次 30 秒快取：(cocode, empno, date_str) -> (WeekInfo, expires_at)
_user_week_cache: Dict[Tuple[str, str, str], Tuple[WeekInfo, datetime]] = {}
_user_week_cache_lock = asyncio.Lock()
USER_WEEK_CACHE_TTL = timedelta(seconds=30)


def _now_taiwan_with_minute() -> str:
    """取得台灣時區當前時間，格式 'YYYY-MM-DD HH:MM'（給新 GetWeeklyNoByDate 用）"""
    tw = pytz.timezone("Asia/Taipei")
    return datetime.now(tw).strftime("%Y-%m-%d %H:%M")


def _today_taiwan() -> str:
    """取得台灣時區的今天日期，格式 YYYY/MM/DD（保留給其他模組用）"""
    tw = pytz.timezone("Asia/Taipei")
    return datetime.now(tw).strftime("%Y/%m/%d")


def _mmdd_to_yyyymmdd(year: int, mmdd: str) -> str:
    """將 'MM/DD' 轉為 'YYYYMMDD'"""
    parts = mmdd.split("/")
    return f"{year}{parts[0].zfill(2)}{parts[1].zfill(2)}"


def _compact(s: Optional[str]) -> str:
    """將 'YYYY/MM/DD' 轉為 'YYYYMMDD'（空字串原樣回傳）"""
    return (s or "").replace("/", "")


async def get_week_by_date(
    date_str: Optional[str],
    cocode: str,
    empno: str,
) -> WeekInfo:
    """
    依「日期+時分」+ 使用者，取得該員工此時應交的週次資訊。
    內部呼叫 CommonAPI GetWeeklyNoByDate（新版簽名）。

    Args:
        date_str: 'YYYY-MM-DD HH:MM' 台灣時區。None → 自動取現在時間。
        cocode:   公司別（會自動轉大寫；空值會 fallback 為 'A'）
        empno:    員工編號

    Returns:
        WeekInfo（含 can_send / workweek_monday / workweek_friday）
    """
    cocode = (cocode or "A").upper()
    if not date_str:
        date_str = _now_taiwan_with_minute()

    cache_key = (cocode, empno, date_str)
    now = datetime.now()
    if cache_key in _user_week_cache:
        info, expires_at = _user_week_cache[cache_key]
        if now < expires_at:
            return info

    async with _user_week_cache_lock:
        # double-check
        if cache_key in _user_week_cache:
            info, expires_at = _user_week_cache[cache_key]
            if now < expires_at:
                return info

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.GET_WEEKLY_NO_BY_DATE_URL,
                json={"cocode": cocode, "empno": empno, "date": date_str},
            )
            data = response.json()

        if data.get("ResponseNo") != "0000":
            raise Exception(f"GetWeeklyNoByDate 失敗: {data.get('ResponseNa')}")

        year_raw = data.get("year")
        weekly_no_raw = data.get("weekly_no")
        if year_raw is None or weekly_no_raw in (None, ""):
            raise Exception(f"GetWeeklyNoByDate 回傳缺少 year/weekly_no: {data}")

        info = WeekInfo(
            year=int(year_raw),
            weekly_no=int(weekly_no_raw),
            start_date=_compact(data.get("startdate")),
            end_date=_compact(data.get("enddate")),
            can_send=bool(data.get("can_send", False)),
            workweek_monday=_compact(data.get("workweek_monday")) or None,
            workweek_friday=_compact(data.get("workweek_friday")) or None,
        )

        # 同時寫入 period cache（只存基本欄位，不含 user-aware）
        _period_cache[(info.year, info.weekly_no)] = WeekInfo(
            year=info.year,
            weekly_no=info.weekly_no,
            start_date=info.start_date,
            end_date=info.end_date,
        )
        _user_week_cache[cache_key] = (info, now + USER_WEEK_CACHE_TTL)
        logger.info(
            f"WeekByDate cache miss → 寫入: cocode={cocode}, empno={empno}, "
            f"date={date_str}, week={info.weekly_no}, can_send={info.can_send}"
        )
        return info


async def get_week_period(year: int, weekly_no: int) -> WeekInfo:
    """
    取得指定週次的日期範圍（永久快取，僅基本欄位）

    Args:
        year: 年份
        weekly_no: 週次

    Returns:
        WeekInfo 物件，包含 YYYYMMDD 格式的日期範圍（不含 user-aware 欄位）

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
                json={"year": str(year), "weeklyNo": str(weekly_no)},
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
        logger.info(
            f"WeekPeriod cache miss → 寫入: ({year}, {weekly_no}) = "
            f"{info.start_date}~{info.end_date}"
        )
        return info


def invalidate_user_week_cache(
    cocode: Optional[str] = None, empno: Optional[str] = None
):
    """
    清除使用者應交週次快取
    - 不帶參數：清空全部
    - 帶 cocode/empno：只清該員工的快取
    用於提交週報後需要立即看到最新狀態
    """
    if not cocode and not empno:
        _user_week_cache.clear()
        return

    cocode_u = (cocode or "").upper()
    keys_to_remove = [
        key
        for key in _user_week_cache.keys()
        if (not cocode_u or key[0] == cocode_u) and (not empno or key[1] == empno)
    ]
    for key in keys_to_remove:
        _user_week_cache.pop(key, None)


# 舊名稱保留為別名（向後相容；建議呼叫端改用 invalidate_user_week_cache）
invalidate_latest_submit_cache = invalidate_user_week_cache
