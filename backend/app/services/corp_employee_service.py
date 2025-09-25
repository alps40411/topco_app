# backend/app/services/corp_employee_service.py

import subprocess
import json
import logging
import os
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 全局緩存
_forward_cache: Dict[str, Dict[str, Any]] = {}
_cache_timeout = 5 * 60  # 5分鐘緩存

class CorpEmployeeService:
    """員工服務 - 使用 C# 子程序調用 CorpEmployeeService.loadForward"""

    def __init__(self):
        # 取得 C# 執行檔路徑 (使用 JSON 版本，類似 DailyDateService)
        backend_dir = Path(__file__).parent.parent.parent
        self.exe_path = backend_dir / "CorpEmployeeServiceJson.exe"

        if not self.exe_path.exists():
            raise FileNotFoundError(f"找不到 CorpEmployeeServiceJson.exe: {self.exe_path}")

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
            logger.info(f"調用 CorpEmployeeService.loadForward: duties={ls_forward_duty}, table={table_name}")

            # TODO: 當 CorpEmployeeServiceJson.exe 準備好後，使用以下代碼：
            # 準備參數
            # duty_params = "|".join(ls_forward_duty)  # 用 | 分隔職稱列表
            
            # 執行 C# 程式
            # result = subprocess.run(
            #     [str(self.exe_path), duty_params, table_name],
            #     capture_output=True,
            #     text=True,
            #     timeout=30,  # 30秒超時
            #     encoding='utf-8',
            #     errors='replace'
            # )

            # if result.returncode != 0:
            #     logger.error(f"C# 程式執行失敗: {result.stderr}")
            #     raise Exception(f"loadForward 執行失敗: {result.stderr}")

            # 解析 JSON 輸出
            # forward_data = self._parse_json_output(result.stdout)

            # 根據實際的 loadForward 調用方式：
            # List<Dictionary<string, List<List<object>>>> lsForward = CorpEmployeeService.loadForward(out lsDuty, null);
            # - 第一個參數是 out 參數，不需要從 Python 傳入
            # - 第二個參數傳入 null

            # 執行 C# 程式 - 不需要任何參數，因為 loadForward 的參數都由 C# 內部處理
            result = subprocess.run(
                [str(self.exe_path)],
                capture_output=True,
                timeout=30,  # 30秒超時
            )
            
            # 手動解碼輸出
            stdout_text = result.stdout.decode('utf-8', errors='replace')
            stderr_text = result.stderr.decode('utf-8', errors='replace')
            
            # 創建結果物件
            result = type('Result', (), {'stdout': stdout_text, 'stderr': stderr_text, 'returncode': result.returncode})()

            if result.returncode != 0:
                logger.error(f"C# 程式執行失敗: {result.stderr}")
                raise Exception(f"loadForward 執行失敗: {result.stderr}")

            # 調試：輸出 C# 程式的原始輸出
            logger.info(f"C# 程式原始輸出: {result.stdout}")
            logger.info(f"C# 程式錯誤輸出: {result.stderr}")
            
            # 解析 JSON 輸出
            forward_data = self._parse_json_output(result.stdout)

            # 更新緩存
            _forward_cache[cache_key] = {
                "data": forward_data,
                "timestamp": current_time
            }

            logger.info(f"轉寄員工數據已緩存: {cache_key}")
            return forward_data

        except Exception as e:
            logger.error(f"執行 loadForward 時發生錯誤: {e}")
            raise

    def _parse_json_output(self, json_output: str) -> Dict[str, Any]:
        """
        解析 C# 程式返回的 JSON 輸出
        
        Args:
            json_output: C# 程式返回的 JSON 字串
            
        Returns:
            Dict: 轉換後的三層結構資料
        """
        try:
            import json
            
            # 調試：輸出原始 JSON 字串
            logger.info(f"原始 JSON 輸出長度: {len(json_output)}")
            logger.info(f"原始 JSON 輸出前 200 字元: {json_output[:200]}")

            # 移除 BOM 字符和空白字符
            json_output = json_output.strip()
            if json_output.startswith('\ufeff'):
                json_output = json_output[1:]

            # 解析 JSON
            raw_data = json.loads(json_output)
            
            # 將 C# 返回的資料結構轉換為我們需要的三層結構
            # C# 返回的是 List[Dict[str, List[List[Dict]]]]
            # 需要轉換為 Dict[str, Dict[str, List[Dict]]]
            
            result = {}
            
            # 調試：輸出原始資料結構
            logger.info(f"原始資料類型: {type(raw_data)}")
            logger.info(f"原始資料長度: {len(raw_data) if isinstance(raw_data, list) else 'N/A'}")
            
            for company_data in raw_data:
                logger.info(f"公司資料類型: {type(company_data)}")
                logger.info(f"公司資料鍵: {list(company_data.keys()) if isinstance(company_data, dict) else 'N/A'}")
                
                for company_name, departments in company_data.items():
                    logger.info(f"公司名稱: {company_name}, 部門資料類型: {type(departments)}")
                    
                    if company_name not in result:
                        result[company_name] = {}
                    
                    # departments 是 List[List[Dict]]
                    for dept_group in departments:
                        logger.info(f"部門群組類型: {type(dept_group)}, 長度: {len(dept_group) if isinstance(dept_group, list) else 'N/A'}")

                        # 尋找群組中的部門名稱
                        current_dept_name = None
                        for employee in dept_group:
                            if employee.get('deptabbv'):
                                current_dept_name = employee.get('deptabbv')
                                break

                        # 如果找不到部門名稱，使用預設值
                        if not current_dept_name:
                            current_dept_name = '未分類部門'

                        logger.info(f"群組部門名稱: {current_dept_name}")

                        if current_dept_name not in result[company_name]:
                            result[company_name][current_dept_name] = []

                        # dept_group 是 List[Dict]，每個 Dict 包含員工資訊
                        for employee in dept_group:
                            # 轉換員工資料格式
                            emp_data = {
                                'empno': employee.get('empno', ''),
                                'empname': employee.get('empnamec', ''),
                                'duty': employee.get('dutyscript', ''),
                                'cocode': '',  # C# 返回的資料中沒有這個欄位
                                'deptno': '',  # C# 返回的資料中沒有這個欄位
                                'dclass': 0,   # C# 返回的資料中沒有這個欄位
                                'adm_rank': 0  # C# 返回的資料中沒有這個欄位
                            }

                            result[company_name][current_dept_name].append(emp_data)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失敗: {e}")
            logger.error(f"原始輸出: {json_output}")
            raise Exception(f"JSON 解析失敗: {e}")
        except Exception as e:
            logger.error(f"資料轉換失敗: {e}")
            raise Exception(f"資料轉換失敗: {e}")

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

