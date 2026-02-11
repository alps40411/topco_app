# backend/app/services/commonapi_file_service.py

import logging
import httpx
from typing import Dict, Any
from fastapi import UploadFile, HTTPException

from ..core.config import settings

logger = logging.getLogger(__name__)

class CommonApiFileService:
    """CommonAPI 檔案上傳服務"""

    @staticmethod
    async def upload_file(
        file: UploadFile,
        cocode: str,
        csrf_token: str = ""
    ) -> Dict[str, Any]:
        """
        上傳檔案至 CommonAPI

        Args:
            file: 上傳的檔案
            cocode: 公司代碼
            csrf_token: CSRF Token (如需要)

        Returns:
            檔案資訊，包含 FileId 和 URL
        """
        try:
            logger.info(f"開始上傳檔案至 CommonAPI: {file.filename}, cocode={cocode}")

            # 檢查副檔名
            ALLOWED_EXTENSIONS = {
                '.pdf', '.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt',
                '.rtf', '.odt', '.ods', '.wps', '.pages', '.txt', '.csv',
                '.jpg', '.png', '.jpeg', '.webp', '.gif',
                '.zip', '.rar', '.7z',
                '.ai', '.psd', '.dwg', '.eps', '.vsdx',
                '.mp4', '.avi',
                '.log', '.eml', '.ics', '.kml', '.xml',
            }
            filename = file.filename or ""
            ext = filename.lower()[filename.rfind('.'):] if '.' in filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=415,
                    detail=f"不支援的檔案格式: {ext}"
                )

            # 讀取檔案內容
            content = await file.read()

            # 檢查檔案大小
            if len(content) > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"檔案太大，最大允許 {settings.MAX_FILE_SIZE // (1024*1024)}MB"
                )

            # 重置檔案指針以便後續可能的重用
            await file.seek(0)

            # 準備上傳
            async with httpx.AsyncClient(timeout=30.0) as client:
                # ✅ 直接使用原始檔名上傳（包括剪貼簿的 image.png）
                files = {
                    'file': (file.filename, content, file.content_type or 'application/octet-stream')
                }

                headers = {}
                if csrf_token:
                    headers['X-CSRF-TOKEN'] = csrf_token

                logger.info(f"調用 CommonAPI 上傳: {settings.COMMONAPI_UPLOAD_URL}")

                response = await client.post(
                    settings.COMMONAPI_UPLOAD_URL,
                    files=files,
                    headers=headers
                )

                if response.status_code != 200:
                    logger.error(f"CommonAPI 上傳失敗: {response.status_code}, {response.text}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"CommonAPI 上傳失敗: {response.text}"
                    )

                # 解析 CommonAPI 回應
                result = response.json()
                logger.info(f"CommonAPI 上傳成功，回應類型: {type(result)}, 內容: {result}")

                # CommonAPI 回應格式可能是：
                # 1. 字典: {"FileId": "xxx", ...}
                # 2. 陣列: ["fileid1", "fileid2", ...]
                # 3. 字串: "fileid"

                file_id = None

                if isinstance(result, dict):
                    # 字典格式
                    file_id = result.get('FileId') or result.get('fileid') or result.get('path', '')
                    logger.info(f"回應格式為字典，提取 FileId: {file_id}")
                elif isinstance(result, list):
                    # 陣列格式 - 取第一個元素
                    if len(result) > 0:
                        file_id = result[0]
                        logger.info(f"回應格式為陣列，取第一個元素: {file_id}")
                    else:
                        logger.error("回應是空陣列")
                        raise HTTPException(status_code=500, detail="CommonAPI 返回空陣列")
                elif isinstance(result, str):
                    # 字串格式
                    file_id = result
                    logger.info(f"回應格式為字串: {file_id}")
                else:
                    logger.error(f"未知的回應格式: {type(result)}")
                    file_id = str(result)

                if not file_id:
                    logger.error("無法從 CommonAPI 回應中提取 FileId")
                    raise HTTPException(status_code=500, detail="CommonAPI 未返回 FileId")

                # 移除可能的逗號（根據您提供的範例）
                file_id = str(file_id).replace(',', '').strip()
                logger.info(f"最終 FileId: {file_id}")

                # ✅ 直接使用 CommonAPI 回傳的 FileId 作為相對路徑
                # 移除開頭的斜線（如果有的話）
                file_path = file_id.lstrip('/')

                logger.info(f"檔案相對路徑（ATT_FILE2）: {file_path}")

                # 構建下載 URL（使用原始檔名）
                download_url = (
                    f"{settings.COMMONAPI_DOWNLOAD_URL}"
                    f"?FileId={file_id}"
                    f"&Type=upimages"
                    f"&CoCode={cocode}"
                    f"&FileName={file.filename}"
                )

                return {
                    "id": file_id,
                    "name": file.filename,  # ✅ ATT_FILE1: 原始檔名 (剪貼簿是 image.png，其他是用戶上傳的檔名)
                    "file_path": file_path,  # ✅ ATT_FILE2: CommonAPI 回傳的相對路徑 (例如：202510/140927170.png)
                    "type": file.content_type or "application/octet-stream",
                    "size": len(content),
                    "url": download_url,  # 前端顯示用的完整 URL
                    "source": "commonapi",
                    "status": "success"
                }

        except httpx.TimeoutException:
            logger.error("CommonAPI 上傳超時")
            raise HTTPException(status_code=504, detail="檔案上傳超時，請稍後再試")
        except httpx.RequestError as e:
            logger.error(f"CommonAPI 請求錯誤: {str(e)}")
            raise HTTPException(status_code=500, detail=f"檔案上傳失敗: 網路錯誤")
        except Exception as e:
            logger.error(f"上傳檔案時發生錯誤: {str(e)}")
            raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {str(e)}")

    @staticmethod
    def generate_download_url(file_id: str, filename: str, cocode: str) -> str:
        """
        生成 CommonAPI 檔案下載 URL

        Args:
            file_id: 檔案ID
            filename: 檔案名稱
            cocode: 公司代碼

        Returns:
            完整的下載 URL
        """
        return (
            f"{settings.COMMONAPI_DOWNLOAD_URL}"
            f"?FileId={file_id}"
            f"&Type=upimages"
            f"&CoCode={cocode}"
            f"&FileName={filename}"
        )
