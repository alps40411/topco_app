# backend/app/services/daily_date_service.py

import subprocess
import json
import logging
import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

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
    """日期範圍服務 - 使用 C# 子程序調用 MyReport.dll"""

    def __init__(self):
        # 取得 C# 執行檔路徑 (使用 JSON 版本)
        backend_dir = Path(__file__).parent.parent.parent
        self.exe_path = backend_dir / "DailyDateServiceJson.exe"

        if not self.exe_path.exists():
            raise FileNotFoundError(f"找不到 DailyDateServiceJson.exe: {self.exe_path}")

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
            logger.info(f"調用 getDailyDate: cocode={cocode}, empno={empno}")

            # 執行 C# 程式
            result = subprocess.run(
                [str(self.exe_path), cocode, empno],
                capture_output=True,
                text=True,
                timeout=30,  # 30秒超時
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                logger.error(f"C# 程式執行失敗: {result.stderr}")
                raise Exception(f"getDailyDate 執行失敗: {result.stderr}")

            # 解析 JSON 輸出
            date_data = self._parse_json_output(result.stdout)

            # 更新緩存
            _date_cache[cache_key] = {
                "data": date_data,
                "timestamp": current_time
            }

            logger.info(f"日期數據已緩存: {cache_key}")
            return date_data

        except subprocess.TimeoutExpired:
            logger.error("C# 程式執行超時")
            raise Exception("getDailyDate 執行超時")
        except Exception as e:
            logger.error(f"執行 getDailyDate 時發生錯誤: {e}")
            raise


    def _parse_json_output(self, output: str) -> List[Dict[str, Any]]:
        """
        解析 C# 程式的 JSON 輸出

        預期輸出格式:
        [{"date":"20250911","status":"OpenWrite","can_write":true}, ...]
        """
        try:
            output = output.strip()

            # 檢查是否為錯誤輸出
            if output.startswith('{"error":true'):
                error_data = json.loads(output)
                raise Exception(f"C# 程式錯誤: {error_data.get('message', 'Unknown error')}")

            # 解析正常的 JSON 輸出
            result = json.loads(output)

            if not isinstance(result, list):
                raise Exception(f"預期 JSON 陣列，但得到: {type(result)}")

            logger.info(f"成功解析 {len(result)} 筆日期資料")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析錯誤: {e}")
            logger.error(f"原始輸出: {output}")
            raise Exception(f"解析 getDailyDate JSON 輸出失敗: {e}")
        except Exception as e:
            logger.error(f"解析輸出時發生錯誤: {e}")
            logger.error(f"原始輸出: {output}")
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