# 服務層重構與職責劃分計畫

**日期**: 2025-10-08
**目標**: 解決 `API_USAGE_ANALYSIS.md` 中指出的架構問題，建立清晰、可維護的服務層。

---

## 1. 執行摘要

目前的後端架構存在服務層職責不清、API 層過於臃腫（上帝物件）、以及隱藏的外部依賴等問題。這導致了程式碼難以理解、維護成本高昂、且不易測試。

本計畫旨在透過分階段的重構，將業務邏輯從 API 控制器中剝離，並集中到職責單一的 Service 層。我們將從最混亂的「記錄與草稿」功能開始，逐步將此模式推廣到「主管審閱」等其他模組，最終建立一個清晰、分層的後端架構。

---

## 2. 核心問題分析

我們在代碼審查中確定了三大結構性問題：

### 問題一：Service 層職責不清且使用不一致
大量的業務邏輯和資料庫查詢直接散落在 API 控制器中，而 Service 層的使用缺乏一致性。

*   **範例 A (已修正)**: 在重構前，`api/drafts.py` 的 `save` 操作呼叫 Service，而 `get` 和 `update` 操作則直接在 API 層操作資料庫。
*   **範例 B**: `api/supervisor.py` 中的 `get_daily_homepage_reports` 方法包含了超過 200 行的複雜 SQL 查詢，這使得 API 層與資料層緊密耦合。

### 問題二：隱藏的外部依賴
系統的關鍵功能依賴於呼叫外部編譯好的 C# 執行檔 (`.exe`)，這使得單純閱讀 Python 程式碼無法理解完整的業務流程。

*   **範例**: `services/daily_date_service.py` 透過 `subprocess.run` 呼叫 `DailyDateServiceJson.exe` 來獲取可用日期。

### 問題三：API 檔案職責過重 (上帝物件)
單一 API 檔案處理了過多不相關的功能，成為難以維護的「上帝物件」。

*   **範例**: `api/legacy_reports.py` 同時處理記錄讀取、最終日報提交、日期範圍、專案列表、檔案上傳等多種不同的業務，違反了單一職責原則。

---

## 3. 分階段重構方案

我們將採用循序漸進的方式進行重構，確保每一步都是一個穩定且可驗證的改進。

### ✅ Phase 1: 集中化「草稿」邏輯 (已完成)

我們已經成功完成了第一階段的重構，為後續工作建立了範本。

*   **行動**: 
    1.  建立 `services/draft_service.py`。
    2.  將所有與草稿相關的資料庫操作（新增、讀取、更新）從 `api/drafts.py` 和 `services/legacy_service_v2.py` 遷移到 `DraftService`。
    3.  重構 `api/drafts.py`，使其僅呼叫 `DraftService`。
    4.  從 `legacy_service_v2.py` 中移除已遷移的 `save_draft` 方法。
*   **狀態**: ✅ **已完成**。

---

### 🟡 Phase 2: 建立 `RecordService` 並重構 `legacy_reports.py` (下一步)

**目標**: 將 `api/legacy_reports.py` 中與 `/api/records` 路由相關的所有邏輯抽離出來。

*   **行動項目**:
    1.  **建立檔案**: 建立 `backend/app/services/record_service.py` 並定義 `RecordService` 類別。
    2.  **遷移讀取邏輯**: 將 `get_consolidated_today` 的邏輯遷移到 `RecordService`。
    3.  **遷移狀態邏輯**: 將 `get_writing_status` 的邏輯遷移到 `RecordService`（內部仍會呼叫 `DailyDateService`）。
    4.  **遷移檔案邏輯**: 將 `upload_file` 和 `delete_upload` 的檔案操作邏輯遷移到 `RecordService`。
    5.  **重構 API 層**: 重構 `legacy_reports.py` 中的 `/api/records` 路由，使其所有端點都呼叫新的 `RecordService`。

---

### 🟡 Phase 3: 建立 `SupervisorService` 並重構 `supervisor.py` (計畫中)

**目標**: 將 `api/supervisor.py` 中的複雜查詢和業務邏輯抽離到專屬的 Service。

*   **行動項目**:
    1.  **建立檔案**: 建立 `backend/app/services/supervisor_service.py` 並定義 `SupervisorService` 類別。
    2.  **遷移首頁邏輯**: 將 `get_daily_homepage_reports` 的複雜 SQL 查詢和處理邏輯遷移到 `SupervisorService`。
    3.  **遷移詳情邏輯**: 將 `get_report_detail` 的邏輯遷移到 `SupervisorService`。
    4.  **重構 API 層**: 重構 `api/supervisor.py`，使其端點呼叫新的 `SupervisorService`。

---

### 🟡 Phase 4: 最終清理與退役 (計畫中)

**目標**: 在所有功能都被遷移到新的 Service 後，安全地移除舊的、職責混亂的檔案。

*   **行動項目**:
    1.  **分析殘餘**: 分析 `legacy_reports.py` 和 `legacy_service_v2.py` 中剩餘的方法。
    2.  **遷移或刪除**: 將仍有用的邏輯遷移到合適的 Service，或直接刪除未使用的程式碼。
    3.  **退役檔案**: 安全刪除 `legacy_reports.py` 和 `legacy_service_v2.py`。

---

## 4. 預期效益

*   **提升程式碼品質**: 程式碼將更易於閱讀、理解和維護。
*   **清晰的職責分離**: API 層只負責路由和參數驗證，Service 層負責業務邏輯，資料層負責數據存取。
*   **簡化測試**: 職責單一的 Service 更容易進行單元測試。
*   **降低技術債務**: 消除「上帝物件」和重複程式碼，為未來的功能擴展打下良好基礎。

---

## 5. 下一步

建議立即開始執行 **Phase 2: 建立 `RecordService` 並重構 `legacy_reports.py`**。

我將等待您的確認後開始執行。
