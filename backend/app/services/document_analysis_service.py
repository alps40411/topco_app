# backend/app/services/document_analysis_service.py

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from typing import IO
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

def _build_client() -> DocumentIntelligenceClient | None:
    if not settings.AZURE_DOC_INTELLIGENCE_ENDPOINT or not settings.AZURE_DOC_INTELLIGENCE_KEY:
        return None
    
    return DocumentIntelligenceClient(
        endpoint=settings.AZURE_DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_DOC_INTELLIGENCE_KEY),
    )

def _analyze_document_sync(file_stream: IO[bytes]) -> str:
    """
    同步分析文件流的內部函數。
    """
    client = _build_client()
    if client is None:
        return "文件分析服務未啟用或尚未配置。"
    poller = client.begin_analyze_document(
        model_id="prebuilt-read",
        body=file_stream,
        content_type="application/octet-stream"
    )
    result: AnalyzeResult = poller.result()
    return result.content if result.content else "無法從文件中提取任何文字內容。"

async def analyze_document_from_stream(file_stream: IO[bytes]) -> str:
    """
    分析文件流 (來自使用者上傳)，並提取其所有文字內容。
    """
    try:
        # 在線程池中運行阻塞操作
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, _analyze_document_sync, file_stream)
        return result
    except Exception as e:
        return "文件分析服務暫時無法使用。"

def _analyze_document_from_path_sync(file_path: str) -> str:
    """
    同步分析檔案路徑的內部函數。
    """
    client = _build_client()
    if client is None:
        return "文件分析服務未啟用或尚未配置。"
    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id="prebuilt-read",
            body=f,
            content_type="application/octet-stream"
        )
        result: AnalyzeResult = poller.result()
    return result.content if result.content else "無法從文件中提取任何文字內容。"

async def analyze_document_from_path(file_path: str) -> str:
    """
    分析儲存在伺服器上的文件 (來自已儲存的筆記)，並提取其所有文字內容。
    """
    if not os.path.exists(file_path):
        return f"錯誤：找不到檔案路徑 {file_path}"
    
    try:
        # 在線程池中運行阻塞操作
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, _analyze_document_from_path_sync, file_path)
        return result
    except Exception as e:
        return "文件分析服務暫時無法使用。"

# 為向後兼容性提供別名
analyze_document_stream = analyze_document_from_stream