# backend/app/api/records.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, time, timedelta

from app.core.database import get_db
from app.schemas.work_record import WorkRecord, WorkRecordCreate, WorkRecordInList, FileAttachment, ConsolidatedReport, WorkRecordUpdate, AIEnhanceRequest, ConsolidatedReportUpdate
from app.services import records_service, file_service, azure_ai_service
from app.core import deps
from app.models.user import User

router = APIRouter(tags=["Work Records"])

def check_writing_time_allowed() -> tuple[bool, str]:
    """
    檢查當前時間是否允許填寫日報
    填寫時間：早上8:30到隔天早上8:30
    
    Returns:
        tuple[bool, str]: (是否允許填寫, 提示訊息)
    """
    now = datetime.now()
    current_time = now.time()
    
    # 實際上任何時間都可以填寫，但會給予不同的提示訊息
    if current_time >= time(8, 30):
        return True, f"正在填寫 {now.strftime('%Y-%m-%d')} 的日報"
    else:
        yesterday = now - timedelta(days=1)
        return True, f"正在填寫 {yesterday.strftime('%Y-%m-%d')} 的日報（延長填寫時間）"

@router.get("/writing-status")
async def get_writing_status():
    """獲取當前填寫狀態和提示訊息"""
    allowed, message = check_writing_time_allowed()
    return {
        "allowed": allowed,
        "message": message,
        "current_time": datetime.now().strftime('%H:%M')
    }

# upload 端點不變
@router.post("/upload", response_model=FileAttachment)
async def upload_file(file: UploadFile = File(...)):
    saved_path = file_service.save_upload_file(upload_file=file)
    return FileAttachment(id=0, name=file.filename, type=file.content_type, size=file.size, url=saved_path)

@router.post("/", response_model=WorkRecord, status_code=201)
async def create_work_record(
    *,
    db: AsyncSession = Depends(get_db),
    record_in: WorkRecordCreate,
    current_user: User = Depends(deps.get_current_user_with_employee)
):
    employee_id = current_user.employee.id
    new_record = await records_service.create(db=db, obj_in=record_in, employee_id=employee_id)
    return new_record

@router.get("/today", response_model=List[WorkRecordInList])
async def get_today_records(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user_with_employee)
):
    employee_id = current_user.employee.id
    records = await records_service.get_multi_by_employee_today(db=db, employee_id=employee_id)
    return records

@router.get("/consolidated/today", response_model=List[ConsolidatedReport])
async def get_consolidated_today_records(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user_with_employee)
):
    employee_id = current_user.employee.id
    consolidated_reports = await records_service.get_consolidated_today(db=db, employee_id=employee_id)
    return consolidated_reports

# --- ↓↓↓ 已重構的 PUT 端點 ↓↓↓ ---
@router.put("/consolidated/{project_id}", status_code=204)
async def update_consolidated_report_endpoint(
    project_id: int,
    report_in: ConsolidatedReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user_with_employee)
):
    """
    更新指定專案的彙整報告內容，包含檔案列表。
    """
    try:
        
        success = await records_service.update_consolidated_report(
            db=db,
            project_id=project_id,
            content=report_in.content,
            files=report_in.files,
            employee_id=current_user.employee.id
        )
        
        if not success:
            print(f"DEBUG: 更新失敗 - 找不到對應的專案或記錄")
            raise HTTPException(status_code=404, detail="找不到對應的專案或記錄可更新")
        
        return
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: 更新 consolidated report 時發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"內部服務器錯誤: {str(e)}")

@router.post("/ai/enhance", response_model=str)
async def enhance_report_with_ai(
    *,
    request_body: AIEnhanceRequest
):
    """
    將報告內容傳送給 AI 進行潤飾。
    """
    enhanced_content = await azure_ai_service.get_ai_enhanced_report(
        original_content=request_body.content,
        project_name=request_body.project_name
    )
    return enhanced_content

@router.post("/ai/enhance_all", response_model=List[ConsolidatedReport])
async def enhance_all_reports_with_ai(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user_with_employee)
):
    """一鍵潤飾今天所有的彙整報告"""
    print(f"[API] /ai/enhance_all 被呼叫 - user_id: {current_user.id}, employee_id: {current_user.employee.id}")
    try:
        result = await records_service.enhance_all_today(db=db, employee_id=current_user.employee.id)
        print(f"[SUCCESS] API: enhance_all_today 執行成功，返回 {len(result)} 個報告")
        return result
    except Exception as e:
        print(f"[ERROR] API: enhance_all_today 執行失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@router.post("/ai/enhance_one/{project_id}", response_model=ConsolidatedReport)
async def enhance_one_report_with_ai(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user_with_employee)
):
    """潤飾今天單一一個專案報告"""
    enhanced_report = await records_service.enhance_one_today(
        db=db, 
        employee_id=current_user.employee.id, 
        project_id=project_id
    )
    if not enhanced_report:
        raise HTTPException(status_code=404, detail="找不到該專案今日的報告紀錄")
    return enhanced_report

