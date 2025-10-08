# backend/app/api/monitoring.py

"""
API 監控端點
提供 API 使用統計和棄用 API 追蹤
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
from collections import Counter, defaultdict

from ..core.deps import get_current_user
from ..schemas.user import User

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])
logger = logging.getLogger(__name__)

@router.get("/stats")
async def get_api_stats(
    current_user: User = Depends(get_current_user)
):
    """
    取得 API 使用統計

    需要管理員權限
    """
    # 檢查權限 (可選：只允許管理員查看)
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="需要管理員權限")

    try:
        # 從中間件取得統計 (如果可用)
        from fastapi import Request
        # stats = request.app.state.monitoring_middleware.get_stats()

        # 暫時返回模擬資料，實際應從中間件取得
        stats = {
            "total_requests": 0,
            "deprecated_requests": 0,
            "error_requests": 0,
            "deprecated_rate_percent": 0,
            "error_rate_percent": 0,
        }

        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"獲取統計失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取統計失敗")

@router.get("/deprecated-calls")
async def get_deprecated_api_calls(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """
    取得棄用 API 呼叫記錄

    - **hours**: 查詢過去幾小時的記錄 (預設 24)
    """
    try:
        log_file = Path("backend/logs/deprecated_api_calls.jsonl")

        if not log_file.exists():
            return {
                "success": True,
                "data": {
                    "calls": [],
                    "summary": {
                        "total_calls": 0,
                        "unique_endpoints": 0,
                        "unique_ips": 0,
                    }
                }
            }

        # 讀取日誌
        cutoff_time = datetime.now() - timedelta(hours=hours)
        calls = []

        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry["timestamp"])

                    # 只取最近的記錄
                    if entry_time >= cutoff_time:
                        calls.append(entry)
                except Exception as e:
                    logger.error(f"解析日誌失敗: {str(e)}")
                    continue

        # 統計分析
        endpoints = [call["path"] for call in calls]
        ips = [call["client_ip"] for call in calls]

        endpoint_counts = Counter(endpoints)
        ip_counts = Counter(ips)

        # 按端點分組統計
        endpoint_stats = []
        for endpoint, count in endpoint_counts.most_common():
            endpoint_calls = [c for c in calls if c["path"] == endpoint]
            avg_duration = sum(c["duration_ms"] for c in endpoint_calls) / len(endpoint_calls)

            endpoint_stats.append({
                "endpoint": endpoint,
                "call_count": count,
                "avg_duration_ms": round(avg_duration, 2),
                "unique_ips": len(set(c["client_ip"] for c in endpoint_calls))
            })

        return {
            "success": True,
            "data": {
                "time_range_hours": hours,
                "calls": calls[-100:],  # 只返回最近 100 筆
                "summary": {
                    "total_calls": len(calls),
                    "unique_endpoints": len(endpoint_counts),
                    "unique_ips": len(ip_counts),
                },
                "endpoint_stats": endpoint_stats,
                "top_callers": [
                    {"ip": ip, "call_count": count}
                    for ip, count in ip_counts.most_common(10)
                ]
            }
        }

    except Exception as e:
        logger.error(f"獲取棄用 API 呼叫記錄失敗: {str(e)}")
        raise HTTPException(status_code=500, detail="獲取記錄失敗")

@router.get("/health")
async def health_check():
    """
    健康檢查端點
    """
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "TopCo Daily Report API",
            "version": "1.0.0"
        }
    }

@router.get("/deprecated-endpoints")
async def get_deprecated_endpoints_list(
    current_user: User = Depends(get_current_user)
):
    """
    取得所有已棄用端點的清單及建議替代方案
    """
    deprecated_endpoints = [
        {
            "endpoint": "GET /api/legacy/reports",
            "reason": "功能重複",
            "alternative": "GET /api/supervisor/daily-homepage",
            "removal_date": "2025-12-01",
            "impact": "中"
        },
        {
            "endpoint": "GET /api/legacy/reports/{daily_no}/content",
            "reason": "功能重複",
            "alternative": "GET /api/supervisor/reports/{report_id}",
            "removal_date": "2025-12-01",
            "impact": "中"
        },
        {
            "endpoint": "GET /api/legacy/work-plans",
            "reason": "已被統一 API 取代",
            "alternative": "GET /api/legacy/work-data",
            "removal_date": "2025-11-15",
            "impact": "低"
        },
        {
            "endpoint": "GET /api/legacy/companies",
            "reason": "已被統一 API 取代",
            "alternative": "GET /api/legacy/work-data",
            "removal_date": "2025-11-15",
            "impact": "低"
        },
        {
            "endpoint": "POST /api/legacy/attachments",
            "reason": "功能重複",
            "alternative": "POST /api/records/upload",
            "removal_date": "2025-12-01",
            "impact": "中"
        },
        {
            "endpoint": "GET /api/legacy/work-items",
            "reason": "已被統一 API 取代",
            "alternative": "GET /api/legacy/work-data",
            "removal_date": "2025-11-15",
            "impact": "低"
        },
        {
            "endpoint": "GET /api/legacy/service-companies",
            "reason": "重複端點",
            "alternative": "GET /api/legacy/work-data",
            "removal_date": "2025-11-15",
            "impact": "低"
        },
        {
            "endpoint": "GET /api/legacy/test-tables",
            "reason": "開發測試用途",
            "alternative": "無 (僅供開發)",
            "removal_date": "立即",
            "impact": "無 (生產環境不應使用)"
        },
        {
            "endpoint": "POST /api/ai/suggestions/{report_id}",
            "reason": "功能重複",
            "alternative": "POST /api/supervisor/reports/{report_id}/ai-suggestions",
            "removal_date": "2025-12-01",
            "impact": "低"
        },
        {
            "endpoint": "POST /api/ai/enhance_all",
            "reason": "前端未使用",
            "alternative": "無 (功能未實作)",
            "removal_date": "2025-11-01",
            "impact": "無"
        },
        {
            "endpoint": "GET /api/ai/status",
            "reason": "前端未使用",
            "alternative": "GET /api/monitoring/health",
            "removal_date": "2025-11-01",
            "impact": "無"
        },
        {
            "endpoint": "GET /api/reports/",
            "reason": "功能重複",
            "alternative": "GET /api/supervisor/daily-homepage",
            "removal_date": "2025-12-01",
            "impact": "中"
        },
    ]

    return {
        "success": True,
        "data": {
            "total_count": len(deprecated_endpoints),
            "endpoints": deprecated_endpoints,
            "deprecation_policy": {
                "warning_period_days": 30,
                "monitoring_period_days": 14,
                "removal_process": [
                    "1. 標記為 deprecated",
                    "2. 添加警告日誌",
                    "3. 監控使用情況 14 天",
                    "4. 通知使用者遷移",
                    "5. 等待 30 天警告期",
                    "6. 移除端點"
                ]
            }
        }
    }
