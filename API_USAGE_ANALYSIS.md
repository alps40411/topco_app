# API 使用分析與重構計劃

## 執行摘要

本文檔分析了前端實際使用的所有 API endpoints，並追溯到後端實現,以識別棄用、未使用的代碼和結構性問題。

**分析日期**: 2025-10-08
**分析範圍**: 前端所有元件 → 後端 API routes → Services 層

---

## 📊 前端 API 使用統計

### 核心使用的前端元件
1. **App.tsx** - 主應用程式
2. **DailyReportTab.tsx** - 日報編輯頁面
3. **DataInputTab.tsx** - 隨筆記錄頁面
4. **EmployeeDetailTab.tsx** - 員工日報詳情頁面
5. **EmployeeListTab.tsx** - 日報首頁列表
6. **ChatInterface.tsx** - 留言互動介面
7. **DateSelector.tsx** - 日期選擇器
8. **AuthContext.tsx** - 認證上下文
9. **LoginPage.tsx** - 登入頁面

---

## 🔍 活躍 API Endpoints 清單

### 1️⃣ **認證相關 API** (AuthContext, LoginPage)

#### ✅ `/api/auth/token` (POST)
- **用途**: 傳統登入（使用員工編號）
- **前端**: LoginPage.tsx:68
- **後端**: backend/app/api/auth.py
- **狀態**: **活躍使用中**

#### ✅ `/api/auth/sso` (POST)
- **用途**: SSO 單一登入
- **前端**: LoginPage.tsx:34, 97
- **後端**: backend/app/api/auth.py
- **狀態**: **活躍使用中**

#### ✅ `/api/users/profile` (GET)
- **用途**: 驗證 token 並獲取用戶資料
- **前端**: AuthContext.tsx:45
- **後端**: backend/app/api/users.py
- **狀態**: **活躍使用中**

---

### 2️⃣ **記錄管理 API** (DataInputTab, DailyReportTab)

#### ✅ `/api/records/consolidated/today` (GET)
- **用途**: 獲取當日彙整記錄（支援 doc_date 參數）
- **前端**:
  - DailyReportTab.tsx:167, 228
  - DataInputTab.tsx:89, 118
- **後端**: backend/app/api/legacy_reports.py (records_router)
- **狀態**: **活躍使用中**

#### ✅ `/api/records/writing-status` (GET)
- **用途**: 檢查特定日期是否可填寫
- **前端**:
  - App.tsx:265
  - DailyReportTab.tsx:189
  - DataInputTab.tsx:70
  - EmployeeListTab.tsx:84
- **後端**: backend/app/api/legacy_reports.py (records_router)
- **狀態**: **活躍使用中** ⚠️ **API 過度呼叫問題**

#### ✅ `/api/records/upload` (POST)
- **用途**: 上傳檔案（附件）
- **前端**:
  - DailyReportTab.tsx:642, 751
- **後端**: backend/app/api/legacy_reports.py (records_router)
- **狀態**: **活躍使用中**

#### ✅ `/api/records/delete/{year_month}/{filename}` (DELETE)
- **用途**: 刪除已上傳的檔案
- **前端**:
  - DailyReportTab.tsx:457, 543, 813
  - DataInputTab.tsx:357
- **後端**: backend/app/api/legacy_reports.py (records_router)
- **狀態**: **活躍使用中**

---

### 3️⃣ **草稿管理 API** (DataInputTab, DailyReportTab)

#### ✅ `/api/drafts` (POST)
- **用途**: 建立或更新草稿
- **前端**:
  - DailyReportTab.tsx:1022
  - DataInputTab.tsx:261
- **後端**: backend/app/api/drafts.py
- **狀態**: **活躍使用中**

#### ✅ `/api/drafts/{empno}` (GET)
- **用途**: 獲取特定員工的草稿列表
- **前端**:
  - DailyReportTab.tsx:972
  - DataInputTab.tsx:212
- **後端**: backend/app/api/drafts.py
- **狀態**: **活躍使用中**

