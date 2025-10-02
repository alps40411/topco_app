# backend/app/services/wfinbox_service.py
"""
Wfinbox 服務層
透過 C# WfinboxRecoveryService.exe 更新 Oracle wfinbox 資料表狀態
"""
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WfinboxService:
    """工作流信箱服務"""

    def __init__(self):
        # 取得 C# 執行檔路徑
        backend_dir = Path(__file__).parent.parent.parent
        self.exe_path = backend_dir / "WfinboxRecoveryService.exe"

        if not self.exe_path.exists():
            logger.warning(f"找不到 WfinboxRecoveryService.exe: {self.exe_path}")

    @staticmethod
    def update_status_to_read(empno: str, serino: str) -> bool:
        """
        更新 wfinbox 狀態為已讀 (xstatus = '3')
        透過調用 C# 程式直接執行 SQL UPDATE

        Args:
            empno: 員工編號（主管工號）
            serino: 日報編號 (daily_no)

        Returns:
            bool: 更新是否成功
        """
        try:
            backend_dir = Path(__file__).parent.parent.parent
            exe_path = backend_dir / "WfinboxRecoveryService.exe"

            if not exe_path.exists():
                logger.error(f"找不到 WfinboxRecoveryService.exe: {exe_path}")
                return False

            logger.info(f"[WFINBOX] 調用 WfinboxRecovery: empno={empno}, serino={serino}")

            # 執行 C# 程式
            # 注意：WfinboxRecoveryService.exe 接收參數順序為 empno, serino
            # 但內部會調用 MyReport.dll 的 WfinboxRecovery(serino, empno)
            result = subprocess.run(
                [str(exe_path), empno, serino],
                capture_output=True,
                text=True,
                timeout=30,  # 30秒超時
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                logger.error(f"[WFINBOX] C# 程式執行失敗: {result.stderr}")
                return False

            # 解析 JSON 輸出
            try:
                output_data = json.loads(result.stdout.strip())

                if output_data.get("error"):
                    logger.error(f"[WFINBOX] 執行錯誤: {output_data.get('message')}")
                    return False

                if output_data.get("success"):
                    logger.info(f"[WFINBOX] 更新成功: empno={empno}, serino={serino}")
                    return True
                else:
                    logger.warning(f"[WFINBOX] 未知的回應: {output_data}")
                    return False

            except json.JSONDecodeError as e:
                logger.error(f"[WFINBOX] JSON 解析失敗: {e}, output: {result.stdout}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("[WFINBOX] C# 程式執行超時")
            return False
        except Exception as e:
            logger.error(f"[WFINBOX] 更新失敗: {str(e)}")
            return False
