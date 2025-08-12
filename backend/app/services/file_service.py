# backend/app/services/file_service.py

from fastapi import UploadFile
import shutil
from pathlib import Path

# 定義儲存檔案的根目錄
STORAGE_PATH = Path("storage")
STORAGE_PATH.mkdir(exist_ok=True) # 如果 storage 資料夾不存在，就建立它

def save_upload_file(upload_file: UploadFile) -> str:
    """
    將上傳的檔案儲存到伺服器上，並回傳檔案的相對路徑。
    """
    # 建立一個安全的路徑來儲存檔案
    file_path = STORAGE_PATH / upload_file.filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    # 回傳相對路徑，讓前端可以引用
    return str(file_path.as_posix()) # 使用 as_posix() 確保路徑是 / 分隔