#### ✅ `/api/drafts/by-daily-planno-sopno/{daily_no}/{planno}/{sopno}` (PUT)
- **用途**: 更新特定草稿（使用 daily_no + planno + sopno 識別）
- **前端**: DailyReportTab.tsx:514
- **後端**: backend/app/api/drafts.py
- **狀態**: **活躍使用中**

---

### 4️⃣ **專案與工作項目 API**

#### ✅ `/api/projects/` (GET)
- **用途**: 獲取專案列表
- **前端**: DailyReportTab.tsx:204
- **後端**: backend/app/api/legacy_reports.py (projects_router)
- **狀態**: **活躍使用中**

---

### 5️⃣ **AI 相關 API** (DailyReportTab, ChatInterface)

#### ✅ `/api/ai/enhance_one/{daily_no}/{planno}/{sopno}` (POST)
- **用途**: 對單一專案進行 AI 潤飾
- **前端**:
  - DailyReportTab.tsx:297, 363
- **後端**: backend/app/api/ai.py
- **狀態**: **活躍使用中**

#### ✅ `/api/supervisor/reports/{report_id}/ai-suggestions` (POST)
- **用途**: 生成主管審閱的 AI 建議
- **前端**: ChatInterface.tsx:395
- **後端**: backend/app/api/supervisor.py
- **狀態**: **活躍使用中**

---

### 6️⃣ **主管審閱 API** (EmployeeDetailTab, EmployeeListTab, ChatInterface)

#### ✅ `/api/supervisor/has-subordinates` (GET)
- **用途**: 檢查當前用戶是否為主管
- **前端**: AuthContext.tsx:74
- **後端**: backend/app/api/supervisor.py
- **狀態**: **活躍使用中**

#### ✅ `/api/supervisor/daily-homepage` (GET)
- **用途**: 獲取日報首頁列表
- **前端**: EmployeeListTab.tsx:115
- **後端**: backend/app/api/supervisor.py
- **狀態**: **活躍使用中**

#### ✅ `/api/supervisor/reports/{report_id}` (GET)
- **用途**: 獲取特定日報詳情
- **前端**:
  - App.tsx:357
  - EmployeeDetailTab.tsx:47
- **後端**: backend/app/api/supervisor.py
- **狀態**: **活躍使用中**

#### ✅ `/api/supervisor/reports/{report_id}/approvals` (GET)
- **用途**: 獲取日報的審核狀態
- **前端**: EmployeeDetailTab.tsx:61
- **後端**: backend/app/api/supervisor.py
- **狀態**: **活躍使用中**

---

### 7️⃣ **留言與審閱 API** (ChatInterface)

#### ✅ `/api/reports/{report_id}/comments` (GET)
- **用途**: 獲取日報的所有留言
- **前端**: ChatInterface.tsx:219
- **後端**: backend/app/api/reports.py
- **狀態**: **活躍使用中**

#### ✅ `/api/reviews/submit` (POST)
- **用途**: 提交主管審閱或一般回覆（統一端點）
- **前端**:
  - ChatInterface.tsx:271, 314
- **後端**: backend/app/api/reviews.py
- **狀態**: **活躍使用中**

#### ✅ `/api/reports/acknowledge` (POST)
- **用途**: 確認已讀（用於 status=P 的場景）
- **前端**: ChatInterface.tsx:362
- **後端**: backend/app/api/reports.py (實際端點在 reviews.py)
- **狀態**: **活躍使用中**

#### ✅ `/api/reports/{report_id}` (DELETE)
- **用途**: 刪除日報
- **前端**: EmployeeListTab.tsx:174
- **後端**: backend/app/api/reports.py
- **狀態**: **活躍使用中**

---

### 8️⃣ **Legacy 舊系統整合 API**

#### ✅ `/api/legacy/next-daily-no` (GET)
- **用途**: 獲取下一個 daily_no
- **前端**:
  - DailyReportTab.tsx:987
  - DataInputTab.tsx:228
- **後端**: backend/app/api/legacy_reports.py
- **狀態**: **活躍使用中**

#### ✅ `/api/legacy/upload-daily-report` (POST)
- **用途**: 上傳最終日報到舊系統
- **前端**: DailyReportTab.tsx:598
- **後端**: backend/app/api/legacy_reports.py
- **狀態**: **活躍使用中**

