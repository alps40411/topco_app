# backend/app/services/wfinbox_service.py
"""
Wfinbox 服務層
透過 CommonAPI 更新 Oracle wfinbox 資料表狀態
"""
import httpx
import logging
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

class WfinboxService:
    """工作流信箱服務"""

    @staticmethod
    def update_status_to_read(empno: str, serino: str) -> bool:
        """
        更新 wfinbox 狀態為已讀 (xstatus = '3')
        透過調用 CommonAPI 的 ChangeWFINBOX 接口

        Args:
            empno: 員工編號（主管/部屬工號）
            serino: 日報編號 (daily_no)

        Returns:
            bool: 更新是否成功
        """
        try:
            logger.info(f"[WFINBOX] 調用 CommonAPI: empno={empno}, serino={serino}")

            # 構造請求參數
            payload = {
                "XSTATUS": "3",      # 狀態：3 = 已讀
                "EMPNO": empno,      # 員工編號
                "SOURCE": "003",  # 來源系統：003 = 日報系統
                "SERINO": serino     # 日報編號
            }

            # 發送 POST 請求
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    settings.WFINBOX_API_URL,
                    json=payload
                )

                # 檢查 HTTP 狀態碼
                if response.status_code != 200:
                    logger.error(f"[WFINBOX] API 請求失敗: status_code={response.status_code}, response={response.text}")
                    return False

                # 解析回應
                result = response.json()
                logger.info(f"[WFINBOX] API 回應: {result}")

                # 判斷是否成功
                # CommonAPI 標準回應格式: ResponseNo = "0000" 表示成功
                response_no = result.get("ResponseNo", "")

                if response_no == "0000":
                    logger.info(f"[WFINBOX] 更新成功: empno={empno}, serino={serino}")
                    return True
                else:
                    logger.warning(f"[WFINBOX] 更新失敗，ResponseNo={response_no}, API 回應: {result}")
                    return False

        except httpx.TimeoutException:
            logger.error("[WFINBOX] API 請求超時")
            return False
        except httpx.RequestError as e:
            logger.error(f"[WFINBOX] 網路請求錯誤: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[WFINBOX] 更新失敗: {str(e)}")
            return False
