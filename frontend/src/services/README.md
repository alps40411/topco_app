# API 服務使用指南

本目錄包含所有前端 API 服務，提供統一、型別安全的 API 調用方式。

---

## 📁 目錄結構

```
services/
├── apiClient.ts          # API 客戶端基礎類別
├── draftsApi.ts          # 草稿管理 API
├── recordsApi.ts         # 記錄管理 API
├── workDataApi.ts        # 工作資料 API
├── datesApi.ts           # 日期管理 API
├── legacyApi.ts          # 舊版 API (逐步棄用)
└── types/                # 型別定義
    ├── common.ts
    ├── draft.ts
    ├── record.ts
    ├── report.ts
    ├── workData.ts
    ├── user.ts
    ├── date.ts
    └── index.ts
```

---

## 🚀 快速開始

### 1. 基本使用

```typescript
import { DraftsApi, RecordsApi, WorkDataApi } from '@/services';
import { useAuth } from '@/hooks/useAuth';

function MyComponent() {
  const { authFetch } = useAuth();

  const handleSaveDraft = async () => {
    try {
      const result = await DraftsApi.save({
        daily_no: '12345',
        empno: '001',
        cocode: 'A',
        doc_date: '20251009',
        draft_type: 'TEMP',
        draft_content: { /* ... */ }
      }, authFetch);

      console.log('成功:', result);
    } catch (error) {
      console.error('錯誤:', error.message);
    }
  };

  return <button onClick={handleSaveDraft}>保存草稿</button>;
}
```

### 2. 使用型別定義

```typescript
import type { DraftSaveRequest, SubmitResponse } from '@/services/types';

// 使用型別定義確保資料正確
const draftData: DraftSaveRequest = {
  daily_no: '12345',
  empno: '001',
  cocode: 'A',
  doc_date: '20251009',
  draft_type: 'TEMP',
  draft_content: {}
};

// TypeScript 會自動檢查回傳型別
const submitReport = async (): Promise<SubmitResponse> => {
  return await RecordsApi.submit('20251009', authFetch);
};
```

---

## 📚 API 服務說明

### DraftsApi - 草稿管理

處理日報草稿的保存、讀取、更新和刪除。

```typescript
import { DraftsApi } from '@/services/draftsApi';

// 保存草稿
const result = await DraftsApi.save(draftData, authFetch);

// 取得員工的草稿列表
const drafts = await DraftsApi.getByEmployee(empno, docDate, 'TEMP', authFetch);

// 更新草稿
await DraftsApi.update(dailyNo, planno, sopno, updateData, authFetch);

// 刪除草稿
await DraftsApi.delete(draftId, authFetch);

// AI 草稿
const aiResult = await DraftsApi.saveAIDraft(aiDraftData, authFetch);
const aiDrafts = await DraftsApi.getAIDrafts(empno, authFetch);
```

---

### RecordsApi - 記錄管理

處理日報記錄、檔案上傳和日報提交。

```typescript
import { RecordsApi } from '@/services/recordsApi';

// 取得今日記錄
const todayRecords = await RecordsApi.getToday(docDate, authFetch);

// 取得合併的今日記錄
const consolidated = await RecordsApi.getConsolidatedToday(docDate, authFetch);

// 取得特定項目的記錄
const projectRecord = await RecordsApi.getConsolidatedByProject(projectId, authFetch);

// 上傳檔案
const uploadResult = await RecordsApi.uploadFile(file, docDate, authFetch);

// 刪除檔案
await RecordsApi.deleteFile('202510', 'filename.jpg', authFetch);

// 提交日報
const submitResult = await RecordsApi.submit(docDate, authFetch);
```

---

### WorkDataApi - 工作資料

取得專案、執行工作、服務公司和服務對象等工作相關資料。

```typescript
import { WorkDataApi } from '@/services/workDataApi';

// 取得所有工作資料（推薦）
const {
  projects,
  executionWorks,
  serviceCompanies,
  serviceTargets
} = await WorkDataApi.getAll(authFetch);

// 或單獨取得
const projects = await WorkDataApi.getProjects(authFetch);
const works = await WorkDataApi.getExecutionWorks(authFetch);
const companies = await WorkDataApi.getServiceCompanies(authFetch);
const targets = await WorkDataApi.getServiceTargets(authFetch);
```

---

### DatesApi - 日期管理

處理日期範圍、日報編號和日期格式轉換。

```typescript
import { DatesApi } from '@/services/datesApi';

// 取得日期範圍
const dateRange = await DatesApi.getRange(authFetch);

// 取得下一個日報編號
const { daily_no } = await DatesApi.getNextDailyNo(authFetch);

// 日期格式化工具
const formatted = DatesApi.formatDateForApi(new Date());
// 輸出: '20251009'

const date = DatesApi.parseDateFromApi('20251009');
// 輸出: Date object
```

---

## 🔧 ApiClient - API 客戶端

