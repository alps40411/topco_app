# 週報編輯頁 - 自動暫存與預覽功能實現方案

## 一、自動暫存功能

### 需求規格

| 項目 | 決定 |
|------|------|
| 套用範圍 | 新增和編輯模式都支援 |
| 暫存方式 | 每 1 分鐘自動儲存 draft 到後端 |
| 新增模式 | 第一次儲存後追蹤 seq，後續使用 updateNote |
| 部分草稿 | 需選擇工作項目且有內容才儲存 |
| 提示方式 | 顯示小提示「已自動儲存」 |
| 畫面更新 | 編輯模式同步更新本地狀態，避免閃爍 |

### 實現邏輯

#### 新增模式自動儲存流程

```
用戶點「新增筆記」
    ↓
開始編輯（newNoteSeqRef = null）
    ↓
1 分鐘後自動儲存觸發
    ↓
調用 saveDraft → 取得新的 seq
    ↓
記住 seq（newNoteSeqRef.current = seq）
    ↓
後續自動儲存 → 使用 updateNote(seq)
    ↓
用戶點「保存」→ 使用 updateNote(seq) 完成保存
用戶點「取消」→ 詢問用戶：
    - 「確定」→ 保留草稿，重新載入列表
    - 「取消」→ 刪除該 draft
```

#### 編輯模式自動儲存流程

```
用戶點「編輯」某筆筆記
    ↓
開始編輯（已有 seq）
    ↓
1 分鐘後自動儲存觸發
    ↓
調用 updateNote(seq)
    ↓
同步更新本地狀態（不重新載入）
```

---

## 二、預覽功能

### 需求規格

| 項目 | 決定 |
|------|------|
| 呈現方式 | 全螢幕 Modal 彈窗 |
| 樣式 | **完全複用 EmployeeDetailTab 的樣式結構** |
| 內容 | 完整週報：員工資訊 + 營收表 + 應收帳款表 + 所有筆記 |
| 按鈕位置 | 編輯頁，始終顯示（無筆記時禁用） |
| 數據來源 | 當前頁面的 weeklyNotes 資料（草稿） |
| 排除內容 | 不顯示回覆區域、評分區域、轉寄選擇器 |
| 標識 | 標題旁顯示「預覽」標籤 |

### UI 結構（與 EmployeeDetailTab 相同）

```
┌─────────────────────────────────────────────────────────────┐
│  [X 關閉]  00001 王小明 2024年 第3週 週報 [預覽]            │
│            資訊部                                           │
├─────────────────────────────────────────────────────────────┤
│  營收達成率表格 (RevenueTable)                               │
├─────────────────────────────────────────────────────────────┤
│  逾期應收帳款表格 (OverdueARTable)                           │
├─────────────────────────────────────────────────────────────┤
│  週報內容                                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ [工作重點] [專案進度報告]                              │  │
│  │ 內容（富文本渲染）                                      │  │
│  │ 附件列表                                               │  │
│  └───────────────────────────────────────────────────────┘  │
│  (重複顯示所有筆記)                                          │
│                                                             │
│  ❌ 不顯示：回覆區域、評分、轉寄選擇器                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、修改的檔案清單

### 新增檔案
| 檔案路徑 | 說明 |
|----------|------|
| `w_frontend/src/hooks/useAutoSave.ts` | 自動儲存 Hook |
| `w_frontend/src/components/WeeklyReportPreviewModal.tsx` | 預覽彈窗組件（複用 EmployeeDetailTab 樣式） |

### 修改檔案
| 檔案路徑 | 修改內容 |
|----------|----------|
| `w_frontend/src/components/WeeklyReportTab.tsx` | 整合自動儲存（新增+編輯）、預覽按鈕、取消詢問邏輯 |

---

## 四、關鍵代碼說明

### useAutoSave Hook

```typescript
export function useAutoSave({
  interval = 60000,  // 預設 1 分鐘
  onSave,            // 儲存函數
  enabled = true,    // 是否啟用
  hasContent,        // 檢查是否有內容可儲存
}: AutoSaveOptions)
```

### 新增模式的 seq 追蹤

```typescript
// 追蹤新增筆記的 seq（用於自動儲存後的更新）
const newNoteSeqRef = useRef<number | null>(null);

// 自動儲存時
if (newNoteSeqRef.current) {
  // 已有 seq，更新
  await WeeklyReportApi.updateNote(weeklyNo, newNoteSeqRef.current, formData, authFetch);
} else {
  // 第一次儲存，取得 seq
  const result = await WeeklyReportApi.saveDraft(formData, authFetch, weeklyNo);
  if (result?.seq) {
    newNoteSeqRef.current = result.seq;
  }
}
```

### 取消時詢問用戶

```typescript
const cancelAddNew = async () => {
  if (newNoteSeqRef.current && weeklyNo) {
    const userChoice = window.confirm(
      "此筆記已自動儲存。\n\n按「確定」保留草稿，按「取消」刪除草稿。"
    );

    if (!userChoice) {
      // 刪除草稿
      await WeeklyReportApi.deleteNote(weeklyNo, newNoteSeqRef.current, authFetch);
    } else {
      // 保留草稿，重新載入列表
      await loadWeeklyNotes();
    }
  }
  resetNewNoteForm();
};
```

---

## 五、測試要點

### 自動暫存測試

1. **新增模式**
   - 新增筆記，輸入內容，等待 1 分鐘，確認自動儲存
   - 確認第一次儲存後 seq 被記住
   - 再等 1 分鐘，確認使用 updateNote 更新而非新增
   - 點擊「取消」，確認彈出詢問對話框
   - 選擇「確定」→ 保留草稿，列表顯示該筆記
   - 選擇「取消」→ 刪除草稿

2. **編輯模式**
   - 編輯現有筆記，修改內容，等待 1 分鐘
   - 確認自動儲存成功
   - 確認畫面不閃爍（本地狀態同步更新）

### 預覽功能測試

1. 點擊預覽按鈕，確認彈窗正確開啟
2. 確認樣式與 EmployeeDetailTab 一致
3. 確認顯示「預覽」標籤
4. 確認顯示員工資訊、營收表、應收帳款表、所有筆記
5. 確認不顯示回覆區域、評分、轉寄選擇器
6. 確認關閉按鈕正常運作（點擊 X、按 Escape、點擊背景）
