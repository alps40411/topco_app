# TSC 業務日誌系統 - 完整部署指南

## 📋 目錄
1. [系統架構](#系統架構)
2. [環境需求](#環境需求)
3. [部署步驟](#部署步驟)
4. [SSO 單一登入配置](#sso-單一登入配置)
5. [環境變數設定](#環境變數設定)
6. [常見問題排查](#常見問題排查)

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────┐
│               Nginx / IIS (Reverse Proxy)            │
│          - 靜態檔案服務 (前端)                        │
│          - API 代理 (後端)                           │
│          - SSO Headers 注入                          │
└─────────────────────────────────────────────────────┘
                        ↓
┌──────────────────┐                  ┌─────────────────┐
│  前端 (React)     │                  │  後端 (FastAPI)  │
│  - Vite Build    │ ← HTTP/HTTPS → │  - Python 3.11+ │
│  - TypeScript    │                  │  - Uvicorn      │
└──────────────────┘                  └─────────────────┘
                                              ↓
                                    ┌──────────────────┐
                                    │  JPS PostgreSQL  │
                                    │  - 員工主檔       │
                                    │  - 部門資料       │
                                    └──────────────────┘
```

---

## 💻 環境需求

### 後端需求
- **Python**: 3.11 或更高版本
- **作業系統**: Windows Server 2016+ / Linux (Ubuntu 20.04+)
- **資料庫**: PostgreSQL 10+ (JPS Legacy Database)
- **記憶體**: 最少 2GB RAM (建議 4GB+)

### 前端需求
- **Node.js**: 18.x 或更高版本
- **npm**: 9.x 或更高版本
- **瀏覽器**: Chrome 90+, Firefox 88+, Edge 90+

### 網路需求
- 可存取 JPS PostgreSQL 資料庫 (預設 Port: 5432)
- 如使用 SSO,需配置 Nginx/IIS 以注入 HTTP Headers

---

## 🚀 部署步驟

### 步驟 1: 環境準備

#### 1.1 安裝 Python (Windows)
```bash
# 下載並安裝 Python 3.11+
# https://www.python.org/downloads/

# 驗證安裝
python --version
# 預期輸出: Python 3.11.x

# 安裝 pip
python -m ensurepip --upgrade
```

#### 1.2 安裝 Node.js (Windows)
```bash
# 下載並安裝 Node.js 18+
# https://nodejs.org/

# 驗證安裝
node --version
# 預期輸出: v18.x.x

npm --version
# 預期輸出: 9.x.x
```

---

### 步驟 2: 後端部署

#### 2.1 建立虛擬環境
```bash
cd C:\Users\Nick\Desktop\topco_app\backend

# 建立虛擬環境
python -m venv venv

# 啟用虛擬環境 (Windows)
.\venv\Scripts\activate

# 或使用 PowerShell
.\venv\Scripts\Activate.ps1
```

#### 2.2 安裝相依套件
```bash
# 確保在虛擬環境中
pip install --upgrade pip

# 安裝所有相依套件
pip install -r requirements.txt

# 驗證安裝
pip list
```

#### 2.3 配置環境變數

建立 `.env` 檔案於 `backend/` 目錄:

```bash
# 複製範例檔案 (如果有)
cp .env.example .env

# 或手動建立
notepad .env
```

**必要環境變數** (詳見 [環境變數設定](#環境變數設定) 章節):
```env
# JPS Legacy Database
LEGACY_DB_HOST=your-db-host
LEGACY_DB_PORT=5432
LEGACY_DB_USER=your-db-user
LEGACY_DB_PASSWORD=your-db-password
LEGACY_DB_SERVICE=jps

# JWT Security
SECRET_KEY=your-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=480

# SSO 配置
SSO_ENABLED=true
SSO_MOCK_ENABLED=false
SSO_MOCK_EMPNO=TEST001
SSO_MOCK_COCODE=A

# CORS (逗號分隔多個來源)
CORS_ORIGINS=http://localhost:5173,https://your-domain.com
```

#### 2.4 啟動後端服務

**開發環境:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**生產環境 (使用 Gunicorn):**
```bash
cd backend
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

**生產環境 (Windows Service):**
```bash
# 安裝 NSSM (Non-Sucking Service Manager)
# https://nssm.cc/download

# 建立 Windows Service
nssm install TopcoBackend "C:\Users\Nick\Desktop\topco_app\backend\venv\Scripts\python.exe"
nssm set TopcoBackend AppParameters "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
nssm set TopcoBackend AppDirectory "C:\Users\Nick\Desktop\topco_app\backend"

# 啟動服務
nssm start TopcoBackend

# 檢查狀態
nssm status TopcoBackend
```

---

### 步驟 3: 前端部署

#### 3.1 安裝相依套件
```bash
cd C:\Users\Nick\Desktop\topco_app\frontend

npm install
```

#### 3.2 配置 API 端點

編輯 `frontend/src/config/api.ts`:
```typescript
// 開發環境
const API_BASE_URL = 'http://localhost:8000'

// 生產環境
const API_BASE_URL = window.location.origin
```

#### 3.3 建置生產版本
```bash
cd frontend

# 建置
npm run build

# 輸出目錄: frontend/dist/
```

#### 3.4 部署靜態檔案

**選項 A: Nginx (推薦)**
```nginx
# /etc/nginx/sites-available/topco-app

server {
    listen 80;
    server_name your-domain.com;

    # 前端靜態檔案
    location / {
        root C:/Users/Nick/Desktop/topco_app/frontend/dist;
        try_files $uri $uri/ /index.html;

        # 快取設定
        add_header Cache-Control "public, max-age=31536000" always;
    }

    # 後端 API 代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSO Headers (根據您的 SSO 系統配置)
        # 方式 1: 從其他 header 映射
        proxy_set_header wwwuser.empno $http_x_user_empno;
        proxy_set_header wwwuser.cocode $http_x_user_cocode;

        # 方式 2: 從 Cookie 映射
        # proxy_set_header wwwuser.empno $cookie_empno;
        # proxy_set_header wwwuser.cocode $cookie_cocode;

        # 超時設定
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**選項 B: IIS (Windows)**
```xml
<!-- web.config -->
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <!-- API 代理規則 -->
        <rule name="API" stopProcessing="true">
          <match url="^api/(.*)" />
          <action type="Rewrite" url="http://localhost:8000/api/{R:1}" />
          <serverVariables>
            <!-- SSO Headers -->
            <set name="HTTP_WWWUSER_EMPNO" value="{HTTP_X_USER_EMPNO}" />
            <set name="HTTP_WWWUSER_COCODE" value="{HTTP_X_USER_COCODE}" />
          </serverVariables>
        </rule>

        <!-- SPA 路由規則 -->
        <rule name="SPA" stopProcessing="true">
          <match url=".*" />
          <conditions logicalGrouping="MatchAll">
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
            <add input="{REQUEST_FILENAME}" matchType="IsDirectory" negate="true" />
          </conditions>
          <action type="Rewrite" url="/" />
        </rule>
      </rules>
    </rewrite>

    <staticContent>
      <mimeMap fileExtension=".json" mimeType="application/json" />
    </staticContent>
  </system.webServer>
</configuration>
```

---

## 🔐 SSO 單一登入配置

### SSO 工作原理

1. **使用者訪問應用** → Nginx/IIS 添加 SSO Headers
2. **前端自動呼叫** `/api/auth/sso` 端點
3. **後端讀取 Headers** 並驗證用戶 (`wwwuser.empno`, `wwwuser.cocode`)
4. **查詢 JPS 資料庫** 確認員工資料
5. **生成 JWT Token** 並返回給前端
6. **後續請求使用 JWT** (標準 Bearer Token 認證)

### 關鍵配置點

#### 1. 後端 SSO 設定 (`backend/app/core/config.py`)
```python
# 生產環境必須關閉 Mock
SSO_ENABLED = True
SSO_MOCK_ENABLED = False  # ⚠️ 生產環境必須為 False

# 開發環境可啟用 Mock
SSO_MOCK_ENABLED = True
SSO_MOCK_EMPNO = "05489"
SSO_MOCK_COCODE = "A"
```

#### 2. Nginx Headers 注入
```nginx
# 確保 Nginx 正確傳遞 SSO Headers
proxy_set_header wwwuser.empno $http_x_user_empno;
proxy_set_header wwwuser.cocode $http_x_user_cocode;
```

#### 3. 前端自動登入
前端會在載入時自動嘗試 SSO 登入 (`frontend/src/components/LoginPage.tsx:19-56`):
```typescript
React.useEffect(() => {
  const checkSSO = async () => {
    const response = await fetch("/api/auth/sso", { method: "POST" });
    if (response.ok) {
      // 自動登入成功
    } else {
      // 顯示手動登入表單
    }
  };
  checkSSO();
}, []);
```

### SSO 故障排查

**問題: 正式機無法 SSO 登入**

**檢查清單:**
1. ✅ 確認 `SSO_MOCK_ENABLED=false` (生產環境)
2. ✅ 檢查 Nginx/IIS 是否正確傳遞 `wwwuser.empno` header
3. ✅ 驗證 JPS 資料庫連線正常
4. ✅ 查看後端日誌確認 headers 是否收到

**測試 SSO Headers:**
```bash
# 手動測試 SSO 端點
curl -X POST http://your-domain.com/api/auth/sso \
  -H "wwwuser.empno: 05489" \
  -H "wwwuser.cocode: A"

# 預期回應: JWT Token
```

**查看後端日誌:**
```bash
# 查找 SSO 相關日誌
tail -f backend/logs/app.log | grep "SSO"

# Windows
Get-Content backend\logs\app.log -Tail 50 -Wait | Select-String "SSO"
```

---

## ⚙️ 環境變數設定

### 完整 `.env` 範例

```env
# ========================================
# JPS Legacy PostgreSQL Database
# ========================================
LEGACY_DB_HOST=10.100.1.10
LEGACY_DB_PORT=5432
LEGACY_DB_USER=jps_user
LEGACY_DB_PASSWORD=your-secure-password
LEGACY_DB_SERVICE=jps
LEGACY_DB_URL=edb://jps_user:your-secure-password@10.100.1.10:5432/jps

# ========================================
# JWT Security Settings
# ========================================
SECRET_KEY=your-secret-key-must-be-at-least-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=480

# ========================================
# SSO Configuration
# ========================================
SSO_ENABLED=true

# ⚠️ 生產環境必須設為 false
SSO_MOCK_ENABLED=false

# 開發環境 Mock 設定 (僅在 SSO_MOCK_ENABLED=true 時有效)
SSO_MOCK_EMPNO=05489
SSO_MOCK_COCODE=A

# ========================================
# CORS Settings
# ========================================
# 多個來源用逗號分隔
CORS_ORIGINS=http://localhost:5173,https://your-domain.com,https://app.your-company.com

# ========================================
# File Upload Settings
# ========================================
UPLOAD_DIR=uploads
MAX_FILE_SIZE=10485760

# ========================================
# Azure Services (Optional)
# ========================================
AZURE_OPENAI_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

AZURE_DOC_INTELLIGENCE_KEY=your-doc-intelligence-key
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://your-instance.cognitiveservices.azure.com/

# ========================================
# Logging Settings
# ========================================
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 環境變數優先順序
1. 系統環境變數 (最高優先權)
2. `.env` 檔案
3. `config.py` 預設值 (最低優先權)

---

## 🔧 常見問題排查

### 問題 1: 無法連接到 JPS 資料庫

**症狀:**
- 後端啟動失敗
- 錯誤訊息: "Could not connect to PostgreSQL"

**解決方案:**
```bash
# 1. 檢查資料庫連線
telnet 10.100.1.10 5432

# 2. 驗證帳號密碼
psql -h 10.100.1.10 -p 5432 -U jps_user -d jps

# 3. 檢查防火牆規則
netsh advfirewall firewall show rule name=all | findstr 5432

# 4. 確認 .env 設定
cat backend/.env | grep LEGACY_DB
```

---

### 問題 2: SSO 登入失敗

**症狀:**
- 自動登入失敗，顯示手動登入表單
- 錯誤: "SSO authentication failed: missing employee ID"

**解決方案:**

**Step 1: 檢查 SSO Mock 設定**
```bash
# backend/.env
SSO_MOCK_ENABLED=false  # 生產環境必須為 false
```

**Step 2: 檢查 Nginx Headers**
```bash
# 在後端加入除錯日誌
# backend/app/core/sso.py 已有詳細 print 語句

# 重啟後端並查看日誌
tail -f backend/logs/app.log
```

**Step 3: 手動測試 Headers**
```bash
# 測試 SSO 端點
curl -X POST http://your-domain.com/api/auth/sso \
  -H "wwwuser.empno: 05489" \
  -H "wwwuser.cocode: A" \
  -v

# 應該看到 200 OK 和 JWT token
```

**Step 4: 檢查前端請求**
```javascript
// 打開瀏覽器 DevTools > Network
// 查看 /api/auth/sso 請求的 Headers
// 確認是否包含 wwwuser.empno 和 wwwuser.cocode
```

---

### 問題 3: CORS 錯誤

**症狀:**
- 前端無法呼叫後端 API
- 錯誤: "CORS policy: No 'Access-Control-Allow-Origin' header"

**解決方案:**
```bash
# backend/.env
CORS_ORIGINS=http://localhost:5173,https://your-domain.com

# 重啟後端服務
nssm restart TopcoBackend
```

---

### 問題 4: 前端無法載入

**症狀:**
- 訪問網站顯示 404
- Nginx 錯誤: "File not found"

**解決方案:**
```bash
# 1. 確認前端已建置
cd frontend
npm run build

# 2. 檢查 dist 目錄
ls -la dist/

# 3. 確認 Nginx 配置路徑正確
cat /etc/nginx/sites-available/topco-app | grep root

# 4. 重新載入 Nginx
sudo nginx -t
sudo nginx -s reload
```

---

### 問題 5: JWT Token 過期

**症狀:**
- 使用者需要頻繁重新登入
- 錯誤: "Token has expired"

**解決方案:**
```bash
# backend/.env
# 調整 token 過期時間 (單位: 分鐘)
ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8 小時

# 重啟後端
nssm restart TopcoBackend
```

---

## 📊 健康檢查

### 後端健康檢查
```bash
# 檢查後端服務狀態
curl http://localhost:8000/

# 預期回應: {"message": "Welcome to TSC API"}
```

### 資料庫連線檢查
```bash
# 使用 Python 測試
cd backend
python -c "from app.core.legacy_database import get_legacy_db; next(get_legacy_db()); print('DB OK')"
```

### 完整測試流程
```bash
# 1. 測試 SSO 登入
curl -X POST http://localhost:8000/api/auth/sso \
  -H "wwwuser.empno: 05489" \
  -H "wwwuser.cocode: A"

# 2. 使用返回的 token 測試 API
TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
curl http://localhost:8000/api/records/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🚦 部署檢查清單

### 生產環境部署前

- [ ] 已建置前端生產版本 (`npm run build`)
- [ ] 已安裝後端相依套件 (`pip install -r requirements.txt`)
- [ ] 已建立 `.env` 檔案並填入所有必要環境變數
- [ ] `SSO_MOCK_ENABLED=false` (生產環境)
- [ ] `CORS_ORIGINS` 已設定為正式網域
- [ ] Nginx/IIS 已配置 SSO Headers
- [ ] 資料庫連線測試通過
- [ ] 後端服務已註冊為 Windows Service
- [ ] 已設定適當的日誌目錄和權限
- [ ] 已測試 SSO 登入流程
- [ ] 已測試手動登入流程 (後備方案)

### 上線後驗證

- [ ] 前端頁面可正常載入
- [ ] SSO 自動登入功能正常
- [ ] 手動登入功能正常
- [ ] API 呼叫成功 (無 CORS 錯誤)
- [ ] JWT Token 正常運作
- [ ] 日誌正常記錄
- [ ] 效能監控正常

---

## 📞 技術支援

### 日誌位置
- **後端日誌**: `backend/logs/app.log`
- **Nginx 日誌**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **IIS 日誌**: `C:\inetpub\logs\LogFiles\`

### 除錯模式

**啟用詳細日誌:**
```bash
# backend/.env
LOG_LEVEL=DEBUG

# 或直接在啟動時設定
uvicorn app.main:app --log-level debug
```

**查看即時日誌:**
```bash
# Linux
tail -f backend/logs/app.log

# Windows PowerShell
Get-Content backend\logs\app.log -Tail 50 -Wait
```

---

## 📝 版本記錄

- **v1.0** (2025-01-XX): 初始版本
  - 實作 SSO 單一登入
  - 整合 JPS 資料庫認證
  - 支援手動登入後備方案

---

## 🔗 相關文件

- [SSO_SETUP.md](./SSO_SETUP.md) - SSO 功能詳細說明
- [README.md](./README.md) - 專案概述
- [API 文件](http://localhost:8000/docs) - FastAPI 自動生成的 API 文件

---

**文件版本**: 1.0
**最後更新**: 2025-01-XX
**維護者**: TSC 技術團隊
