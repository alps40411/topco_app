# backend/app/api/documents.py

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.services import document_analysis_service
from app.core import deps
from app.models.user import User

# --- 關鍵修正：移除這裡的 prefix ---
router = APIRouter(
    tags=["Documents"],
)

# --- 確保 API 受保護 ---
@router.post("/analyze", response_model=str)
async def analyze_document(
    file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user) # <-- 確保端點受保護
):
    """
    接收上傳的檔案，使用 Azure AI Document Intelligence 進行分析，
    並回傳提取出的純文字內容。
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="無法識別檔案類型")
        
    extracted_content = await document_analysis_service.analyze_document_from_stream(file.file)
    
    return extracted_content