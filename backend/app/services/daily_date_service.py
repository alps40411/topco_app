# backend/app/services/daily_date_service.py

import json
import logging
import time
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 全局緩存
_date_cache: Dict[str, Dict[str, Any]] = {}
_cache_timeout = 5 * 60  # 5分鐘緩存

def clear_date_cache(cocode: str = None, empno: str = None):
    """
    清除日期快取

    Args:
        cocode: 公司別（可選，如果不提供則清除所有快取）
        empno: 員工編號（可選，必須與 cocode 一起使用）
    """
    global _date_cache

    if cocode and empno:
        cache_key = f"{cocode}:{empno}"
        if cache_key in _date_cache:
            del _date_cache[cache_key]
            logger.info(f"🗑️ 清除日期快取: {cache_key}")
    else:
        # 清除所有快取
        _date_cache.clear()
        logger.info("🗑️ 清除所有日期快取")

class DailyDateService:
    """日期範圍服務 - 使用 HTTP API 調用 CommonApi/MyReport/GetWritableDate"""

    def __init__(self):
        # API 端點
        self.api_url = "http://10.129.7.248/CommonApi/MyReport/GetWritableDate"
        # HTTP 客戶端超時設置
        self.timeout = 30.0

    def get_daily_date_range(self, cocode: str, empno: str) -> List[Dict[str, Any]]:
        """
        取得員工可填寫日報的日期範圍（帶緩存）

        Args:
            cocode: 公司別
            empno: 員工編號

        Returns:
            List[Dict]: 日期資料列表
            格式: [{"date": "20250911", "status": "OpenWrite"}, ...]
        """
        cache_key = f"{cocode}:{empno}"
        current_time = time.time()

        # 檢查緩存
        if cache_key in _date_cache:
            cached_data = _date_cache[cache_key]
            if current_time - cached_data["timestamp"] < _cache_timeout:
                logger.info(f"使用緩存的日期數據: {cache_key}")
                return cached_data["data"]
            else:
                logger.info(f"緩存已過期，重新獲取: {cache_key}")

        try:
            logger.info(f"調用 GetWritableDate API: cocode={cocode}, empno={empno}")

            # 準備 API 請求
            payload = {
                "cocode": cocode,
                "empno": empno
            }

            # 調用 HTTP API
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.api_url, json=payload)
                response.raise_for_status()  # 如果狀態碼不是 2xx，拋出異常

            # 解析 API 回應
            date_data = self._parse_api_response(response.json())

            # 更新緩存
            _date_cache[cache_key] = {
                "data": date_data,
                "timestamp": current_time
            }

            logger.info(f"日期數據已緩存: {cache_key}")
            return date_data

        except httpx.TimeoutException:
            logger.error("API 請求超時")
            raise Exception("GetWritableDate API 請求超時")
        except httpx.HTTPStatusError as e:
            logger.error(f"API 請求失敗: {e.response.status_code} - {e.response.text}")
            raise Exception(f"GetWritableDate API 請求失敗: {e}")
        except Exception as e:
            logger.error(f"執行 GetWritableDate 時發生錯誤: {e}")
            raise


    def _parse_api_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析 API 回應並轉換為系統使用的格式

        API 回應格式:
        {
            "ResponseCmd": "GetWritableDate",
            "ResponseData": [["20251015", ""]],
            "ResponseNo": "0000",
            "ResponseNa": "Success"
        }

        轉換為:
        [{"date": "20251015", "status": "OpenWrite", "can_write": true}, ...]
        """
        try:
            # 檢查回應狀態
            response_no = response_data.get("ResponseNo", "")
            if response_no != "0000":
                error_msg = response_data.get("ResponseNa", "Unknown error")
                raise Exception(f"API 錯誤: {error_msg} (代碼: {response_no})")

            # 取得日期資料
            response_dates = response_data.get("ResponseData", [])

            if not isinstance(response_dates, list):
                raise Exception(f"預期 ResponseData 為陣列，但得到: {type(response_dates)}")

            # 轉換格式
            result = []
            for date_item in response_dates:
                if isinstance(date_item, list) and len(date_item) > 0:
                    date_value = date_item[0]
                    # ResponseData 格式為 [["20251015", ""]]
                    # 第二個元素為空字串，我們假設所有返回的日期都是可寫入的
                    result.append({
                        "date": date_value,
                        "status": "OpenWrite",
                        "can_write": True
                    })

            logger.info(f"成功解析 {len(result)} 筆日期資料")
            return result

        except Exception as e:
            logger.error(f"解析 API 回應時發生錯誤: {e}")
            logger.error(f"原始回應: {response_data}")
            raise

    def get_date_range_simple(self, cocode: str, empno: str) -> Dict[str, Any]:
        """
        取得簡化的日期範圍資訊

        Returns:
            Dict: {
                "available_dates": ["20250911", "20250912", ...],
                "open_dates": ["20250911", "20250912", ...],
                "total_count": 3
            }
        """
        try:
            date_data = self.get_daily_date_range(cocode, empno)

            available_dates = [item["date"] for item in date_data]
            open_dates = [item["date"] for item in date_data if item.get("can_write", False)]

            return {
                "available_dates": available_dates,
                "open_dates": open_dates,
                "total_count": len(date_data),
                "open_count": len(open_dates)
            }

        except Exception as e:
            logger.error(f"取得簡化日期範圍時發生錯誤: {e}")
            raise