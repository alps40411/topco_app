# backend/app/main.py

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings
from typing import Dict
import time

from fastapi.staticfiles import StaticFiles

# --- 引入所有需要的 API 路由 ---
from app.api import records, projects, supervisor, users, auth, documents, comments

app = FastAPI(
    title="TSC 業務日誌 API",
    description="這是 TSC 業務日誌的後端 API 服務。",
    version="0.1.0",
)

# --- 掛載 storage 資料夾為靜態檔案目錄 ---
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# 最寬鬆的CORS設置，允許所有來源
origins = ["*"]  # 允許所有來源

print(f"CORS允許的來源: {origins}")

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
    print(f"{request.method} {request.url.path} - 開始處理")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"{request.method} {request.url.path} - 完成 ({response.status_code}) - {process_time:.2f}s")
    
    return response

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
app.include_router(comments.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to TSC Business Log API"}