## Windows 部署指南（後端 FastAPI + 前端 Vite React）

本文件說明如何在 Windows 10/11 上部署本專案。請先完成最小必要環境準備，依序完成後端與前端部署。

### 1) 先決條件
- 已安裝 Python 3.11+（建議從 Microsoft Store 或 python.org）
- 已安裝 Node.js 18+（含 npm）
- 已安裝 Git（可選）
- 已安裝 PostgreSQL 14+/15+，並建立資料庫與使用者
  - 例如建立資料庫 `topco_db`，並設定使用者/密碼

### 2) 設定環境變數檔（後端）
1. 進入 `backend` 目錄，複製 `env.sample` 為 `.env`
   - PowerShell：`Copy-Item env.sample .env`
2. 編輯 `.env`，填入：
   - `DATABASE_URL`：PostgreSQL 連線字串（asyncpg）
   - `SECRET_KEY`：JWT 用長隨機字串
   - Azure OpenAI 與 Document Intelligence 的 `KEY`/`ENDPOINT`/`DEPLOYMENT_NAME`
   - `CORS_ORIGINS`（預設 `http://localhost:5173`）

> 注意：程式已在啟動時檢查必要變數，缺少將直接報錯提醒。

### 3) 安裝後端依賴並啟動
```powershell
cd backend
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -U pip
pip install -r requirements.txt

# 初始化資料庫（擇一）
# (A) 使用 Alembic 遷移（推薦）
alembic upgrade head | cat
# (B) 重建資料表並灌入預設資料（會清空資料）
python reset_db.py | cat
python seed_db.py | cat

# 啟動 API（開發/小型部署）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

選用：將後端註冊為 Windows 服務（方便自動啟動）
- 可用 `NSSM` 建立服務（`nssm install`）
  - Application: `C:\path\to\backend\.venv\Scripts\python.exe`
  - Arguments: `-m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
  - AppDirectory: `C:\path\to\backend`（確保能讀到 `.env`）

### 4) 安裝並建置前端
```powershell
cd frontend
npm ci
npm run build
```
產物將輸出於 `frontend/dist`。開發時可用：
```powershell
npm run dev
```
Vite 已於 `vite.config.ts` 設定 `'/api'` 代理至 `http://127.0.0.1:8000`。

### 5) 前端靜態檔案佈署選項
- 小型佈署：`npx serve -s dist -l 5173`
- IIS：設定站台實體路徑指向 `frontend/dist`
  - 若需要 API 反向代理，可安裝 URL Rewrite 與 ARR，將 `^/api/(.*)` 代理至 `http://127.0.0.1:8000/api/{R:1}`

### 6) 安全性與維運
- 請勿將 `.env`、密鑰與憑證加入版本控制
- `backend/requirements.txt` 已精簡並鎖定主要版本
- 定期更新依賴：`pip list --outdated`、`npm outdated`
- 備份資料庫與 .env

### 7) 常見問題
- 啟動報 `缺少必要設定`：請確認 `backend/.env` 存在且內容正確
- `EmailStr` 失敗：請確認已安裝 `email-validator`（已包含於依賴）
- 連線資料庫錯誤：檢查 `DATABASE_URL`、防火牆與 Postgres 服務狀態

