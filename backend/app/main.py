# backend/app/main.py

from fastapi import FastAPI, Request
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings
from typing import Dict
import time

from fastapi.staticfiles import StaticFiles

# --- 引入所有需要的 API 路由 ---
from app.api import supervisor, auth, legacy_reports, reviews, users, reports, drafts, ai, work_data, dates, records

app = FastAPI(
    title="TSC 業務日誌 API",
    description="這是 TSC 業務日誌的後端 API 服務。",
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "認證相關操作",
        },
        {
            "name": "Reports",
            "description": "日報相關操作",
        },
        {
            "name": "Users",
            "description": "用戶相關操作",
        },
    ],
)

# --- 掛載 storage 資料夾為靜態檔案目錄 ---
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# --- 掛載 uploads 資料夾為靜態檔案目錄 ---
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 最寬鬆的CORS設置，允許所有來源
origins = ["*"]  # 允許所有來源

print(f"CORS allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # 當使用 "*" 時必須設為 False
    allow_methods=["*"],  # 允許所有HTTP方法
    allow_headers=["*"],
    expose_headers=["*"],
)

# 添加請求日誌中間件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    print(f"{request.method} {request.url.path} - Start processing")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"{request.method} {request.url.path} - Completed ({response.status_code}) - {process_time:.2f}s")
    
    return response

# 基本啟動前檢查：確保必要環境變數已設定
required_settings: Dict[str, str] = {
    "SECRET_KEY": settings.SECRET_KEY,
}
missing = [name for name, value in required_settings.items() if not value]
if missing:
    missing_str = ", ".join(missing)
    raise RuntimeError(
        f"Missing required settings: {missing_str}. Please create .env file in backend folder or set corresponding environment variables."
    )

# --- 修正：加入 "/api" 前綴以匹配前端代理設定 ---
# 前端透過 Vite 代理將 /api/* 請求轉發到後端
# 所以後端需要註冊 /api/* 路由

# === 新的組織化 API 路由 ===
app.include_router(auth.router, prefix="/api/auth")
app.include_router(users.router, prefix="/api/users")
app.include_router(reports.router, prefix="/api/reports")
app.include_router(drafts.router, prefix="/api/drafts")
app.include_router(records.router, prefix="/api")  # prefix 已在 router 中定義為 /records
app.include_router(ai.router, prefix="/api/ai")
app.include_router(work_data.router, prefix="/api")  # prefix 已在 router 中定義為 /work-data
app.include_router(dates.router, prefix="/api")  # prefix 已在 router 中定義為 /dates

# === 現有的 API 路由（保持向後兼容）===
app.include_router(supervisor.router, prefix="/api/supervisor")
app.include_router(legacy_reports.router, prefix="/api")
# app.include_router(legacy_reports.records_router, prefix="/api")  # 已移至 records.py
app.include_router(legacy_reports.projects_router, prefix="/api")
app.include_router(reviews.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to TSC Business Log API"}