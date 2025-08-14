# backend/app/main.py

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings
from typing import Dict

from fastapi.staticfiles import StaticFiles

# --- 引入所有需要的 API 路由 ---
from app.api import records, projects, supervisor, users, auth, documents

app = FastAPI(
    title="TSC 業務日誌 API",
    description="這是 TSC 業務日誌的後端 API 服務。",
    version="0.1.0",
)

# --- 掛載 storage 資料夾為靜態檔案目錄 ---
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()] or [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 基本啟動前檢查：確保必要環境變數已設定
required_settings: Dict[str, str] = {
    "DATABASE_URL": settings.DATABASE_URL,
    "SECRET_KEY": settings.SECRET_KEY,
}
missing = [name for name, value in required_settings.items() if not value]
if missing:
    missing_str = ", ".join(missing)
    raise RuntimeError(
        f"缺少必要設定: {missing_str}. 請在 backend 資料夾建立 .env，或設定對應的系統環境變數。"
    )

# --- 修正：加入 "/api" 前綴以匹配前端代理設定 ---
# 前端透過 Vite 代理將 /api/* 請求轉發到後端
# 所以後端需要註冊 /api/* 路由
app.include_router(auth.router, prefix="/api/auth")
app.include_router(users.router, prefix="/api/users")
app.include_router(records.router, prefix="/api/records")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(supervisor.router, prefix="/api/supervisor")
app.include_router(documents.router, prefix="/api/documents")

@app.get("/")
def read_root():
    return {"message": "Welcome to TSC Business Log API"}