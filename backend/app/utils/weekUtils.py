# backend/app/utils/weekUtils.py

from datetime import datetime, timedelta


def get_week_start_date(year: int, week_no: int) -> str:
    """
    獲取指定年份和週次的週一日期 (ISO 8601 標準)

    Args:
        year: 年份
        week_no: 週次 (1-53)

    Returns:
        YYYYMMDD 格式的日期字串
    """
    # ISO 8601 週次：週一是一週的第一天
    # 第一週包含該年的第一個星期四
    jan_4 = datetime(year, 1, 4)
    week_one_monday = jan_4 - timedelta(days=jan_4.weekday())

    # 計算指定週次的週一
    target_monday = week_one_monday + timedelta(weeks=week_no - 1)

    return target_monday.strftime("%Y%m%d")


def get_week_end_date(year: int, week_no: int) -> str:
    """
    獲取指定年份和週次的週日日期 (ISO 8601 標準)

    Args:
        year: 年份
        week_no: 週次 (1-53)

    Returns:
        YYYYMMDD 格式的日期字串
    """
    # 獲取週一日期
    monday_str = get_week_start_date(year, week_no)
    monday = datetime.strptime(monday_str, "%Y%m%d")

    # 週日 = 週一 + 6 天
    sunday = monday + timedelta(days=6)

    return sunday.strftime("%Y%m%d")