#### ✅ `/api/legacy/daily-date-range` (GET)
- **用途**: 獲取可用日期範圍
- **前端**: DateSelector.tsx:83
- **後端**: backend/app/api/legacy_reports.py
- **狀態**: **活躍使用中**

---

## ⚠️ 發現的問題

### 問題 1: 重複 API 呼叫
**描述**: `/api/records/writing-status` 在多個元件中被重複呼叫
- App.tsx
- DailyReportTab.tsx
- DataInputTab.tsx
- EmployeeListTab.tsx

**影響**: 性能問題，增加伺服器負載

**建議**:
1. 在 AuthContext 中統一管理 writing status
2. 使用全域狀態管理（如 Context 或 Redux）
3. 實作快取機制

---

### 問題 2: API 路徑結構不一致
**描述**: API 路徑命名沒有統一規範

**範例**:
- ✅ RESTful: `/api/reports/{id}` (好)
- ❌ 非 RESTful: `/api/drafts/by-daily-planno-sopno/{daily_no}/{planno}/{sopno}` (過長)
- ❌ 混合風格: `/api/supervisor/daily-homepage` (不符合 REST 慣例)

**建議**:
```
目前: /api/drafts/by-daily-planno-sopno/{daily_no}/{planno}/{sopno}
建議: /api/drafts/{daily_no}?planno={planno}&sopno={sopno}

目前: /api/supervisor/daily-homepage?date={date}
建議: /api/supervisor/reports/daily?date={date}
```

---

### 問題 3: Service 層架構不清晰
**檔案列表**:
- `legacy_service_v2.py` - 為什麼有 v2？v1 在哪裡？
- `review_service.py` - 審閱服務
- `wfinbox_service.py` - 不明確的用途
- `corp_employee_service.py` - 員工服務
- `daily_date_service.py` - 日期服務
- `ai_suggestion_service.py` - AI 建議服務
- `azure_ai_service.py` - Azure AI 服務
- `user_service.py` - 用戶服務

**問題**:
1. 命名不一致 (有些加 service，有些沒有)
2. 職責不清（legacy_service_v2 似乎做了很多事情）
3. 缺乏文檔說明每個 service 的職責

---

### 問題 4: 缺少 API 文檔
**描述**: 沒有統一的 API 文檔，前後端溝通困難

**建議**:
1. 使用 FastAPI 的自動文檔功能
2. 為每個端點添加詳細的 docstring
3. 建立 Swagger/OpenAPI 規範

---

## 📋 完整後端 API 端點分析

以下是所有後端 API 檔案的完整分析，標記活躍使用和可能棄用的端點。

---

## backend/app/api/auth.py

### 活躍 API (前端有使用)
- `/api/auth/sso` (POST) - SSO 單一登入 - **前端**: LoginPage.tsx
- `/api/auth/token` (POST) - 傳統登入（員工編號） - **前端**: LoginPage.tsx

### 可能棄用的 API (前端未使用)
- 無 - 所有 API 都有使用

---

## backend/app/api/users.py

### 活躍 API (前端有使用)
- `/api/users/profile` (GET) - 取得用戶個人資料 - **前端**: AuthContext.tsx

### 可能棄用的 API (前端未使用)
- `/api/users/subordinates` (GET) - 取得下屬列表 - **推測用途**: 主管功能，可能前端未實作
- `/api/users/permissions` (GET) - 取得用戶權限 - **推測用途**: 權限管理，可能前端未實作

---

## backend/app/api/reviews.py

### 活躍 API (前端有使用)
- `/api/reviews/submit` (POST) - 提交主管審閱（評分和回復） - **前端**: ChatInterface.tsx

### 可能棄用的 API (前端未使用)
- `/api/reviews/{daily_no}/status` (GET) - 取得指定日報的審閱狀態 - **推測用途**: 審閱狀態查詢
- `/api/forward/visors` (GET) - 取得轉寄職稱名單 - **推測用途**: 轉寄功能（可能前端未完全實作）
- `/api/forward/employees` (GET) - 取得轉寄員工名單 - **推測用途**: 轉寄功能（可能前端未完全實作）
- `/api/reports/acknowledge` (POST) - 確認已讀日報 - **實際端點**: 雖然前端有使用，但實際在 reviews.py 中實作

