# SSO 單一登入整合說明

## 🎯 概述

本專案已成功整合 SSO (Single Sign-On) 單一登入功能，支援從 HTTP Headers 自動認證用戶。

## 🏗️ 架構說明

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Nginx/Proxy   │────│  FastAPI Backend │────│   JPS Database  │
│  (Add Headers)  │    │  (SSO Middleware)│    │  (User Lookup)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 認證流程
1. 用戶通過 Nginx/Proxy 訪問應用
2. Proxy 添加 SSO headers (`wwwuser.empno`, `wwwuser.cocode`)
3. 前端自動調用 `/api/auth/sso` 端點
4. 後端讀取 headers，查詢 JPS 資料庫驗證用戶
5. 生成 JWT token 返回前端
6. 後續 API 調用使用 JWT (保持現有架構)

## 📋 功能特性

### ✅ 已實現功能
- **雙重認證支援**: JWT Token + SSO Headers
- **開發環境 Mock**: 自動模擬 SSO headers
- **向後兼容**: 保持原有登入方式
- **優雅降級**: SSO 失敗時顯示手動登入
- **安全設計**: 只信任指定來源的 headers

### 🔄 認證優先順序
1. JWT Token (現有 API 調用)
2. SSO Headers (新增支援)
3. 開發環境 Mock (測試用)

## 🛠️ 部署配置

### 1. 後端環境變數 (.env)
```bash
# SSO 配置
SSO_ENABLED=true
SSO_MOCK_ENABLED=true  # 生產環境設為 false
SSO_MOCK_EMPNO=TEST001
SSO_MOCK_COCODE=A

# JWT 配置
ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8小時
```

### 2. Nginx/Proxy 配置
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端靜態檔案
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 後端 API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSO Headers - 根據您的 SSO 系統配置
        proxy_set_header wwwuser.empno $http_x_user_empno;  # 示例
        proxy_set_header wwwuser.cocode $http_x_user_cocode; # 示例

        # 或者使用固定值進行測試
        # proxy_set_header wwwuser.empno "TEST001";
        # proxy_set_header wwwuser.cocode "A";
    }
}
```

### 3. 生產環境安全設定
```python
# 在 config.py 中
SSO_ENABLED = True
SSO_MOCK_ENABLED = False  # 關閉開發模式 Mock
TRUSTED_SSO_SOURCES = ["10.0.0.0/8", "192.168.0.0/16"]  # 信任的來源IP
```

## 🧪 測試指南

### 自動測試腳本
```bash
cd /path/to/project
python test_sso.py
```

### 手動測試步驟

1. **測試 SSO Headers 認證**
   ```bash
   curl -X POST http://localhost:8000/api/auth/sso \
        -H "wwwuser.empno: TEST001" \
        -H "wwwuser.cocode: A"
   ```

2. **測試傳統登入 (向後兼容)**
   ```bash
   curl -X POST http://localhost:8000/api/auth/token \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=TEST001&password=dummy"
   ```

3. **測試前端自動 SSO**
   - 訪問 http://localhost:3000
   - 應該自動嘗試 SSO 登入
   - 失敗時顯示登入表單

## 🚀 部署步驟

### 開發環境
1. 啟動後端服務
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

2. 啟動前端服務
   ```bash
   cd frontend
   npm run dev
   ```

3. 測試 SSO 功能
   ```bash
   python test_sso.py
   ```

### 生產環境
1. **構建前端**
   ```bash
   cd frontend
   npm run build
   ```

2. **配置環境變數**
   ```bash
   # 關閉開發模式 Mock
   echo "SSO_MOCK_ENABLED=false" >> backend/.env
   ```

3. **配置 Nginx/Proxy**
   - 設定正確的 SSO headers 映射
   - 確保 headers 來源可信

4. **啟動服務**
   ```bash
   # 後端
   cd backend
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

   # Nginx
   sudo nginx -s reload
   ```

## 📝 API 端點

| 端點 | 方法 | 用途 | 狀態 |
|------|------|------|------|
| `/api/auth/sso` | POST | SSO 認證 | ✅ 新增 |
| `/api/auth/token` | POST | 傳統登入 | ✅ 保持 |
| `/api/records/*` | GET/POST | 業務 API | ✅ 支援雙重認證 |

## 🔍 故障排除

### 常見問題

**1. SSO 登入失敗**
- 檢查 headers 是否正確傳遞
- 確認 JPS 資料庫連接正常
- 查看後端日誌: `docker logs backend`

**2. 開發環境無法登入**
- 確認 `SSO_MOCK_ENABLED=true`
- 檢查 Mock empno 是否在 JPS 中存在

**3. 生產環境 Mock 洩漏**
- 確認 `SSO_MOCK_ENABLED=false`
- 重新啟動後端服務

### 日誌檢查
```bash
# 後端 SSO 相關日誌
grep "SSO\|Authentication" backend/logs/app.log

# Nginx access 日誌
tail -f /var/log/nginx/access.log | grep "wwwuser"
```

## 🔐 安全考慮

1. **Headers 驗證**: 只接受來自可信 IP 的 headers
2. **Token 過期**: 設定合理的 JWT 過期時間
3. **日誌記錄**: 記錄所有認證嘗試
4. **錯誤處理**: 不洩露敏感信息

## 📞 支援聯絡

如有問題或需要協助，請聯絡：
- 技術支援: [您的聯絡方式]
- 部署指導: [部署團隊聯絡方式]