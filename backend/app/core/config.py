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

    # Phison LLM settings
    PHISON_API_URL: str = ""
    PHISON_USERNAME: str = ""
    PHISON_PASSWORD: str = ""

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

    # File upload settings (使用 CommonAPI)
    MAX_FILE_SIZE: int = 6 * 1024 * 1024  # 6MB

    # CommonAPI 配置
    COMMONAPI_BASE_URL: str = "http://10.129.8.248/CommonApi"
    COMMONAPI_UPLOAD_URL: str = "http://10.129.8.248/CommonApi/api/SharedFile/upimages"
    COMMONAPI_DOWNLOAD_URL: str = "http://10.129.8.248/CommonApi/api/SharedFile"
    WFINBOX_API_URL: str = "http://10.129.8.248/CommonApi/EIP/ChangeWFINBOX"
    MYREPORT_GET_WRITABLE_DATE_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetWritableDate"
    MYREPORT_GET_FORWARD_LIST_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetForwardList"
    # 週報列表 API（可在 .env 中配置，預設使用測試環境）
    WEEKLY_REPORT_LIST_API_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetWeeklyReportList"
    # 逾期應收帳款 API
    OVERDUE_AR_API_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetOverdueAR"
    # 營收達成率 API
    REVENUE_API_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetRevenue"
    # 提交週報 API
    SUBMIT_WEEKLY_REPORT_API_URL: str = "http://10.129.8.248/CommonApi/MyReport/SubmitWeeklyReport"
    # 週報詳情 API
    SHOW_WEEKLY_REPORT_API_URL: str = "http://10.129.8.248/CommonApi/MyReport/ShowWeeklyReport"
    # 回覆週報 API
    REPLY_WEEKLY_REPORT_API_URL: str = "http://10.129.8.248/CommonApi/MyReport/ReplyWeeklyReport"
    # 刪除週報 API
    DELETE_WEEKLY_REPORT_API_URL: str = "http://10.129.8.248/CommonApi/MyReport/DeleteWeeklyReport"
    # 週次查詢 API
    GET_WEEKLY_NO_BY_DATE_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetWeeklyNoByDate"
    GET_WEEKLY_PERIOD_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetWeeklyPeriod"
    # 自動繳交週報 API
    SET_AUTO_SUBMIT_URL: str = "http://10.129.8.248/CommonApi/MyReport/SetAutoSubmit"
    GET_AUTO_SUBMIT_RECORDS_URL: str = "http://10.129.8.248/CommonApi/MyReport/GetAutoSubmitRecords"

    # Graylog 設定
    GRAYLOG_HOST: str = ""
    GRAYLOG_PORT: int = 12201
    GRAYLOG_SOURCE: str = "TopcoWebCore"
    APP_VERSION: str = "1.0.0"



    class Config:
        # 將 .env 鎖定為 backend 目錄下的 .env，避免從不同工作目錄啟動時找不到
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        extra = "ignore"


settings = Settings()