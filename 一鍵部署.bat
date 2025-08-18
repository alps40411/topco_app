@echo off
chcp 65001 >nul
echo ================================
echo     TOPCO日報系統 - 一鍵部署
echo ================================
echo.

:: 自動獲取IP
set "LOCAL_IP="
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr "192.168"') do (
    for /f "tokens=1" %%j in ("%%i") do (
        set LOCAL_IP=%%j
        goto :found_ip
    )
)
if "%LOCAL_IP%"=="" (
    for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr " 10\."') do (
        for /f "tokens=1" %%j in ("%%i") do (
            set LOCAL_IP=%%j
            goto :found_ip
        )
    )
)
if "%LOCAL_IP%"=="" set LOCAL_IP=localhost

:found_ip
echo 檢測到IP: %LOCAL_IP%
echo.

@REM :: 更新配置
@REM echo [1/5] 更新配置檔案...
@REM echo VITE_API_BASE_URL=http://%LOCAL_IP%:8000 > frontend\.env.production

(
echo # 生產環境配置
echo DATABASE_URL=postgresql+asyncpg://postgres:0000@localhost/topco_db
echo AZURE_OPENAI_KEY=B4dROq5hPmfD3yyvBKbPeTmjrEnLTx3LQroPRwWnQzg2WLP17mrTJQQJ99BHACYeBjFXJ3w3AAABACOGddoP
echo AZURE_OPENAI_ENDPOINT=https://aoai-ragdev-eastus.openai.azure.com/
echo AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
echo AZURE_DOC_INTELLIGENCE_KEY=4pUGXt7l1vbAdQxlJxNL4nKIIPp9Jh4X45pTX6GIBgcMVoP3NNlJJQQJ99BHACYeBjFXJ3w3AAALACOGNdVf
echo AZURE_DOC_INTELLIGENCE_ENDPOINT=https://doc0811.cognitiveservices.azure.com/
echo SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
echo CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://%LOCAL_IP%:3000
echo SOURCE_DB_USER="a05489"
echo SOURCE_DB_PASSWORD="yanb0606"
) > backend\.env.production

:: 設置後端
echo [2/5] 設置後端環境...
cd backend
if not exist "venv" python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt >nul 2>&1
alembic upgrade head
cd ..

:: 構建前端
echo [3/5] 構建前端...
cd frontend
call npm install >nul 2>&1
call npm run build:production
cd ..

:: 開放防火牆
echo [4/5] 設置防火牆...
netsh advfirewall firewall delete rule name="日報系統-前端" >nul 2>&1
netsh advfirewall firewall delete rule name="日報系統-後端" >nul 2>&1
netsh advfirewall firewall add rule name="日報系統-前端" dir=in action=allow protocol=TCP localport=3000 >nul 2>&1
netsh advfirewall firewall add rule name="日報系統-後端" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1

:: 創建啟動腳本
echo [5/5] 創建啟動腳本...
(
echo @echo off
echo echo 啟動頂寶日報系統...
echo echo.
echo echo 後端服務: http://%LOCAL_IP%:8000
echo echo 前端服務: http://%LOCAL_IP%:3000
echo echo 請讓同事使用: http://%LOCAL_IP%:3000
echo echo.
echo start "後端服務" cmd /k "cd backend && venv\Scripts\activate.bat && python start_production.py"
echo timeout /t 3 /nobreak ^> nul
echo start "前端服務" cmd /k "cd frontend && npm run preview:production"
echo timeout /t 5 /nobreak ^> nul
echo start "" "http://%LOCAL_IP%:3000"
) > 啟動系統.bat

echo.
echo ================================
echo          部署完成！
echo ================================
echo.
echo 訪問網址: http://%LOCAL_IP%:3000
echo API服務: http://%LOCAL_IP%:8000/docs
echo.
echo 預設帳號:
echo 員工: employee@example.com / password123
echo 主管: supervisor@example.com / StrongPassword123
echo.

set /p START_NOW="現在啟動系統? (y/n): "
if /i "%START_NOW%"=="y" (
    echo 啟動系統中...
    call 啟動系統.bat
) else (
    echo 稍後執行 啟動系統.bat 來啟動
)

pause