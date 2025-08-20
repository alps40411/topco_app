@echo off
chcp 65001 >nul
echo 啟動TOPCO日報系統...
echo.
echo 後端服務: http://192.168.56.1:8000
echo 前端服務: http://192.168.56.1:3000
echo 請讓同事使用: http://192.168.56.1:3000
echo.
cd /d "D:\topco\Desktop\topco_app\"
start "後端服務" cmd /k "cd backend && venv\Scripts\activate.bat && python start_production.py"
timeout /t 3 /nobreak > nul
start "前端服務" cmd /k "cd frontend && npm run preview:production"
timeout /t 5 /nobreak > nul
start "" "http://192.168.56.1:3000"
