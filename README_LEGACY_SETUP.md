# 舊資料庫串接設定指南

## 📋 設定步驟

### 1. 設定環境變數

複製 `backend/.env.example` 到 `backend/.env` 並填入以下資料：

```env
# Legacy PostgreSQL Database settings
LEGACY_DB_HOST=你的舊資料庫主機
LEGACY_DB_PORT=5432
LEGACY_DB_USER=資料庫使用者名稱
LEGACY_DB_PASSWORD=資料庫密碼
LEGACY_DB_SERVICE=資料庫名稱
```

### 2. 建立新資料表

在舊資料庫中執行以下 SQL 檔案：

```bash
psql -h 你的主機 -U 使用者名稱 -d 資料庫名稱 -f backend/setup_legacy_tables.sql
```

這會建立三張新資料表：
- `tdr_draft` - 日報暫存表
- `tdr_ai_draft` - AI草稿記錄表  
- `tdr_draft_attachment` - 附件暫存表

### 3. 測試連接

```bash
cd backend
python test_legacy_connection.py
```

### 4. 啟動服務

```bash
# 後端
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

## 🧪 測試功能

啟動後訪問前端，點擊 **「舊DB測試」** 標籤頁：

### 基本功能測試
1. **獲取新日報編號** - 測試序列功能
2. **獲取工作計畫** - 測試現有資料查詢
3. **獲取公司列表** - 測試基礎資料
4. **獲取日報列表** - 測試複雜查詢

### 暫存功能測試
5. **保存暫存** - 測試暫存功能
6. **獲取暫存資料** - 測試暫存查詢
7. **提交日報** - 測試正式提交

## 🔄 完整資料流程

1. **取得 daily_no** → `GET /api/legacy/next-daily-no`
2. **暫存保存** → `POST /api/legacy/drafts`
3. **AI 草稿** → `POST /api/legacy/ai-drafts` 
4. **附件上傳** → `POST /api/legacy/attachments`
5. **正式提交** → `POST /api/legacy/submit`

## 📋 可用的 API 端點

### 查詢類
- `GET /api/legacy/reports?empno=XXX&doc_date=YYYYMMDD` - 日報列表
- `GET /api/legacy/reports/{daily_no}/content` - 日報內容
- `GET /api/legacy/work-plans?empno=XXX` - 工作計畫
- `GET /api/legacy/companies` - 公司列表
- `GET /api/legacy/next-daily-no` - 新日報編號

### 暫存類
- `POST /api/legacy/drafts` - 保存暫存
- `GET /api/legacy/drafts/{empno}?draft_type=TEMP` - 查詢暫存
- `DELETE /api/legacy/drafts/{draft_id}` - 刪除暫存

### AI功能
- `POST /api/legacy/ai-drafts` - 保存AI草稿
- `GET /api/legacy/ai-drafts/{empno}` - 查詢AI草稿

### 提交類
- `POST /api/legacy/submit` - 正式提交日報
- `POST /api/legacy/attachments` - 保存附件

## ⚠️ 注意事項

1. **日期格式**：所有日期都使用 `YYYYMMDD` 格式
2. **編號統一**：暫存和正式提交使用相同的 `daily_no`
3. **JSON 格式**：暫存內容以 JSON 格式儲存
4. **軟刪除**：暫存資料使用軟刪除（STATUS='D'）
5. **字串長度**：注意各欄位的字串長度限制

## 🚨 故障排除

### 連接錯誤
- 檢查 `.env` 檔案設定
- 確認資料庫服務正在運行
- 檢查防火牆和網路連線

### SQL 錯誤
- 確認已執行 `setup_legacy_tables.sql`
- 檢查資料表是否存在
- 檢查使用者權限

### API 錯誤
- 查看後端 console 輸出
- 檢查瀏覽器 Network 標籤
- 確認參數格式正確