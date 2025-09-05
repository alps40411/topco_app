# API 重組計劃

## 目標
重新組織 API 端點，遵循 RESTful 設計原則，提供清晰的命名和一致的結構。

## 新的 API 結構

### 1. 認證相關 (`/api/auth`)
```
POST   /api/auth/login              # 登入
POST   /api/auth/refresh           # 刷新 token
POST   /api/auth/logout            # 登出
GET    /api/auth/me                # 取得當前用戶資訊
```

### 2. 用戶管理 (`/api/users`)
```
GET    /api/users/profile          # 取得個人資料
PUT    /api/users/profile          # 更新個人資料
GET    /api/users/subordinates     # 取得下屬列表
GET    /api/users/permissions      # 取得用戶權限
```

### 3. 日報管理 (`/api/reports`)
```
# 日報CRUD
GET    /api/reports                # 取得日報列表（支援查詢參數）
GET    /api/reports/{report_id}    # 取得單一日報詳情
POST   /api/reports                # 創建新日報
PUT    /api/reports/{report_id}    # 更新日報
DELETE /api/reports/{report_id}    # 刪除日報

# 日報狀態管理
POST   /api/reports/{report_id}/submit     # 提交日報
POST   /api/reports/{report_id}/withdraw   # 撤回日報

# 日報查詢
GET    /api/reports/my             # 我的日報
GET    /api/reports/subordinates   # 下屬日報
GET    /api/reports/by-date        # 按日期查詢日報
```

### 4. 草稿管理 (`/api/drafts`)
```
GET    /api/drafts                 # 取得草稿列表
GET    /api/drafts/{draft_id}      # 取得草稿詳情
POST   /api/drafts                 # 保存草稿
PUT    /api/drafts/{draft_id}      # 更新草稿
DELETE /api/drafts/{draft_id}      # 刪除草稿
POST   /api/drafts/{draft_id}/submit   # 提交草稿為正式日報
```

### 5. 審閱管理 (`/api/reviews`)
```
# 審閱操作
POST   /api/reviews                # 提交審閱（評分+回應）
GET    /api/reviews/{report_id}    # 取得日報的所有審閱記錄
GET    /api/reviews/{report_id}/my-review  # 取得我的審閱記錄

# 快速操作
POST   /api/reviews/{report_id}/score    # 快速評分
POST   /api/reviews/{report_id}/comment  # 快速留言
```

### 6. 工作計畫管理 (`/api/work-plans`)
```
GET    /api/work-plans             # 取得工作計畫列表
GET    /api/work-plans/{plan_id}   # 取得工作計畫詳情
GET    /api/work-plans/{plan_id}/execution-works  # 取得計畫的執行工作
```

### 7. 執行工作管理 (`/api/execution-works`)
```
GET    /api/execution-works        # 取得執行工作列表
GET    /api/execution-works/{work_id}/items    # 取得工作項目列表
```

### 8. 服務對象管理 (`/api/service-targets`)
```
GET    /api/service-targets/companies    # 取得服務公司列表
GET    /api/service-targets/employees    # 取得服務人員列表
```

### 9. 轉發管理 (`/api/forwards`)
```
GET    /api/forwards/candidates    # 取得轉發候選人
POST   /api/forwards               # 執行轉發操作
```

### 10. 系統管理 (`/api/system`)
```
GET    /api/system/status          # 系統狀態
GET    /api/system/config          # 系統配置
GET    /api/system/health          # 健康檢查
```

## 命名規範

### URL 命名
- 使用小寫字母和連字符
- 使用複數名詞作為資源名稱
- 遵循 RESTful 慣例

### 參數命名
- `report_id` 統一用於日報 ID
- `employee_id` 統一用於員工 ID  
- `plan_id` 統一用於工作計畫 ID
- `work_id` 統一用於執行工作 ID

### 響應格式
- 成功：`{ success: true, data: ..., message?: string }`
- 錯誤：`{ success: false, error: string, details?: any }`
- 列表：`{ success: true, data: [], total?: number, page?: number }`

## HTTP 狀態碼使用
- 200: 成功
- 201: 創建成功
- 400: 請求錯誤
- 401: 未認證
- 403: 無權限
- 404: 資源不存在
- 422: 驗證失敗
- 500: 服務器錯誤

## 遷移策略

### 第一階段：新 API 實現
1. 創建新的路由文件
2. 實現新的服務層
3. 保持舊 API 繼續運行

### 第二階段：前端更新
1. 更新前端 API 調用
2. 測試新 API 功能
3. 確保功能正常

### 第三階段：舊 API 清理
1. 標記舊 API 為 deprecated
2. 移除未使用的舊端點
3. 清理重複代碼

## 向後兼容性
在遷移過程中，保持現有 API 端點的功能，直到前端完全遷移到新 API。