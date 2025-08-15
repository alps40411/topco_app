# backend/app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = ""
    SOURCE_DB_USER: str = ""
    SOURCE_DB_PASSWORD: str = ""

    # Azure OpenAI settings
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = ""

    # Azure Document Intelligence settings
    AZURE_DOC_INTELLIGENCE_KEY: str = ""
    AZURE_DOC_INTELLIGENCE_ENDPOINT: str = ""

    # JWT settings
    SECRET_KEY: str = ""

    # CORS origins (comma-separated). Example: http://localhost:5173,https://your.domain
    CORS_ORIGINS: str = ""

    @field_validator("DATABASE_URL", mode="before")
    def _clean_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = v.strip().strip('"').strip("'")
            return cleaned
        return v

    class Config:
        # 將 .env 鎖定為 backend 目錄下的 .env，避免從不同工作目錄啟動時找不到
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        extra = "ignore"


settings = Settings()