---

## backend/app/api/ai.py

### 活躍 API (前端有使用)
- `/api/ai/enhance_one/{daily_no}/{planno}/{sopno}` (POST) - AI 增強單個記錄 - **前端**: DailyReportTab.tsx

### 可能棄用的 API (前端未使用)
- `/api/ai/suggestions/{report_id}` (POST) - 取得日報的 AI 建議 - **推測用途**: AI 建議功能（已被 supervisor API 取代）
- `/api/ai/enhance_all` (POST) - 批量 AI 增強記錄 - **推測用途**: 批量潤飾功能（前端未使用）
- `/api/ai/status` (GET) - 取得 AI 服務狀態 - **推測用途**: 系統狀態監控

---

## backend/app/api/reports.py

### 活躍 API (前端有使用)
- `/api/reports/{report_id}/comments` (GET) - 取得日報的所有留言 - **前端**: ChatInterface.tsx
- `/api/reports/{report_id}` (DELETE) - 刪除日報 - **前端**: EmployeeListTab.tsx

### 可能棄用的 API (前端未使用)
- `/api/reports` (GET) - 取得日報列表（支援過濾） - **推測用途**: 日報查詢（可能被 supervisor API 取代）
- `/api/reports/{report_id}` (GET) - 取得單一日報詳情 - **推測用途**: 日報詳情（可能被 supervisor API 取代）
- `/api/reports/{report_id}/comments` (POST) - 發表日報留言 - **推測用途**: 留言功能（可能被 reviews API 取代）
- `/api/reports/{report_id}/approvals` (GET) - 取得日報的審核記錄 - **推測用途**: 審核記錄（可能被 supervisor API 取代）

**註**: reports.py 中的多個端點可能與 supervisor.py 功能重疊

---

## backend/app/api/drafts.py

### 活躍 API (前端有使用)
- `/api/drafts` (POST) - 保存日報暫存 - **前端**: DailyReportTab.tsx, DataInputTab.tsx
- `/api/drafts/{empno}` (GET) - 取得員工的暫存資料 - **前端**: DailyReportTab.tsx, DataInputTab.tsx
- `/api/drafts/by-daily-planno-sopno/{daily_no}/{planno}/{sopno}` (PUT) - 更新特定暫存記錄 - **前端**: DailyReportTab.tsx

### 可能棄用的 API (前端未使用)
- 無 - 所有 API 都有使用

---

## backend/app/api/legacy_reports.py

這個檔案非常龐大，包含多個 router (legacy, records, projects)

### 活躍 API (前端有使用)

#### Legacy Router (`/api/legacy/`)
- `/api/legacy/next-daily-no` (GET) - 取得新的日報編號 - **前端**: DailyReportTab, DataInputTab
- `/api/legacy/upload-daily-report` (POST) - 上傳日報到正式表 - **前端**: DailyReportTab.tsx
- `/api/legacy/daily-date-range` (GET) - 取得可填寫日報的日期範圍 - **前端**: DateSelector.tsx
- `/api/legacy/work-data` (GET) - 取得所有工作相關資料 - **推測**: 可能被前端使用

#### Records Router (`/api/records/`)
- `/api/records/consolidated/today` (GET) - 取得當日彙整記錄 - **前端**: DailyReportTab, DataInputTab
- `/api/records/writing-status` (GET) - 取得寫作狀態 - **前端**: App, DailyReportTab, DataInputTab, EmployeeListTab
- `/api/records/upload` (POST) - 檔案上傳 - **前端**: DailyReportTab.tsx
- `/api/records/delete/{year_month}/{filename}` (DELETE) - 刪除上傳檔案 - **前端**: DailyReportTab, DataInputTab

#### Projects Router (`/api/projects/`)
- `/api/projects/` (GET) - 取得專案列表 - **前端**: DailyReportTab.tsx

### 可能棄用的 API (前端未使用)

