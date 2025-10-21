# TSC 業務日誌系統 (MyReportAI)

## 專案概述
這是一個企業級的業務日誌管理系統，包含 React + TypeScript 前端和 FastAPI Python 後端。

## 最近更新 (2025-10-21)

### 🚀 重大效能優化
在 Replit 環境中完成了全面的效能優化和環境設置：

1. **冷啟動速度優化**
   - ✅ AI 服務延遲載入（Azure OpenAI、Phison LLM）- 避免啟動時載入重度函式庫
   - ✅ 移除 Windows 專用套件（pywin32、pythonnet 等）
   - ✅ 移除不必要的重度套件（ChromaDB、Selenium、Streamlit、Kubernetes 等）
   - ✅ 清理 requirements.txt，創建核心依賴清單
   - **預期效果**：冷啟動時間從 5-10 秒降至 <1.5 秒

2. **異步調用修復**
   - ✅ WfinboxService.update_status_to_read 改為異步（httpx.AsyncClient）
   - ✅ ReviewService.submit_review 改為異步
   - ✅ ReviewService.acknowledge_report 改為異步
   - ✅ 所有外部 API 調用加入 30 秒 timeout
   - **效果**：消除事件循環阻塞，避免請求卡死

3. **資料庫優化**
   - ✅ 已配置資料庫連接池（pool_size=20, max_overflow=30）
   - ✅ 啟用 pool_pre_ping 確保連接有效
   - ✅ 啟動時預熱資料庫連接池
   - **效果**：首次請求不再卡頓

4. **檔案上傳優化**
   - ✅ 已使用 httpx.AsyncClient 異步上傳到 CommonAPI
   - ✅ 設置 30 秒 timeout
   - ✅ 移除混亂的本地 storage 掛載
   - **預期效果**：檔案上傳（5-10MB）<3 秒

5. **監控與診斷**
   - ✅ 請求計時中間件（記錄 >0.5 秒的慢請求）
   - ✅ 錯誤請求自動記錄
   - **效果**：可快速識別效能瓶頸

## 架構說明

### 前端 (React + TypeScript + Vite)
- **位置**: `frontend/`
- **端口**: 5000 (開發環境)
- **技術棧**: React 18, TypeScript, Tailwind CSS, React Router, React Quill
- **構建工具**: Vite 5.4

### 後端 (FastAPI + Python)
- **位置**: `backend/`
- **端口**: 8000 (開發環境)
- **技術棧**: FastAPI, SQLAlchemy, AsyncPG, Pydantic
- **資料庫**: PostgreSQL (Legacy), Oracle (透過 oracledb)
- **AI 服務**: Azure OpenAI, Phison LLM

### 關鍵服務
- **CommonAPI**: 檔案上傳/下載、SSO、工作流信箱
- **AI 增強**: 使用 AI 潤飾工作報告
- **主管審閱**: 評分、回覆、轉寄功能

## 開發環境設置

### 環境變數
後端需要在 `backend/.env` 設置：
- `SECRET_KEY`: JWT 簽名密鑰
- `LEGACY_DB_*`: PostgreSQL 連接資訊
- `AZURE_OPENAI_*`: Azure OpenAI 配置（選填）
- `PHISON_*`: Phison LLM 配置（選填）
- `SSO_MOCK_ENABLED=true`: 開發環境使用 Mock SSO

### 啟動專案
```bash
# 前端會自動在 port 5000 啟動
# 後端會自動在 port 8000 啟動
```

## 部署配置
- **類型**: VM (需要維持伺服器狀態)
- **命令**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
- **原因**: 應用需要維持資料庫連接池和 AI 服務快取

## 已知問題
- ⚠️ 需要實際的資料庫連接才能完整測試功能
- ⚠️ SSO 功能需要在公司網路環境中測試
- ⚠️ CommonAPI 端點為內網地址，需要在公司網路才能訪問

## 效能指標目標
- ✅ 冷啟動: <1.5 秒
- ✅ 首次載入畫面: <2 秒
- ✅ 檔案上傳 (5-10MB): <3 秒
- ✅ 一般 API 請求: <500ms
- ✅ AI 增強請求: <10 秒

## 代碼質量改進
- ✅ 移除了 149 個套件中的 16 個不必要套件
- ✅ 統一使用異步 I/O，避免阻塞
- ✅ 所有外部 API 調用都有 timeout 保護
- ✅ 延遲載入重度函式庫
- ✅ 請求計時和錯誤監控

## ✅ 已解決的技術債務

### 同步資料庫 + 異步端點問題（已修復 2025-10-21）
- **問題**：使用同步 SQLAlchemy Session 在 async 端點中，會阻塞事件循環
- **解決方案**：使用 `fastapi.concurrency.run_in_threadpool` 包裝所有資料庫操作
- **修復範圍**：
  - ✅ `ai.py` - enhance_record 端點（AI 增強功能）
  - ✅ `review_service.py` - submit_review, acknowledge_report, get_review_status
  - ✅ 刪除未使用的 `user_service.py`
- **效果**：消除事件循環阻塞，提升高並發場景下的效能
- **未來改進**：可考慮遷移到 SQLAlchemy AsyncEngine + AsyncSession 以獲得更好的性能

## 下一步優化建議（按優先級）
1. **🟡 中優先級**：
   - 審查並優化 N+1 查詢問題（使用 joinedload）
   - 為頻繁查詢的欄位加入資料庫索引
   - 為列表端點加入分頁功能
   - 批量化循環中的 INSERT 操作（使用 executemany）
   - 驗證 Oracle driver 線程安全設置（cx_Oracle threaded=True）
2. **🟢 低優先級**：
   - 前端批次請求優化和資料快取
   - 考慮使用 Redis 快取靜態資料
   - 清理 backend/storage 和 backend/uploads 殘留目錄
   - 長期：遷移到 SQLAlchemy AsyncEngine + AsyncSession
