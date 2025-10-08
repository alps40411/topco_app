# backend/app/middleware/api_monitoring.py

"""
API 監控中間件
追蹤所有 API 呼叫，特別是棄用的 API
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import time
from typing import Callable
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class APIMonitoringMiddleware(BaseHTTPMiddleware):
    """
    監控所有 API 請求
    - 記錄請求時間
    - 追蹤響應時間
    - 標記棄用 API 呼叫
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.deprecated_endpoints = self._load_deprecated_endpoints()
        self.stats = {
            "total_requests": 0,
            "deprecated_requests": 0,
            "error_requests": 0,
        }

    def _load_deprecated_endpoints(self) -> set:
        """載入已棄用的端點列表"""
        return {
            # legacy_reports.py
            "/api/legacy/reports",
            "/api/legacy/reports/{daily_no}/content",
            "/api/legacy/work-plans",
            "/api/legacy/companies",
            "/api/legacy/attachments",
            "/api/legacy/work-items",
            "/api/legacy/service-companies",
            "/api/legacy/test-tables",

            # ai.py
            "/api/ai/suggestions/{report_id}",
            "/api/ai/enhance_all",
            "/api/ai/status",

            # reports.py
            "/api/reports/",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """處理請求並記錄統計"""
        start_time = time.time()
        path = request.url.path
        method = request.method

        # 檢查是否為棄用端點
        is_deprecated = self._is_deprecated_endpoint(path)

        # 記錄請求開始
        logger.info(f"[API] {method} {path} {'[DEPRECATED]' if is_deprecated else ''}")

        # 執行請求
        try:
            response = await call_next(request)

            # 計算響應時間
            duration = time.time() - start_time

            # 記錄詳細資訊
            self._log_request(
                method=method,
                path=path,
                status_code=response.status_code,
                duration=duration,
                is_deprecated=is_deprecated,
                user_agent=request.headers.get("user-agent", "unknown"),
                client_ip=request.client.host if request.client else "unknown"
            )

            # 更新統計
            self.stats["total_requests"] += 1
            if is_deprecated:
                self.stats["deprecated_requests"] += 1
            if response.status_code >= 400:
                self.stats["error_requests"] += 1

            # 為棄用 API 添加警告 header
            if is_deprecated:
                response.headers["X-API-Deprecated"] = "true"
                response.headers["X-API-Deprecation-Warning"] = "This endpoint is deprecated and will be removed in a future version"

            return response

        except Exception as e:
            logger.error(f"[API ERROR] {method} {path}: {str(e)}")
            self.stats["error_requests"] += 1
            raise

    def _is_deprecated_endpoint(self, path: str) -> bool:
        """檢查端點是否已棄用"""
        # 精確匹配
        if path in self.deprecated_endpoints:
            return True

        # 模糊匹配 (處理路徑參數)
        for deprecated_path in self.deprecated_endpoints:
            if self._path_matches(path, deprecated_path):
                return True

        return False

    def _path_matches(self, actual_path: str, pattern_path: str) -> bool:
        """匹配路徑模式 (支援 {param} 語法)"""
        actual_parts = actual_path.strip("/").split("/")
        pattern_parts = pattern_path.strip("/").split("/")

        if len(actual_parts) != len(pattern_parts):
            return False

        for actual, pattern in zip(actual_parts, pattern_parts):
            # 如果是參數 (例如 {daily_no})，跳過
            if pattern.startswith("{") and pattern.endswith("}"):
                continue
            # 否則必須完全匹配
            if actual != pattern:
                return False

        return True

    def _log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        is_deprecated: bool,
        user_agent: str,
        client_ip: str
    ):
        """記錄詳細的請求資訊到日誌檔案"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration * 1000, 2),
            "is_deprecated": is_deprecated,
            "user_agent": user_agent,
            "client_ip": client_ip,
        }

        # 記錄到一般日誌
        logger.info(
            f"[API METRICS] {method} {path} - "
            f"Status: {status_code}, "
            f"Duration: {log_entry['duration_ms']}ms"
            f"{' [DEPRECATED]' if is_deprecated else ''}"
        )

        # 如果是棄用 API，記錄到特殊日誌
        if is_deprecated:
            self._log_deprecated_api(log_entry)

    def _log_deprecated_api(self, log_entry: dict):
        """專門記錄棄用 API 的呼叫"""
        # 建立 logs 目錄
        log_dir = Path("backend/logs")
        log_dir.mkdir(exist_ok=True, parents=True)

        # 寫入棄用 API 日誌
        deprecated_log_file = log_dir / "deprecated_api_calls.jsonl"
        with open(deprecated_log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        logger.warning(
            f"[DEPRECATED API CALL] {log_entry['method']} {log_entry['path']} - "
            f"Client: {log_entry['client_ip']}, "
            f"UA: {log_entry['user_agent'][:50]}"
        )

    def get_stats(self) -> dict:
        """取得統計資訊"""
        deprecated_rate = 0
        if self.stats["total_requests"] > 0:
            deprecated_rate = (
                self.stats["deprecated_requests"] / self.stats["total_requests"] * 100
            )

        error_rate = 0
        if self.stats["total_requests"] > 0:
            error_rate = (
                self.stats["error_requests"] / self.stats["total_requests"] * 100
            )

        return {
            **self.stats,
            "deprecated_rate_percent": round(deprecated_rate, 2),
            "error_rate_percent": round(error_rate, 2),
        }
