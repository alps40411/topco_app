# 正式機環境檔案上傳與預覽路徑配置指南

本文檔說明將應用程式部署到正式環境時,如何正確配置檔案上傳及圖片預覽功能所需的路徑。

## 摘要

- **開發環境路徑**: `backend/uploads/`
- **正式環境路徑**: `D:\Websites\MyReport\MyReport\upimages`
- **正式環境 URL 前綴**: `/MyReportAI` (如果部署在子路徑下)

系統已經進行架構改進,使用環境變數和工具函數來自動處理開發/正式環境的差異。

---

## 架構說明

### 當前架構的改進

1. **環境變數驅動**: 使用 `.env` 檔案統一管理所有環境相關設定
2. **自動路徑處理**: 前端使用 `getFullFileUrl()` 工具函數自動判斷環境
3. **URL 前綴支援**: 新增 `STATIC_URL_PREFIX` 支援部署在子路徑 (如 `/MyReportAI`)

---

## 1. 後端配置步驟

### 1.1. 環境變數設定 (`.env` 檔案)

後端的所有路徑設定都透過 `.env` 檔案管理。

**檔案位置**: `backend/.env`

**必要設定**:
```bash
# 檔案上傳設定
UPLOAD_DIR=D:\Websites\MyReport\MyReport\upimages  # 正式機絕對路徑
STATIC_URL_PREFIX=/MyReportAI                       # URL 前綴 (如果部署在子路徑)
MAX_FILE_SIZE=10485760                              # 10MB (可選)
```

**說明**:
- `UPLOAD_DIR`: 檔案實際儲存的物理路徑
  - 開發環境: `uploads` (相對路徑)
  - 正式環境: `D:\Websites\MyReport\MyReport\upimages` (絕對路徑)
  - ⚠️ Windows 路徑可使用單斜線 `/` 或雙反斜線 `\\`

- `STATIC_URL_PREFIX`: URL 路徑前綴
  - 如果應用部署在 `https://domain.com/MyReportAI/`,則設為 `/MyReportAI`
  - 如果部署在根路徑 `https://domain.com/`,則設為空字串 ``
  - 此設定會影響檔案 URL 的生成,例如: `/MyReportAI/uploads/202510/file.png`

### 1.2. 檔案掛載點 (`backend/app/main.py`)

**當前設定** (無需修改):
```python
# backend/app/main.py

# 掛載 uploads 資料夾為靜態檔案目錄
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

**注意**:
- 這個掛載點目前寫死為 `"uploads"`,在正式機需要改為 `settings.UPLOAD_DIR`
- ⚠️ **建議修改**: 改為 `StaticFiles(directory=settings.UPLOAD_DIR)` 以保持一致性

**建議修改**:
```python
# backend/app/main.py
from app.core.config import settings

# 掛載 uploads 資料夾為靜態檔案目錄
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
```

### 1.3. 檢查程式碼中的路徑處理

**已處理的檔案**:
- ✅ `backend/app/services/record_service.py`: 使用 `settings.STATIC_URL_PREFIX` 生成檔案 URL
- ✅ `backend/app/services/azure_ai_service.py`: 使用 `settings.STATIC_URL_PREFIX` 處理路徑

**需要注意的檔案**:
- ⚠️ `backend/app/api/ai.py`: 第 94-96 行仍使用 `/uploads/` 路徑
  ```python
  # 目前的程式碼
  if url_path.startswith('/uploads/'):
      file_path = settings.UPLOAD_DIR + url_path.replace('/uploads/', '/')
  ```

  **建議**: 這段程式碼可能需要更新以支援不同的 URL 前綴

---

## 2. 前端配置步驟

### 2.1. 自動環境偵測

**前端已經實現自動環境偵測** (`frontend/src/utils/urlUtils.ts`):

```typescript
export const getFullFileUrl = (url: string): string => {
  // 如果 URL 已經是完整的，直接返回
  if (url.startsWith("http")) {
    return url;
  }

  // 檢查是否為開發環境
  const isDevelopment =
    window.location.port === "5173" ||
    window.location.port === "5174" ||
    window.location.port === "3000" ||
    window.location.hostname === "localhost";

  // 建立後端 URL
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;

  // 開發環境: http://localhost:8000
  // 正式環境: 與前端相同的 domain
  const backendUrl = isDevelopment
    ? `${protocol}//${hostname}:8000`
    : `${protocol}//${hostname}`;

  const fullUrl = url.startsWith("/")
    ? `${backendUrl}${url}`
    : `${backendUrl}/${url}`;

  return fullUrl;
};
```

**優點**:
- ✅ 無需修改前端程式碼
- ✅ 自動判斷開發/正式環境
- ✅ 自動組合完整 URL

**使用範例**:
```typescript
// 後端返回: /uploads/202510/image.png
// 開發環境自動轉換為: http://localhost:8000/uploads/202510/image.png
// 正式環境自動轉換為: https://your-domain.com/uploads/202510/image.png

const fileUrl = getFullFileUrl(file.url);
```

### 2.2. URL 前綴處理

如果正式環境部署在子路徑 (例如 `/MyReportAI/`),前端會自動處理:

**情境 1: 部署在根路徑**
- 前端位置: `https://domain.com/`
- 後端 API: `https://domain.com/api/`
- 檔案 URL: `https://domain.com/uploads/202510/file.png`
- `.env` 設定: `STATIC_URL_PREFIX=`

