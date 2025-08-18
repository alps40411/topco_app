@echo off 
chcp 65001 > nul
echo 啟動前端服務... 
cd frontend 
echo 前端綁定到所有網路介面 (0.0.0.0:3000)
echo API地址自動偵測當前主機
call npm run preview:production 