所有 API 服務的基礎，提供統一的請求處理。

```typescript
import { apiClient, createAuthApiClient } from '@/services/apiClient';

// 使用預設客戶端（無認證）
const data = await apiClient.get('/api/some-endpoint');

// 使用認證客戶端
const authClient = createAuthApiClient(authFetch);

// GET 請求
const getData = await authClient.get('/api/endpoint', {
  param1: 'value1',
  param2: 'value2'
});

// POST 請求
const postData = await authClient.post('/api/endpoint', {
  key: 'value'
});

// PUT 請求
const putData = await authClient.put('/api/endpoint', {
  key: 'value'
});

// DELETE 請求
await authClient.delete('/api/endpoint');

// 檔案上傳
const uploadResult = await authClient.uploadFile(
  '/api/upload',
  file,
  { doc_date: '20251009' }
);
```

---

## 🎯 最佳實踐

### 1. 使用 useAuth Hook

```typescript
import { useAuth } from '@/hooks/useAuth';
import { WorkDataApi } from '@/services/workDataApi';

function MyComponent() {
  const { authFetch } = useAuth();

  useEffect(() => {
    const loadData = async () => {
      const data = await WorkDataApi.getAll(authFetch);
      // ...
    };
    loadData();
  }, [authFetch]);
}
```

### 2. 錯誤處理

```typescript
try {
  const result = await DraftsApi.save(draftData, authFetch);
  toast.success('保存成功!');
} catch (error) {
  // error 包含 message, status, detail 屬性
  console.error('保存失敗:', error.message);

  if (error.status === 401) {
    // 未授權，可能需要重新登入
  } else if (error.status === 400) {
    // 請求資料有誤
    toast.error(error.detail || '資料格式錯誤');
  } else {
    // 其他錯誤
    toast.error('操作失敗，請稍後再試');
  }
}
```

### 3. 在 Context 中使用

```typescript
import { createContext, useContext, useState, useEffect } from 'react';
import { WorkDataApi } from '@/services/workDataApi';
import type { WorkPlan, ExecutionWork } from '@/services/types';

interface WorkDataContextType {
  projects: WorkPlan[];
  executionWorks: ExecutionWork[];
  isLoading: boolean;
  refetch: () => Promise<void>;
}

const WorkDataContext = createContext<WorkDataContextType | undefined>(undefined);

export function WorkDataProvider({ children }) {
  const [projects, setProjects] = useState<WorkPlan[]>([]);
  const [executionWorks, setExecutionWorks] = useState<ExecutionWork[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const { authFetch } = useAuth();

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const data = await WorkDataApi.getAll(authFetch);
      setProjects(data.projects);
      setExecutionWorks(data.executionWorks);
    } catch (error) {
      console.error('載入工作資料失敗:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <WorkDataContext.Provider value={{
      projects,
      executionWorks,
      isLoading,
      refetch: fetchData
    }}>
      {children}
    </WorkDataContext.Provider>
  );
}

export const useWorkData = () => {
  const context = useContext(WorkDataContext);
  if (!context) {
    throw new Error('useWorkData must be used within WorkDataProvider');
  }
  return context;
};
```

---

## ⚠️ 常見錯誤

### 1. 忘記傳入 authFetch

```typescript
// ❌ 錯誤 - 需要認證的 API 沒有傳入 authFetch
const data = await WorkDataApi.getAll();

// ✅ 正確
const { authFetch } = useAuth();
const data = await WorkDataApi.getAll(authFetch);
```

### 2. 不處理錯誤

```typescript
// ❌ 錯誤 - 沒有錯誤處理
const data = await DraftsApi.save(draftData, authFetch);

// ✅ 正確
try {
  const data = await DraftsApi.save(draftData, authFetch);
} catch (error) {
  console.error('保存失敗:', error);
  // 顯示錯誤訊息給用戶
}
```

### 3. 不使用型別定義

```typescript
// ❌ 錯誤 - 沒有使用型別定義
const draftData = {
  daily_no: '123',
  // 可能漏掉必填欄位
};

// ✅ 正確
import type { DraftSaveRequest } from '@/services/types';

const draftData: DraftSaveRequest = {
  daily_no: '123',
  empno: '001',
  cocode: 'A',
  doc_date: '20251009',
  // TypeScript 會提示缺少的欄位
  draft_type: 'TEMP',
  draft_content: {}
};
```

---

## 🔗 相關文件

- [MIGRATION_GUIDE.md](../../MIGRATION_GUIDE.md) - 從舊 API 遷移指南
- [API_REFACTORING_PLAN.md](../../API_REFACTORING_PLAN.md) - 重構計畫
- [REFACTORING_SUMMARY.md](../../REFACTORING_SUMMARY.md) - 重構總結

---

## 📞 支援

如有問題或建議，請：
1. 查閱本文件和相關指南
2. 檢查型別定義文件
3. 聯繫開發團隊
