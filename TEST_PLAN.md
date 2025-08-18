## 測試計畫（Topco App）

本計畫涵蓋後端 API、服務層單元測試、前端 UI 互動與端對端驗證。優先以後端 API 與關鍵服務為主，逐步擴增前端測試。

### 一、測試範疇

- 後端
  - 驗證與授權：`/api/auth/token`
  - 使用者：`/api/users/*`
  - 專案、紀錄、主管、文件 OCR 等 API
  - 服務層：`user_service`、`records_service`、`document_analysis_service`、`azure_ai_service`
- 前端
  - 關鍵頁面與流程：登入、員工清單、工作紀錄、新增/編輯/上傳附件、AI 產出日報

### 二、測試環境

- Windows 10/11
- Python 3.11+，Node 18+
- 本機或測試資料庫（PostgreSQL）
- `.env` 使用測試金鑰與測試資料庫

### 三、測試類型與工具

- 後端單元/整合測試：pytest、pytest-asyncio、httpx（AsyncClient）
- 前端元件/單元測試（選擇性）：Vitest + React Testing Library
- 端對端（E2E）（選擇性）：Playwright

### 四、測試資料

- `seed_db.py` 會建立：
  - 使用者：`employee@example.com`、`supervisor@example.com`（密碼 `password123`）
  - 預設專案 8 筆

### 五、後端測試案例（範例）

1. Auth
   - 成功登入取得 token（200）
   - 錯誤密碼/不存在帳號（401）
2. Users
   - 帶 token 取得自己資訊（200）
   - 未帶 token（401）
3. Records/Projects
   - 新增、查詢、更新、刪除（CRUD）
4. Document Intelligence
   - 上傳測試檔（以小檔或 mock 取代，避免成本）
5. Azure AI 生成報告
   - 使用小輸入與 mock 回傳，驗證輸出格式與錯誤處理

### 六、前端測試重點（手動/自動）

- 手動冒煙測試：
  - 登入 → 導向首頁 → 清單載入 → 新增/編輯紀錄 → 上傳附件 → 觸發 AI 產出
- 自動化（選擇性）：
  - Vitest：元件渲染、狀態切換、表單驗證
  - Playwright：登入流程與主要操作腳本

### 七、執行方式

- 後端（建議建立開發測試依賴）：

```powershell
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx
pytest -q | cat
```

- 前端（若加入 vitest）：

```powershell
cd frontend
npm i -D vitest @testing-library/react @testing-library/jest-dom
npm run test
```

### 八、驗收標準（範例）

- 後端關鍵 API 測試通過率 ≥ 90%
- 冒煙測試全通過
- 主要缺陷（P0/P1）全數關閉
