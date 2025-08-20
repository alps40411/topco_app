@echo off
chcp 65001 >nul
echo ================================
echo     測試部署腳本
echo ================================
echo.

echo 檢查必要文件...
if not exist "backend\requirements.txt" (
    echo ❌ 缺少 backend\requirements.txt
    pause
    exit /b 1
)

if not exist "backend\start_production.py" (
    echo ❌ 缺少 backend\start_production.py
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ❌ 缺少 frontend\package.json
    pause
    exit /b 1
)

if not exist "frontend\vite.config.production.ts" (
    echo ❌ 缺少 frontend\vite.config.production.ts
    pause
    exit /b 1
)

echo ✅ 所有必要文件都存在
echo.

echo 檢查 Python 環境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安裝或不在 PATH 中
    pause
    exit /b 1
)
echo ✅ Python 環境正常
echo.

echo 檢查 Node.js 環境...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安裝或不在 PATH 中
    pause
    exit /b 1
)
echo ✅ Node.js 環境正常
echo.

echo 檢查 npm 環境...
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm 未安裝或不在 PATH 中
    pause
    exit /b 1
)
echo ✅ npm 環境正常
echo.

echo ================================
echo     環境檢查完成！
echo ================================
echo.
echo 現在可以運行 一鍵部署.bat 了
pause
