# backend/app/api/records.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.work_record import WorkRecord, WorkRecordCreate, WorkRecordInList, FileAttachment, ConsolidatedReport, WorkRecordUpdate, AIEnhanceRequest, ConsolidatedReportUpdate
from app.services import records_service, file_service, azure_ai_service
from app.core import deps
from app.models.user import User

router = APIRouter(tags=["Work Records"])

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
    current_user: User = Depends(deps.get_current_user)
):
    employee_id = current_user.id
    new_record = await records_service.create(db=db, obj_in=record_in, employee_id=employee_id)
    return new_record

@router.get("/today", response_model=List[WorkRecordInList])
async def get_today_records(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    employee_id = current_user.id
    records = await records_service.get_multi_by_employee_today(db=db, employee_id=employee_id)
    return records

@router.get("/consolidated/today", response_model=List[ConsolidatedReport])
async def get_consolidated_today_records(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    employee_id = current_user.id
    consolidated_reports = await records_service.get_consolidated_today(db=db, employee_id=employee_id)
    return consolidated_reports

# --- ↓↓↓ 已重構的 PUT 端點 ↓↓↓ ---
@router.put("/consolidated/{project_id}", status_code=204)
async def update_consolidated_report_endpoint(
    project_id: int,
    report_in: ConsolidatedReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    更新指定專案的彙整報告內容，包含檔案列表。
    """
    try:
        print(f"DEBUG: 收到更新請求 - project_id: {project_id}, user_id: {current_user.id}")
        print(f"DEBUG: content 長度: {len(report_in.content)}")
        print(f"DEBUG: files 數量: {len(report_in.files)}")
        
        success = await records_service.update_consolidated_report(
            db=db,
            project_id=project_id,
            content=report_in.content,
            files=report_in.files,
            employee_id=current_user.id
        )
        
        if not success:
            print(f"DEBUG: 更新失敗 - 找不到對應的專案或記錄")
            raise HTTPException(status_code=404, detail="找不到對應的專案或記錄可更新")
        
        print(f"DEBUG: 更新成功")
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
    current_user: User = Depends(deps.get_current_user)
):
    """一鍵潤飾今天所有的彙整報告"""
    return await records_service.enhance_all_today(db=db, employee_id=current_user.id)


@router.post("/ai/enhance_one/{project_id}", response_model=ConsolidatedReport)
async def enhance_one_report_with_ai(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """潤飾今天單一一個專案報告"""
    enhanced_report = await records_service.enhance_one_today(
        db=db, 
        employee_id=current_user.id, 
        project_id=project_id
    )
    if not enhanced_report:
        raise HTTPException(status_code=404, detail="找不到該專案今日的報告紀錄")
    return enhanced_report

