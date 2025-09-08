@echo off
ECHO Starting Backend Server (FastAPI)...
REM 啟動一個新的命令視窗來執行後端伺服器
REM /D "backend" 參數確保命令在 backend 資料夾內執行
START "Backend" /D "backend" cmd /c "call venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000"

ECHO Starting Frontend Server (Vite)...
REM 啟動另一個新的命令視窗來執行前端開發伺服器
REM /D "frontend" 參數確保命令在 frontend 資料夾內執行
REM npm run dev 後面的 -- --host 是為了將 --host 參數傳遞給 vite
START "Frontend" /D "frontend" cmd /c "npm run dev -- --host"

ECHO Both servers are starting in separate windows.
