# backend/app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    # Database settings
    SOURCE_DB_USER: str = ""
    SOURCE_DB_PASSWORD: str = ""
    
    # Legacy PostgreSQL Database settings
    LEGACY_DB_URL: str = ""
    LEGACY_DB_USER: str = ""
    LEGACY_DB_PASSWORD: str = ""
    LEGACY_DB_HOST: str = ""
    LEGACY_DB_PORT: str = "5432"
    LEGACY_DB_SERVICE: str = ""  # database name

    # Azure OpenAI settings
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = ""

    # Azure Document Intelligence settings
    AZURE_DOC_INTELLIGENCE_KEY: str = ""
    AZURE_DOC_INTELLIGENCE_ENDPOINT: str = ""

    # JWT settings
    SECRET_KEY: str = ""

    # SSO 配置
    SSO_ENABLED: bool = True
    SSO_MOCK_ENABLED: bool = False  # 關閉 Mock，避免自動登入
    SSO_MOCK_EMPNO: str = "05489"
    SSO_MOCK_COCODE: str = "A"

    # JWT 配置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 小時

    # CORS origins (comma-separated). Example: http://localhost:5173,https://your.domain
    CORS_ORIGINS: str = ""

    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    STATIC_URL_PREFIX: str = ""  # 靜態檔案 URL 前綴，例如 /MyReportAI

    # CommonAPI 配置
    WFINBOX_API_URL: str = "http://10.129.7.248/CommonApi/EIP/ChangeWFINBOX"
    MYREPORT_GET_WRITABLE_DATE_URL: str = "http://10.129.7.248/CommonApi/MyReport/GetWritableDate"
    MYREPORT_GET_FORWARD_LIST_URL: str = "http://10.129.7.248/CommonApi/MyReport/GetForwardList"



    class Config:
        # 將 .env 鎖定為 backend 目錄下的 .env，避免從不同工作目錄啟動時找不到
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        extra = "ignore"


settings = Settings()