#### Legacy Router
- `/api/legacy/reports` (GET) - 取得日報列表 BY 工號（主管） - **推測用途**: 主管查詢（可能被 supervisor API 取代）
- `/api/legacy/reports/{daily_no}/content` (GET) - 取得日報內容詳細 - **推測用途**: 日報內容查詢
- `/api/legacy/work-plans` (GET) - 取得工作計畫 - **推測用途**: 工作計畫查詢
- `/api/legacy/companies` (GET) - 取得服務公司列表 - **推測用途**: 公司列表（可能被 work-data 包含）
- `/api/legacy/attachments` (POST) - 保存附件 - **推測用途**: 附件管理（可能棄用）
- `/api/legacy/api-status` (GET) - 獲取API配置狀態 - **推測用途**: 系統狀態監控
- `/api/legacy/work-items` (GET) - 取得工作項目列表 - **推測用途**: 工作項目查詢（可能被 work-data 包含）
- `/api/legacy/service-companies` (GET) - 取得服務公司列表（重用） - **推測用途**: 重複的公司列表 API
- `/api/legacy/test-tables` (GET) - 測試資料庫連接 - **推測用途**: 開發測試用途
- `/api/legacy/service-targets` (GET) - 取得服務對象列表 - **推測用途**: 服務對象查詢（可能被 work-data 包含）
- `/api/legacy/execution-works` (GET) - 取得執行工作和工作項目 - **推測用途**: 執行工作查詢（可能被 work-data 取代）

#### Records Router
- `/api/records/upload-record` (POST) - 上傳記錄（兼容性端點） - **推測用途**: 舊版上傳接口
- `/api/records/consolidated/{project_id}` (GET) - 取得特定項目的合併記錄 - **推測用途**: 專案記錄查詢
- `/api/records/` (POST) - 創建新記錄（兼容性端點） - **推測用途**: 舊版創建接口

**註**: legacy_reports.py 包含大量可能棄用的端點，建議整理並移除未使用的 API

---

## backend/app/api/supervisor.py

### 活躍 API (前端有使用)
- `/api/supervisor/has-subordinates` (GET) - 檢查當前用戶是否有下屬 - **前端**: AuthContext.tsx
- `/api/supervisor/reports/{report_id}` (GET) - 取得單一日報詳情 - **前端**: App.tsx, EmployeeDetailTab.tsx
- `/api/supervisor/reports/{report_id}/approvals` (GET) - 取得日報的審核資訊 - **前端**: EmployeeDetailTab.tsx
- `/api/supervisor/reports/{report_id}/ai-suggestions` (POST) - 生成 AI 建議 - **前端**: ChatInterface.tsx
- `/api/supervisor/daily-homepage` (GET) - 新的日報首頁 - **前端**: EmployeeListTab.tsx

### 可能棄用的 API (前端未使用)
- `/api/supervisor/employee-editing-status` (GET) - 取得員工編輯狀態 - **推測用途**: 編輯權限檢查（暫時返回允許編輯）
- `/api/supervisor/forward/candidates` (GET) - 取得轉寄名單 - **推測用途**: 轉寄功能（可能前端未完全實作）
- `/api/supervisor/files/download/{file_id}` (GET) - 下載檔案 - **推測用途**: 檔案下載（前端可能使用靜態路徑）
- `/api/supervisor/reports-by-date` (GET) - 取得指定日期的所有下屬日報 - **推測用途**: 主管日報查詢（可能被 daily-homepage 取代）

---

## 📊 統計摘要

### 總體統計
- **後端 API 檔案總數**: 8 個主要檔案
- **定義的 API 端點總數**: 約 60+ 個端點
- **前端活躍使用**: 約 25-30 個端點
- **可能棄用的端點**: 約 30-35 個端點

### 各檔案活躍度
1. **auth.py**: 2/2 (100%) - 全部活躍
2. **users.py**: 1/3 (33%) - 2 個未使用
3. **reviews.py**: 1/4 (25%) - 3 個未使用
4. **ai.py**: 1/4 (25%) - 3 個未使用
5. **reports.py**: 2/6 (33%) - 4 個未使用
6. **drafts.py**: 3/3 (100%) - 全部活躍
7. **legacy_reports.py**: 8/25+ (32%) - 約 17 個未使用
8. **supervisor.py**: 5/9 (56%) - 4 個未使用