**情境 2: 部署在子路徑**
- 前端位置: `https://domain.com/MyReportAI/`
- 後端 API: `https://domain.com/MyReportAI/api/`
- 檔案 URL: `https://domain.com/MyReportAI/uploads/202510/file.png`
- `.env` 設定: `STATIC_URL_PREFIX=/MyReportAI`

---

## 3. IIS 部署設定

### 3.1. 目錄權限

確保 IIS 應用程式集區身分對上傳目錄有讀寫權限:

```
目錄: D:\Websites\MyReport\MyReport\upimages
權限: IIS AppPool\YourAppPoolName (修改)
```

### 3.2. URL Rewrite (如果使用子路徑)

如果部署在子路徑 (例如 `/MyReportAI/`),需要設定 IIS URL Rewrite:

**web.config 範例**:
```xml
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <!-- 靜態檔案直接提供 -->
        <rule name="Uploads" stopProcessing="true">
          <match url="^MyReportAI/uploads/(.*)$" />
          <action type="Rewrite" url="upimages/{R:1}" />
        </rule>

        <!-- API 請求轉發到後端 -->
        <rule name="API" stopProcessing="true">
          <match url="^MyReportAI/api/(.*)$" />
          <action type="Rewrite" url="http://localhost:8000/api/{R:1}" />
        </rule>

        <!-- 前端 SPA 路由 -->
        <rule name="SPA" stopProcessing="true">
          <match url="^MyReportAI/(.*)$" />
          <conditions>
            <add input="{REQUEST_FILENAME}" matchType="IsFile" negate="true" />
          </conditions>
          <action type="Rewrite" url="MyReportAI/index.html" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
```

---

## 4. 部署檢查清單

### 後端檢查

- [ ] `backend/.env` 中 `UPLOAD_DIR` 已設為正式機絕對路徑
- [ ] `backend/.env` 中 `STATIC_URL_PREFIX` 已正確設定 (如需要)
- [ ] `backend/app/main.py` 的 `app.mount()` 已改用 `settings.UPLOAD_DIR`
- [ ] 後端程式碼中使用 `/uploads/` 的地方已檢查並更新
- [ ] 正式機目錄 `D:\Websites\MyReport\MyReport\upimages` 已建立
- [ ] IIS 應用程式集區對上傳目錄有讀寫權限

### 前端檢查

- [ ] 前端使用 `getFullFileUrl()` 處理所有檔案 URL
- [ ] 前端建置時無硬編碼的 API 位址
- [ ] 如部署在子路徑,IIS URL Rewrite 規則已設定

### 測試驗證

- [ ] 可正常上傳檔案
- [ ] 上傳的檔案儲存在正確的物理路徑
- [ ] 可正常預覽上傳的圖片/檔案
- [ ] AI 功能可正常讀取檔案 (如有使用)
- [ ] 跨日期的檔案都能正常存取

---

## 5. 常見問題排查

### 問題 1: 檔案上傳成功但無法預覽

**可能原因**:
- 物理路徑與 URL 掛載點不一致
- IIS 目錄權限不足
- URL 前綴設定錯誤

**檢查步驟**:
1. 確認檔案已實際儲存在 `UPLOAD_DIR` 指定的路徑
2. 檢查 IIS 應用程式集區對該目錄的權限
3. 檢查 `STATIC_URL_PREFIX` 設定是否與 IIS URL Rewrite 一致

### 問題 2: AI 功能無法讀取檔案

**可能原因**:
- Azure AI Service 中的路徑轉換邏輯錯誤
- `STATIC_URL_PREFIX` 未正確處理

**檢查**:
查看 `backend/app/services/azure_ai_service.py` 的路徑處理邏輯

### 問題 3: 開發環境正常,正式環境失敗

**可能原因**:
- `.env` 檔案未正確部署到正式機
- 環境變數未正確載入

**檢查**:
1. 確認正式機有 `backend/.env` 檔案
2. 檢查後端啟動日誌,確認環境變數已載入

---

## 6. 升級建議

### 建議修改 1: main.py 使用動態路徑

```python
# backend/app/main.py
from app.core.config import settings

# 將寫死的 "uploads" 改為使用設定
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
```

### 建議修改 2: 統一 URL 前綴處理

考慮在所有檔案路徑處理中統一使用 `STATIC_URL_PREFIX`,避免硬編碼 `/uploads/`。

**需要檢查的檔案**:
- `backend/app/api/ai.py`
- 其他可能有檔案路徑處理的 API

---

## 附錄: 範例設定

### 開發環境 `.env`
```bash
UPLOAD_DIR=uploads
STATIC_URL_PREFIX=
```

### 正式環境 `.env` (根路徑部署)
```bash
UPLOAD_DIR=D:\Websites\MyReport\MyReport\upimages
STATIC_URL_PREFIX=
```

### 正式環境 `.env` (子路徑部署)
```bash
UPLOAD_DIR=D:\Websites\MyReport\MyReport\upimages
STATIC_URL_PREFIX=/MyReportAI
```
