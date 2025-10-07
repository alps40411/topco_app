# 正式機環境檔案上傳與預覽路徑配置指南

本文檔旨在說明將應用程式部署到正式環境時，如何正確配置檔案上傳及圖片預覽功能所需的路徑。

## 摘要

- **開發環境路徑**: `backend/uploads/`
- **正式環境路徑**: `D:\Websites\MyReport\MyReport\upimages`

為了使功能在正式環境正常運作，需要對後端和前端的相關設定進行修改。

---

## 1. 後端修改步驟

後端主要負責處理檔案儲存的實體路徑和提供檔案的網路存取路徑。

### 1.1. 修改實體儲存路徑

此設定決定了上傳的檔案要儲存在伺服器上的哪個位置。

- **檔案**: `backend/app/core/config.py`
- **說明**: 修改 `UPLOAD_DIR` 變數，指向正式環境的絕對路徑。

**修改前**:
```python
# backend/app/core/config.py

# ...
UPLOAD_DIR: str = "uploads"
# ...
```

**修改後**:
```python
# backend/app/core/config.py

# ...
# 注意：在 Windows 路徑中，建議使用雙反斜線 `\` 或單斜線 `/` 以避免轉義字元問題。
UPLOAD_DIR: str = "D:\\Websites\\MyReport\\MyReport\\upimages"
# 或
# UPLOAD_DIR: str = "D:/Websites/MyReport/MyReport/upimages"
# ...
```

### 1.2. 修改靜態檔案掛載點

此設定將實體儲存路徑映射到一個 URL，讓前端可以透過這個 URL 存取圖片。

- **檔案**: `backend/app/main.py`
- **說明**: 更新 `app.mount()` 的 `directory` 參數，並建議將 URL 路徑從 `/uploads` 改為 `/upimages` 以保持一致性。

**修改前**:
```python
# backend/app/main.py

# ...
# --- 掛載 uploads 資料夾為靜態檔案目錄 ---
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# ...
```

**修改後**:
```python
# backend/app/main.py
from app.core.config import settings

# ...
# --- 掛載 upimages 資料夾為靜態檔案目錄 ---
app.mount("/upimages", StaticFiles(directory=settings.UPLOAD_DIR), name="upimages")
# ...
```
**注意**: 這裡我們直接從 `settings` 匯入 `UPLOAD_DIR`，這樣可以確保路徑設定的一致性，未來若有變動只需修改 `config.py` 即可。

### 1.3. 修改程式碼中寫死的 URL

在程式碼的其他地方，可能存在直接使用 `/uploads/` 路徑的情況，需要一併修改。

- **檔案**: `backend/app/api/ai.py`
- **修改前**:
  ```python
  if url_path.startswith('/uploads/'):
      file_path = settings.UPLOAD_DIR + url_path.replace('/uploads/', '/')
  ```
- **修改後**:
  ```python
  if url_path.startswith('/upimages/'):
      file_path = settings.UPLOAD_DIR + url_path.replace('/upimages/', '/')
  ```

- **檔案**: `backend/app/api/legacy_reports.py`
- **修改前**:
  ```python
  "url": f"/uploads/{safe_filename}",
  ```
- **修改後**:
  ```python
  "url": f"/upimages/{safe_filename}",
  ```

---

## 2. 前端修改步驟

前端主要負責在使用者介面上顯示圖片，它需要知道後端服務的位址和圖片的正確 URL。

### 2.1. 確認 API 服務位址

在開發環境中，前端呼叫的 API 位址可能是 `http://localhost:8000`。在正式環境中，這需要改為您正式的域名或 IP 位址。

- **檢查點**: 查找前端專案中設定 API 基礎 URL 的地方，通常在環境變數檔案（如 `.env.production`）或設定檔（如 `src/config/index.ts`）中。
- **修改範例** (`frontend/.env.production`):
  ```
  VITE_API_URL=https://your-production-domain.com
  ```

### 2.2. 更新圖片 URL 路徑

前端在顯示圖片時，會組合 API 位址和圖片路徑。請確保程式碼中使用的是新的 `/upimages/` 路徑。

- **檢查點**: 搜尋前端專案中所有 `/uploads/` 的字串。
- **修改範例** (可能在 `AttachedFilesDisplay.tsx` 或類似的元件中):
  
  **修改前**:
  ```typescript
  const imageUrl = `${import.meta.env.VITE_API_URL}/uploads/${fileName}`;
  ```

  **修改後**:
  ```typescript
  const imageUrl = `${import.meta.env.VITE_API_URL}/upimages/${fileName}`;
  ```

---

## 總結檢查清單

- [ ] `backend/app/core/config.py` 中的 `UPLOAD_DIR` 已更新為正式機絕對路徑。
- [ ] `backend/app/main.py` 中的 `app.mount` 已更新為新的 URL `/upimages` 和正確的目錄。
- [ ] 後端程式碼中所有寫死的 `/uploads/` 都已改為 `/upimages/`。
- [ ] 前端設定了正確的正式環境 API 位址。
- [ ] 前端獲取圖片的 URL 已從 `/uploads/` 改為 `/upimages/`。
- [ ] 確認正式機目錄 `D:\Websites\MyReport\MyReport\upimages` 的 IIS 使用者或應用程式集區身分具有讀寫權限。
- [ ] 重新建置並部署前端與後端應用程式。
