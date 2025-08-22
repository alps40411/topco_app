# backend/app/services/records_service.py

from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete
from datetime import date, datetime, time
from typing import List
from app.services import azure_ai_service, document_analysis_service
from app.models import work_record as models
from app.models.project import Project as ProjectModel
from app.schemas.work_record import WorkRecord as WorkRecordSchema, WorkRecordCreate, ConsolidatedReport, FileAttachment as FileAttachmentSchema, WorkRecordUpdate

async def create(db: AsyncSession, *, obj_in: WorkRecordCreate, employee_id: int) -> models.WorkRecord:
    db_obj = models.WorkRecord(
        content=obj_in.content,
        project_id=obj_in.project_id, # <-- 使用 project_id
        employee_id=employee_id,
        execution_time_minutes=obj_in.execution_time_minutes,
    )

    if obj_in.files:
        for file_in in obj_in.files:
            db_file = models.FileAttachment(**file_in.model_dump())
            db_obj.files.append(db_file)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    
    query = select(models.WorkRecord).where(models.WorkRecord.id == db_obj.id).options(
        selectinload(models.WorkRecord.files), 
        selectinload(models.WorkRecord.project) # <-- 預先載入專案資訊
    )
    result = await db.execute(query)
    return result.scalar_one()

async def get_multi_by_employee_today(db: AsyncSession, *, employee_id: int):
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)
    
    query = (
        select(models.WorkRecord)
        .where(
            models.WorkRecord.employee_id == employee_id,
            models.WorkRecord.created_at >= today_start,
            models.WorkRecord.created_at <= today_end
        )
        .options(
            selectinload(models.WorkRecord.files), 
            selectinload(models.WorkRecord.project) # <-- 預先載入專案資訊
        )
        .order_by(models.WorkRecord.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_consolidated_today(db: AsyncSession, *, employee_id: int) -> List[ConsolidatedReport]:
    print(f"[INFO] get_consolidated_today 開始 - employee_id: {employee_id}")
    today_records = await get_multi_by_employee_today(db=db, employee_id=employee_id)
    print(f"   [INFO] 從資料庫取得 {len(today_records)} 筆今日記錄")
    project_groups = defaultdict(lambda: {"content": [], "files": [], "record_count": 0, "project_obj": None, "ai_content": None, "total_execution_time": 0})
    
    for i, record in enumerate(today_records):
        print(f"   [INFO] 處理記錄 {i+1}: project_id={record.project_id}, files={len(record.files)}, execution_time={record.execution_time_minutes}min")
        if record.project:
            proj_id = record.project_id
            # 只有在 content 存在且不為純空白時才加入列表
            if record.content and record.content.strip():
                project_groups[proj_id]["content"].append(record.content.strip())
            
            for j, file in enumerate(record.files):
                print(f"      📎 檔案 {j+1}: {file.name} (is_selected_for_ai: {file.is_selected_for_ai})")
            
            project_groups[proj_id]["files"].extend(record.files)
            project_groups[proj_id]["record_count"] += 1
            project_groups[proj_id]["project_obj"] = record.project
            project_groups[proj_id]["total_execution_time"] += record.execution_time_minutes
            # 以第一筆紀錄的 ai_content 為主
            if project_groups[proj_id]["ai_content"] is None:
                project_groups[proj_id]["ai_content"] = record.ai_content
            
    consolidated_list = []
    for project_id, data in project_groups.items():
        if data["project_obj"]:
            # 過濾掉所有可能的空字串，然後用換行符連接
            valid_content = [c for c in data["content"] if c]
            final_content = "\n\n".join(valid_content)

            files_schema = [FileAttachmentSchema.model_validate(f) for f in data["files"]]
            consolidated_list.append(
                ConsolidatedReport(
                    project=data["project_obj"],
                    content=final_content,
                    files=files_schema,
                    record_count=data["record_count"],
                    ai_content=data["ai_content"],
                    total_execution_time_minutes=data["total_execution_time"],
                )
            )
    return consolidated_list

# --- ↓↓↓ 新增這個函式 ↓↓↓ ---
async def enhance_all_today(db: AsyncSession, *, employee_id: int) -> List[ConsolidatedReport]:
    """一鍵潤飾今天所有的專案報告"""
    print(f"[INFO] enhance_all_today 開始 - employee_id: {employee_id}")
    
    consolidated_reports = await get_consolidated_today(db=db, employee_id=employee_id)
    print(f"[INFO] 取得 {len(consolidated_reports)} 個彙整報告")
    
    for i, report in enumerate(consolidated_reports):
        print(f"🚀 處理第 {i+1} 個報告: {report.project.plan_subj_c}")
        reference_texts = []

        print(f"📁 檢查 {len(report.files)} 個附件")
        for j, file_attachment in enumerate(report.files):
            print(f"   檔案 {j+1}: {file_attachment.name} (is_selected_for_ai: {file_attachment.is_selected_for_ai})")
            if file_attachment.is_selected_for_ai:
                print(f"[INFO] 正在分析檔案: {file_attachment.url}")
                try:
                    # 呼叫文件分析服務讀取檔案內容
                    analyzed_text = await document_analysis_service.analyze_document_from_path(file_attachment.url)
                    print(f"[SUCCESS] 檔案分析成功，提取文字長度: {len(analyzed_text)}")
                    reference_texts.append(analyzed_text)
                except Exception as e:
                    print(f"[ERROR] 檔案分析失敗: {str(e)}")
                    import traceback
                    traceback.print_exc()


        # 呼叫 AI 服務
        print(f"🤖 呼叫 Azure AI 服務 - 專案: {report.project.plan_subj_c}, 參考檔案數: {len(reference_texts)}")
        print(f"[INFO] 原始內容長度: {len(report.content)}")
        try:
            ai_text = await azure_ai_service.get_ai_enhanced_report(
                original_content=report.content,
                project_name=report.project.plan_subj_c,
                reference_texts=reference_texts
            )
            print(f"[SUCCESS] AI 潤飾成功，結果長度: {len(ai_text)}")
            report.ai_content = ai_text
        except Exception as e:
            print(f"[ERROR] AI 潤飾失敗: {str(e)}")
            import traceback
            traceback.print_exc()
            report.ai_content = report.content  # 失敗時使用原始內容
        
        # 將 AI 結果存回資料庫 (只更新第一筆)
        today_start = datetime.combine(date.today(), time.min)
        first_record_query = select(models.WorkRecord).where(
            models.WorkRecord.employee_id == employee_id,
            models.WorkRecord.project_id == report.project.id,
            models.WorkRecord.created_at >= today_start
        ).limit(1)
        
        result = await db.execute(first_record_query)
        record_to_update = result.scalar_one_or_none()
        if record_to_update:
            record_to_update.ai_content = ai_text
            await db.commit()
            
    return consolidated_reports


async def enhance_one_today(db: AsyncSession, *, employee_id: int, project_id: int) -> ConsolidatedReport:


    # 1. 取得該使用者、該專案今天的所有紀錄
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)
    
    query = (
        select(models.WorkRecord)
        .where(
            models.WorkRecord.employee_id == employee_id,
            models.WorkRecord.project_id == project_id,
            models.WorkRecord.created_at >= today_start,
            models.WorkRecord.created_at <= today_end
        )
        .options(
            selectinload(models.WorkRecord.files), 
            selectinload(models.WorkRecord.project)
        )
        .order_by(models.WorkRecord.created_at.asc()) # 確保第一筆是時間最早的
    )
    result = await db.execute(query)
    today_records = result.scalars().all()

    if not today_records:
        print("--- DEBUG結束: 未找到記錄，返回 None ---")
        return None

    # 2. 彙整成單一報告物件
    project_obj = today_records[0].project
    content_list = [r.content for r in today_records]
    files_list = [f for r in today_records for f in r.files]
    
    report = ConsolidatedReport(
        project=project_obj,
        content="\n\n".join(content_list),
        files=[FileAttachmentSchema.model_validate(f) for f in files_list],
        record_count=len(today_records),
        ai_content=today_records[0].ai_content # 使用第一筆的 ai_content
    )

    # 3. 呼叫 AI 服務
    print("準備呼叫 AI 服務...")
    reference_texts = []
    for file_attachment in report.files:
        if file_attachment.is_selected_for_ai:
            analyzed_text = await document_analysis_service.analyze_document_from_path(file_attachment.url)
            reference_texts.append(analyzed_text)
    print(f"AI 文件分析結果: {reference_texts}")

    ai_text = await azure_ai_service.get_ai_enhanced_report(
        original_content=report.content,
        project_name=report.project.plan_subj_c,
        reference_texts=reference_texts
    )
    report.ai_content = ai_text
    print("AI 服務呼叫完成")
    
    # 4. 將 AI 結果存回資料庫 (只更新第一筆)
    record_to_update = today_records[0]
    record_to_update.ai_content = ai_text
    await db.commit()
    await db.refresh(record_to_update)
    print("AI 結果已存回資料庫")
    print("--- DEBUG結束: 成功返回報告 ---")
            
    return report



# --- ↓↓↓ 新增這個函式 ↓↓↓ ---
async def update_ai_report(db: AsyncSession, *, project_id: int, ai_content: str, employee_id: int) -> bool:
    """儲存使用者編輯後的 AI 內容"""
    today_start = datetime.combine(date.today(), time.min)
    
    # 找到今天該專案的第一筆紀錄來儲存 AI 內容
    first_record_query = select(models.WorkRecord).where(
        models.WorkRecord.employee_id == employee_id,
        models.WorkRecord.project_id == project_id,
        models.WorkRecord.created_at >= today_start
    ).limit(1)

    result = await db.execute(first_record_query)
    record_to_update = result.scalar_one_or_none()
    
    if record_to_update:
        record_to_update.ai_content = ai_content
        await db.commit()
        return True
    return False



# --- ↓↓↓ 使用這個功能更完整的版本覆蓋舊的函式 ↓↓↓ ---
async def update_consolidated_report(db: AsyncSession, *, project_id: int, content: str, files: List, employee_id: int) -> bool:
    """
    更新一個專案的彙整報告。
    此版本將智慧處理檔案的新增、刪除與狀態更新。
    """
    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)

    query = select(models.WorkRecord).where(
        models.WorkRecord.employee_id == employee_id,
        models.WorkRecord.project_id == project_id,
        models.WorkRecord.created_at >= today_start,
        models.WorkRecord.created_at <= today_end
    ).options(selectinload(models.WorkRecord.files))
    
    result = await db.execute(query)
    records_to_update = result.scalars().all()

    if not records_to_update:
        print("DEBUG: 沒有找到可更新的記錄")
        return False

    main_record = records_to_update[0]
    main_record.content = content
    
    existing_files_map = {f.url: f for f in main_record.files}
    new_files_map = {f.url: f for f in files}

    # 刪除：存在於舊列表但不存在於新列表的檔案
    for url, file_to_delete in existing_files_map.items():
        if url not in new_files_map:
            await db.delete(file_to_delete)

    # 新增或更新
    for url, new_file_data in new_files_map.items():
        if url in existing_files_map:
            existing_files_map[url].is_selected_for_ai = new_file_data.is_selected_for_ai
        else:
            # 建立新檔案，排除可能的 id 屬性
            file_data = new_file_data.model_dump()
            file_data.pop('id', None)  # 安全地移除 id 如果存在
            new_file = models.FileAttachment(**file_data)
            main_record.files.append(new_file)

    # 刪除除了第一筆之外的所有多餘筆記
    for record in records_to_update[1:]:
        for file_to_delete in record.files:
            await db.delete(file_to_delete)
        await db.delete(record)

    await db.commit()
    return True