# backend/app/schemas/work_record.py

from pydantic import BaseModel
from typing import List, Optional
import datetime
from .base_schema import BaseSchema
# 移除 from .project import Project，因為我們將使用前向引用

# --- FileAttachment Schemas (不變) ---
class FileAttachmentBase(BaseModel):
    name: str
    type: Optional[str] = None
    size: Optional[int] = None
    url: str
    is_selected_for_ai: Optional[bool] = False

class FileAttachmentCreate(FileAttachmentBase):
    pass

class FileAttachmentInDB(FileAttachmentBase):
    id: int

class FileAttachment(FileAttachmentInDB):
    class Config:
        from_attributes = True

# --- WorkRecord Schemas (已重構) ---
class WorkRecordBase(BaseModel):
    content: str
    project_id: int

class WorkRecordCreate(WorkRecordBase):
    files: List[FileAttachmentCreate] = []

class WorkRecordUpdate(WorkRecordBase):
    pass

# 這個是在 API 回傳時使用的模型
class WorkRecord(WorkRecordBase):
    id: int
    created_at: datetime.datetime
    employee_id: int
    files: List[FileAttachment] = []
    project: 'Project'
    ai_content: Optional[str] = None

    class Config:
        from_attributes = True

# 用於列表顯示的模型
class WorkRecordInList(BaseModel):
    id: int
    content: str
    created_at: datetime.datetime
    project: 'Project' # <-- 關鍵修正：使用字串 'Project'
    files: List[FileAttachment] = []
    ai_content: Optional[str] = None

    class Config:
        from_attributes = True

# 用於彙整報告的模型
class ConsolidatedReport(BaseModel):
    project: 'Project' # <-- 關鍵修正：使用字串 'Project'
    content: str
    files: List[FileAttachment] = []
    record_count: int
    ai_content: Optional[str] = None

    class Config:
        from_attributes = True

class AIEnhanceRequest(BaseModel):
    project_name: str
    content: str

class ConsolidatedReportUpdate(BaseModel):
    content: str
    files: List[FileAttachmentBase] = []


# --- ↓↓↓ 在所有類別定義完畢後，加入這一段來更新前向引用 ↓↓↓ ---
from .project import Project

WorkRecord.model_rebuild()
WorkRecordInList.model_rebuild()
ConsolidatedReport.model_rebuild()