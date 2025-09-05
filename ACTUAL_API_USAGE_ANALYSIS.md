# 前端實際使用的 API 端點分析

## 認證相關 API
- 在 AuthContext 中處理，沒有直接 authFetch 調用

## 實際使用的 API 端點列表

### 1. 主管功能相關 (`/api/supervisor/`)
```
GET  /api/supervisor/has-subordinates          # 檢查是否有下屬
GET  /api/supervisor/employee-editing-status   # 取得編輯狀態
GET  /api/supervisor/reports/{reportId}        # 取得日報詳情
GET  /api/supervisor/reports/{reportId}/approvals  # 取得審核資訊
GET  /api/supervisor/reports-by-date           # 按日期取得下屬日報
GET  /api/supervisor/my-reports-by-date        # 取得我的日報
POST /api/supervisor/reports/submit            # 提交日報
POST /api/supervisor/reports/{reportId}/ai-suggestions  # AI 建議
```

### 2. 日報評論相關 (`/api/reports/`)
```
GET  /api/reports/{reportId}/comments          # 取得留言
POST /api/reports/{reportId}/comments          # 發表留言
```

### 3. 審閱相關 (`/api/reviews/`)
```
POST /api/reviews/submit                       # 提交審閱
```

### 4. 記錄相關 (`/api/records/`)
```
GET  /api/records/consolidated/today           # 取得今日合併記錄
GET  /api/records/writing-status               # 取得寫作狀態
POST /api/records/upload                       # 上傳記錄
POST /api/records/                            # 創建記錄
POST /api/records/ai/enhance_one/{projectId}   # AI 增強單個記錄
POST /api/records/ai/enhance_all              # AI 增強所有記錄
PUT  /api/records/consolidated/{editingProjectId}  # 更新合併記錄
```

### 5. 項目相關 (`/api/projects/`)
```
GET  /api/projects/                           # 取得項目列表
```

### 6. Legacy 相關 (`/api/legacy/`)
```
GET  /api/legacy/next-daily-no                # 取得下一個日報編號
POST /api/legacy/drafts                       # 保存草稿
```

### 7. 轉發相關 (`/api/forward/`)
```
GET  /api/forward/visors                      # 取得職稱轉寄名單
GET  /api/forward/employees                   # 取得員工轉寄名單
```

## 功能分類與重構建議

### 保留並優化的端點（高使用頻率）
1. **主管功能** - 需要重構命名
2. **日報管理** - 需要整合分散的功能
3. **記錄管理** - 需要清理重複功能
4. **審閱系統** - 保持現有結構

### 需要整合的重複功能
1. 日報提交功能分散在多個端點
2. 記錄上傳功能有多個版本
3. AI 功能分散

### 未使用或可簡化的功能
1. 複雜的 legacy API 中大部分未被使用
2. 某些 records API 功能重複

## 重構優先級

### 第一優先級（核心功能）
- 日報 CRUD 操作整合
- 主管審閱功能優化
- 用戶權限檢查

### 第二優先級（支援功能）
- AI 功能整合
- 轉發功能優化
- 記錄上傳統一

### 第三優先級（清理）
- 移除未使用的 legacy 端點
- 統一響應格式
- 錯誤處理標準化

## 建議的新 API 結構（基於實際使用）

### 認證 (`/api/auth/`)
```
POST /api/auth/login
GET  /api/auth/profile
```

### 用戶管理 (`/api/users/`)
```
GET  /api/users/permissions
GET  /api/users/subordinates
```

### 日報管理 (`/api/reports/`)
```
GET    /api/reports                    # 取得日報列表（整合現有查詢功能）
GET    /api/reports/{id}               # 取得日報詳情
POST   /api/reports                    # 創建/提交日報
PUT    /api/reports/{id}               # 更新日報
GET    /api/reports/{id}/comments      # 取得留言
POST   /api/reports/{id}/comments      # 發表留言
GET    /api/reports/{id}/approvals     # 取得審核記錄
```

### 草稿管理 (`/api/drafts/`)
```
GET    /api/drafts                     # 取得草稿列表
POST   /api/drafts                     # 保存草稿
PUT    /api/drafts/{id}               # 更新草稿
DELETE /api/drafts/{id}               # 刪除草稿
```

### 審閱管理 (`/api/reviews/`)
```
POST   /api/reviews                    # 提交審閱
```

### AI 服務 (`/api/ai/`)
```
POST   /api/ai/suggestions/{reportId}  # 取得 AI 建議
POST   /api/ai/enhance/{recordId}     # AI 增強記錄
POST   /api/ai/enhance-batch          # 批量 AI 增強
```

### 轉發管理 (`/api/forwards/`)
```
GET    /api/forwards/candidates        # 取得轉發候選人
```

### 項目管理 (`/api/projects/`)
```
GET    /api/projects                   # 取得項目列表
```