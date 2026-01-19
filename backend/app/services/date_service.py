# backend/app/services/date_service.py

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

logger = logging.getLogger(__name__)


class DateService:
    """處理日期範圍和日報編號的服務"""

    @staticmethod
    def get_date_range_with_status(
        db: Session,
        empno: str,
        cocode: str
    ) -> Dict[str, Any]:
        """
        取得用戶可填寫日報的日期範圍，包含狀態檢查
        整合了 daily-date-range 和 writing-status 的功能
        """
        try:
            # 使用 DailyDateService 獲取基本日期範圍
            from .daily_date_service import DailyDateService

            daily_service = DailyDateService()
            date_range = daily_service.get_daily_date_range(cocode, empno)

            if not date_range:
                logger.warning(f"getDailyDate 查詢結果為空: empno={empno}")
                return {
                    "success": True,
                    "data": [],
                    "current_report_date": "",
                    "empno": empno,
                    "cocode": cocode,
                    "total_dates": 0,
                    "writable_dates": 0,
                    "allowed": False,
                    "message": "沒有可用的日期範圍",
                    "has_other_writable_dates": False,
                    "selected_date_info": None,
                    "current_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

            logger.info(f"成功從 getDailyDate 取得日期範圍: {len(date_range)} 個選項")

            # 處理每個日期，檢查審閱狀態
            available_dates = []
            for date_info in date_range:
                date_value = date_info["date"]
                status = date_info["status"]
                can_write = date_info["can_write"]
                can_submit = date_info.get("can_submit", False)  # 從 API 獲取是否可提交

                # 檢查該日期是否已被主管審閱
                review_status_sql = text("""
                    SELECT
                        (SELECT COUNT(*) FROM jps.tdr_score s
                         JOIN jps.tdr_master m ON s.daily_no = m.daily_no
                         WHERE m.empno = :empno AND m.doc_date = :doc_date) as score_count,
                        (SELECT COUNT(*) FROM jps.tdr_reply r
                         JOIN jps.tdr_master m ON r.daily_no = m.daily_no
                         WHERE m.empno = :empno AND m.doc_date = :doc_date AND r.from_where is not NULL) as reply_count
                """)

                review_result = db.execute(review_status_sql, {
                    "empno": empno,
                    "doc_date": date_value
                }).fetchone()

                score_count = review_result[0] if review_result else 0
                reply_count = review_result[1] if review_result else 0
                has_supervisor_review = score_count > 0 or reply_count > 0

                # 如果已被主管審閱，標記為不可寫入且不可提交
                if has_supervisor_review:
                    logger.info(f"日期 {date_value} 已被主管審閱，標記為不可寫入且不可提交")
                    can_write = False
                    can_submit = False

                # 解析日期
                try:
                    date_obj = datetime.strptime(date_value, '%Y%m%d')
                    is_weekday = date_obj.weekday() < 5
                    display_date = date_obj.strftime('%Y-%m-%d')
                    today = datetime.now().strftime('%Y%m%d')
                    is_today = date_value == today

                    available_dates.append({
                        "value": date_value,
                        "display": display_date,
                        "date": display_date,
                        "is_weekday": is_weekday,
                        "is_today": is_today,
                        "is_default": False,
                        "can_write": can_write,
                        "can_submit": can_submit,  # 新增: 是否可提交最終版
                        "status": "Reviewed" if has_supervisor_review else (status or "Available"),
                        "has_supervisor_review": has_supervisor_review
                    })
                except ValueError:
                    logger.warning(f"無法解析日期: {date_value}")
                    continue

            # 按日期排序（最新的在前）
            available_dates.sort(key=lambda x: x["value"], reverse=True)

            # 設定預設日期
            current_report_date = ""
            for date_option in available_dates:
                if date_option["can_write"]:
                    current_report_date = date_option["value"]
                    date_option["is_default"] = True
                    break

            # 如果沒有可填寫的日期，使用最新的日期
            if not current_report_date and available_dates:
                current_report_date = available_dates[0]["value"]
                available_dates[0]["is_default"] = True
                logger.info(f"沒有可填寫日期，使用最新日期: {current_report_date}")

            # 計算全局狀態
            writable_dates_list = [d for d in available_dates if d["can_write"]]
            writable_dates_count = len(writable_dates_list)
            allowed = writable_dates_count > 0

            # 計算可提交的日期數量
            submittable_dates_list = [d for d in available_dates if d["can_submit"]]
            submittable_dates_count = len(submittable_dates_list)

            # 全局提示訊息
            message = ""
            if not allowed and available_dates:
                message = "日報已被主管審閱，無法編輯，請等待隔天8:30後填寫新的日報"
            elif not available_dates:
                message = "目前沒有可填寫的日期範圍"

            # 當前選擇日期的詳細狀態
            selected_date_info = None
            can_submit_today = False
            if current_report_date:
                selected_date_info = next(
                    (d for d in available_dates if d["value"] == current_report_date),
                    None
                )
                if selected_date_info:
                    can_submit_today = selected_date_info.get("can_submit", False)

            return {
                "success": True,
                "data": available_dates,
                "current_report_date": current_report_date,
                "empno": empno,
                "cocode": cocode,
                "total_dates": len(available_dates),
                "writable_dates": writable_dates_count,
                "submittable_dates": submittable_dates_count,  # 新增: 可提交日期數量
                "allowed": allowed,
                "can_submit_today": can_submit_today,  # 新增: 當前日期是否可提交
                "message": message,
                "has_other_writable_dates": writable_dates_count > 0,
                "selected_date_info": selected_date_info,
                "current_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            logger.error(f"Error getting date range: {str(e)}")
            raise


