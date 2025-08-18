@echo off 
chcp 65001 > nul
echo 啟動後端服務... 
cd backend 
call venv\Scripts\activate.bat 
echo 後端綁定到所有網路介面 (0.0.0.0:8000)
echo CORS設定為最寬鬆模式
python start_production.py 
