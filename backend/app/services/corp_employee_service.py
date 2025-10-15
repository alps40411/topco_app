# backend/app/services/corp_employee_service.py

import json
import logging
import time
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 全局緩存
_forward_cache: Dict[str, Dict[str, Any]] = {}
_cache_timeout = 5 * 60  # 5分鐘緩存

class CorpEmployeeService:
    """員工服務 - 使用 HTTP API 調用 CommonApi/MyReport/GetForwardList"""

    def __init__(self):
        # API 端點
        self.api_url = "http://10.129.7.248/CommonApi/MyReport/GetForwardList"
        # HTTP 客戶端超時設置
        self.timeout = 30.0

    def load_forward(self, ls_forward_duty: List[str], table_name: str) -> Dict[str, Any]:
        """
        載入轉寄員工資料

        Args:
            ls_forward_duty: 職稱列表
            table_name: 表格名稱

        Returns:
            Dict: 三層結構的員工資料
            第一層: 業務單位/幕僚單位
            第二層: 事業本部
            第三層: 人員列表(含職稱)
        """
        cache_key = f"{':'.join(ls_forward_duty)}:{table_name}"
        current_time = time.time()

        # 檢查緩存
        if cache_key in _forward_cache:
            cached_data = _forward_cache[cache_key]
            if current_time - cached_data["timestamp"] < _cache_timeout:
                logger.info(f"使用緩存的轉寄員工數據: {cache_key}")
                return cached_data["data"]
            else:
                logger.info(f"緩存已過期，重新獲取: {cache_key}")

        try:
            logger.info(f"調用 GetForwardList API (忽略參數 duties={ls_forward_duty}, table={table_name})")

            # 準備 API 請求 (API 不需要參數)
            payload = {}

            # 調用 HTTP API
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.api_url, json=payload)
                response.raise_for_status()  # 如果狀態碼不是 2xx，拋出異常

            # 解析 API 回應
            forward_data = self._parse_api_response(response.json())

            # 更新緩存
            _forward_cache[cache_key] = {
                "data": forward_data,
                "timestamp": current_time
            }

            logger.info(f"轉寄員工數據已緩存: {cache_key}")
            return forward_data

        except httpx.TimeoutException:
            logger.error("API 請求超時")
            raise Exception("GetForwardList API 請求超時")
        except httpx.HTTPStatusError as e:
            logger.error(f"API 請求失敗: {e.response.status_code} - {e.response.text}")
            raise Exception(f"GetForwardList API 請求失敗: {e}")
        except Exception as e:
            logger.error(f"執行 GetForwardList 時發生錯誤: {e}")
            raise

    def _parse_api_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 API 回應並轉換為系統使用的格式

        API 回應格式:
        {
            "ResponseCmd": "GetForwardList",
            "ResponseData": [
                {
                    "業務單位": [[{員工1}, {員工2}], [{員工3}]],
                    "幕僚單位": [[{員工4}]]
                }
            ],
            "IsDuty": [...],
            "ResponseNo": "0000",
            "ResponseNa": "Success"
        }

        轉換為:
        {
            "業務單位": {
                "第一事業本部": [{員工1}, {員工2}],
                "第二事業本部": [{員工3}]
            },
            "幕僚單位": {
                "董事長室": [{員工4}]
            }
        }
        """
        try:
            # 檢查回應狀態
            response_no = response_data.get("ResponseNo", "")
            if response_no != "0000":
                error_msg = response_data.get("ResponseNa", "Unknown error")
                raise Exception(f"API 錯誤: {error_msg} (代碼: {response_no})")

            # 取得員工資料
            response_list = response_data.get("ResponseData", [])

            if not isinstance(response_list, list) or len(response_list) == 0:
                raise Exception(f"預期 ResponseData 為非空陣列，但得到: {type(response_list)}")

            # ResponseData 是一個包含多個字典的陣列
            # 每個字典的 key 是組織單位名稱（如 "業務單位"、"幕僚單位"）
            result = {}

            for unit_data in response_list:
                if not isinstance(unit_data, dict):
                    continue

                # 遍歷每個組織單位
                for unit_name, dept_groups in unit_data.items():
                    if unit_name not in result:
                        result[unit_name] = {}

                    # dept_groups 是一個二維陣列
                    # 每個子陣列代表一個部門的員工列表
                    for dept_group in dept_groups:
                        if not isinstance(dept_group, list) or len(dept_group) == 0:
                            continue

                        # 尋找群組中的部門名稱 (deptabbv)
                        current_dept_name = None
                        for employee in dept_group:
                            if isinstance(employee, dict) and employee.get('deptabbv'):
                                current_dept_name = employee.get('deptabbv')
                                break

                        # 如果找不到部門名稱，使用預設值
                        if not current_dept_name:
                            current_dept_name = '未分類部門'

                        # 初始化部門
                        if current_dept_name not in result[unit_name]:
                            result[unit_name][current_dept_name] = []

                        # 將員工加入部門
                        for employee in dept_group:
                            if not isinstance(employee, dict):
                                continue

                            # 轉換員工資料格式
                            emp_data = {
                                'empno': employee.get('empno', ''),
                                'empname': employee.get('empnamec', ''),
                                'duty': employee.get('dutyscript', ''),
                                'cocode': '',  # API 返回的資料中沒有這個欄位
                                'deptno': '',  # API 返回的資料中沒有這個欄位
                                'dclass': 0,   # API 返回的資料中沒有這個欄位
                                'adm_rank': 0  # API 返回的資料中沒有這個欄位
                            }

                            result[unit_name][current_dept_name].append(emp_data)

            logger.info(f"成功解析 {len(result)} 個組織單位的員工資料")
            return result

        except Exception as e:
            logger.error(f"解析 API 回應時發生錯誤: {e}")
            logger.error(f"原始回應: {response_data}")
            raise

    def _get_mock_data(self) -> Dict[str, Any]:
        """返回模擬的三層結構資料"""
        return {
            "業務單位": {
                "事業本部A": {
                    "部門A1": [
                        {
                            "empno": "001",
                            "empname": "張三",
                            "duty": "總經理",
                            "cocode": "A",
                            "deptno": "A001",
                            "dclass": 1,
                            "adm_rank": 1
                        },
                        {
                            "empno": "002",
                            "empname": "李四",
                            "duty": "協理",
                            "cocode": "A",
                            "deptno": "A001",
                            "dclass": 2,
                            "adm_rank": 2
                        }
                    ],
                    "部門A2": [
                        {
                            "empno": "003",
                            "empname": "王五",
                            "duty": "處長",
                            "cocode": "A",
                            "deptno": "A002",
                            "dclass": 3,
                            "adm_rank": 3
                        }
                    ]
                },
                "事業本部B": {
                    "部門B1": [
                        {
                            "empno": "004",
                            "empname": "趙六",
                            "duty": "經理",
                            "cocode": "B",
                            "deptno": "B001",
                            "dclass": 4,
                            "adm_rank": 4
                        }
                    ]
                }
            },
            "幕僚單位": {
                "人事處": {
                    "人事部": [
                        {
                            "empno": "005",
                            "empname": "錢七",
                            "duty": "副理",
                            "cocode": "C",
                            "deptno": "C001",
                            "dclass": 5,
                            "adm_rank": 5
                        }
                    ]
                },
                "財務處": {
                    "會計部": [
                        {
                            "empno": "006",
                            "empname": "孫八",
                            "duty": "專員",
                            "cocode": "D",
                            "deptno": "D001",
                            "dclass": 6,
                            "adm_rank": 6
                        }
                    ]
                }
            }
        }

