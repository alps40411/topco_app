# backend/app/api/legacy_reports.py
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from ..core.legacy_database import get_legacy_db
from ..core.deps import get_current_user
from ..core.config import settings
from ..models.user import User
from ..services.legacy_service_v2 import LegacyReportServiceV2
from ..services.record_service import RecordService
from ..services.draft_service import DraftService
from ..schemas.legacy_schemas import (
    DailyReportListItem, DailyReportContent, WorkPlan,
    DraftSaveRequest, AttachmentSaveRequest,
    ReportSubmitRequest, DraftResponse, SubmitResponse
)
import logging
import json
import os
import uuid
import aiofiles
from datetime import datetime, timedelta, time
from pathlib import Path
from functools import lru_cache

router = APIRouter(prefix="/legacy", tags=["legacy-reports"])
logger = logging.getLogger(__name__)

# 簡單的內存緩存
_work_data_cache = {}
_cache_timeout = timedelta(minutes=10)  # 緩存 10 分鐘


@router.get("/api-status")
async def get_api_status():
    """獲取API配置狀態，幫助前端了解後端邏輯"""
    return {
        "message": "Legacy Reports API Status",
        "work_plan_config": {
            "is_required": False,
            "description": "工作計畫為非必填項目",
            "default_option": "請選擇工作計畫"
        },
        "execution_work_config": {
            "is_required": True,
            "description": "執行工作為必填項目",
            "depends_on_work_plan": False,
            "note": "不管是否選擇工作計畫，都可以選擇執行工作"
        },
        "work_item_config": {
            "is_required": True,
            "description": "工作項目為必填項目",
            "depends_on_execution_work": True
        },
        "service_target_config": {
            "is_required": False,
            "description": "服務對象為非必填項目"
        }
    }
# === Projects API (前端相容性) ===
projects_router = APIRouter(prefix="/projects", tags=["projects"])

@projects_router.get("/")
async def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_legacy_db)
):
    """取得專案/工作計畫列表"""
    try:
        if not current_user.employee:
            raise HTTPException(status_code=400, detail="用戶沒有員工資訊")
        
        empno = current_user.employee.empno
        
        # 取得工作計畫列表
        projects_sql = text("""
            SELECT DISTINCT A.planno, A.plan_subj_c
            FROM jps.tjp_master A
            WHERE (A.empno = :empno OR A.pm_empno = :empno)
            AND (A.plan_date2 IS NULL OR A.plan_date2 >= TO_CHAR(CURRENT_DATE,'YYYYMMDD'))
            ORDER BY A.planno DESC
        """)
        
        result = db.execute(projects_sql, {"empno": empno})
        
        projects = []
        for row in result.fetchall():
            projects.append({
                "id": row[0],  # planno
                "plan_subj_c": row[1] or f"工作計畫 {row[0]}",
                "name": row[1] or f"工作計畫 {row[0]}"  # 別名，以防前端期待 name 欄位
            })
        
        return projects
        
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得專案列表失敗: {str(e)}")

# ✅ REMOVED: /api/legacy/daily-date-range - Replaced by /api/dates/range

