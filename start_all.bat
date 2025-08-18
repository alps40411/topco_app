@echo off 
chcp 65001 > nul
echo ================================ 
echo     TSC 業務日誌系統 
echo ================================ 
echo. 
echo 後端服務: http://0.0.0.0:8000 (支援所有網路介面)
echo 前端服務: http://0.0.0.0:3000 (支援所有網路介面)
echo. 
echo 可透過以下地址訪問: 
echo   本機: http://localhost:3000 
echo   內網: http://192.168.56.1:3000 
echo   公司: http://10.129.130.120:3000 
echo. 
start "後端服務" start_backend.bat 
timeout /t 3 /nobreak > nul 
start "前端服務" start_frontend.bat 
echo 服務啟動中，請稍候.. 
timeout /t 5 /nobreak > nul 
start "" "http://localhost:3000" 