### 高風險棄用區域
1. **legacy_reports.py** - 包含大量未使用的舊 API
2. **reports.py** - 與 supervisor.py 功能重疊
3. **ai.py** - 批量功能未使用
4. **reviews.py** - 轉寄相關功能未完全實作

---

## 🎯 重構建議

### Phase 1: 清理棄用 API (高優先級)
1. 標記所有未使用的 API 為 `@deprecated`
2. 在日誌中記錄任何對這些端點的訪問
3. 監控 1-2 週，確認真的沒有使用
4. 移除確認未使用的端點

**建議移除的端點**:
- `/api/legacy/reports` (GET) - 被 supervisor API 取代
- `/api/legacy/test-tables` (GET) - 開發測試用途
- `/api/ai/suggestions/{report_id}` (POST) - 被 supervisor AI 取代
- `/api/ai/enhance_all` (POST) - 批量功能未使用
- `/api/reports/{report_id}` (GET) - 被 supervisor API 取代

### Phase 2: 合併重複功能 (中優先級)
1. 合併 `reports.py` 和 `supervisor.py` 中重複的日報查詢功能
2. 統一轉寄功能到單一模組
3. 整合 AI 相關功能到統一接口

### Phase 3: 標準化 API 結構 (中優先級)
1. 統一 API 路徑命名規範（RESTful）
2. 縮短過長的路徑（使用 query parameters）
3. 建立 API 版本控制機制

### Phase 4: 優化性能 (高優先級)
1. 實作 `/api/records/writing-status` 的全域快取
2. 減少重複 API 呼叫
3. 考慮使用 WebSocket 進行即時狀態更新

### Phase 5: 文檔與監控 (中優先級)
1. 為每個活躍 API 添加完整的 docstring
2. 使用 FastAPI 自動生成 OpenAPI 文檔
3. 建立 API 使用監控儀表板
4. 記錄每個 API 的呼叫次數和響應時間

---

## 📁 建議的新檔案結構

### 簡化後的 API 結構
```
backend/app/api/
├── __init__.py
├── v1/                          # API 版本 1
│   ├── __init__.py
│   ├── auth.py                  # 認證 (保持不變)
│   ├── users.py                 # 用戶管理 (合併權限查詢)
│   ├── reports.py               # 日報管理 (合併 reports + supervisor)
│   ├── drafts.py                # 草稿管理 (保持不變)
│   ├── reviews.py               # 審閱與留言 (合併評論功能)
│   ├── ai.py                    # AI 功能 (整合所有 AI)
│   └── legacy.py                # 舊系統整合 (簡化)
└── deprecated/                  # 待移除的 API
    └── legacy_reports_old.py
```

---

## 🔄 遷移計劃

### Step 1: 標記階段 (Week 1-2)
- 為所有可能棄用的 API 添加 `@deprecated` 裝飾器
- 在響應中添加 `X-Deprecated: true` header
- 記錄所有訪問日誌

### Step 2: 通知階段 (Week 3-4)
- 通知前端團隊棄用的 API 列表
- 提供遷移指南
- 建立新的標準化 API

### Step 3: 移除階段 (Week 5-6)
- 確認無訪問後移除棄用 API
- 更新文檔
- 發布新版本

---

## 📝 結論

經過完整的後端 API 分析，發現：

1. ✅ **活躍使用的 API**: 約 25-30 個，主要集中在核心功能
2. ❌ **可能棄用的 API**: 約 30-35 個，大部分在 legacy_reports.py
3. ⚠️ **重複功能**: reports.py 與 supervisor.py 有顯著重疊
4. 🔧 **需要優化**: writing-status API 過度呼叫
5. 📚 **缺少文檔**: 大部分 API 缺乏詳細文檔

**下一步行動**:
1. 立即開始標記棄用 API
2. 監控 API 使用情況
3. 規劃 API 重構時間表
4. 建立完整的 API 文檔

---

**分析完成日期**: 2025-10-08
**下次審查日期**: 2025-11-08
