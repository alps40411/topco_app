# 服務公司/對象資料完整化重構計劃

## 一、問題分析

### 1.1 現有問題
- **tdr_draft 表欄位不足**：只有 `service_cocode`, `service_empno`, `service_empnamec`, `service_deptno`，缺少服務對象公司別
- **資料不完整**：無法完整記錄服務對象的所有資訊
- **顯示問題**：
  - 服務公司顯示代碼而非中文名稱
  - 服務對象名稱未正確顯示
- **設計不一致**：tdr_draft 和 tdr_detail2 的欄位設計不一致

### 1.2 Work Data API 提供的完整資料
```json
{
  "cocode": "5",
  "coabbv": "崇越福委",
  "deptno": "00000",
  "deptabbv": "崇越福委會",
  "empno": "U0077",
  "empnamec": "林育伶"
}
```

### 1.3 tdr_detail2 的欄位（正式資料）
- `PPS_SERVECOCODE` - 服務公司別
- `PPS_EMPNO` - 服務對象工號
- `PPS_EMPNAMEC` - 服務對象姓名
- `PPS_COCODE` - 服務對象公司別 ⭐
- `PPS_DEPTNO` - 服務對象部門

---

## 二、資料庫修改方案

### 2.1 tdr_draft 表需要新增的欄位

**新增欄位：**
```sql
ALTER TABLE jps.tdr_draft
ADD COLUMN service_target_cocode VARCHAR(10);  -- 服務對象公司別
```

**完整欄位列表（修改後）：**
- `service_cocode` - 服務公司別（保持不變）
- `service_empno` - 服務對象工號（保持不變）
- `service_empnamec` - 服務對象姓名（保持不變）
- `service_deptno` - 服務對象部門（保持不變）
- `service_target_cocode` - **服務對象公司別（新增）** ⭐

### 2.2 對應關係

| tdr_draft 欄位 | tdr_detail2 欄位 | 說明 |
|---------------|-----------------|------|
| service_cocode | PPS_SERVECOCODE | 服務公司別 |
| service_target_cocode | PPS_COCODE | 服務對象公司別 ⭐ |
| service_empno | PPS_EMPNO | 服務對象工號 |
| service_empnamec | PPS_EMPNAMEC | 服務對象姓名 |
| service_deptno | PPS_DEPTNO | 服務對象部門 |

---

## 三、需要修改的程式碼

### 3.1 前端修改

#### A. ServiceSelector.tsx
**目前：**
```typescript
onCompanyChange={(cocode) => setServiceCocode(cocode)}
onTargetChange={(empno) => setServiceEmpno(empno)}
```

**修改為：**
```typescript
interface ServiceCompany {
  cocode: string;
  coabbv: string;
}

interface ServiceTarget {
  empno: string;
  empnamec: string;
  cocode: string;      // ⭐ 新增
  deptno: string;
}

onCompanyChange={(company: ServiceCompany | null) => {
  // 傳遞完整公司資訊
}}

onTargetChange={(target: ServiceTarget | null) => {
  // 傳遞完整對象資訊，包含 cocode
}}
```

#### B. DailyReportTab.tsx
**新增狀態：**
```typescript
const [editServiceTargetCocode, setEditServiceTargetCocode] = useState<string | undefined>();
```

**修改介面：**
```typescript
interface DraftRecord extends Omit<WorkRecordCreate, "service_company_id" | "service_target_id"> {
  service_cocode?: string;
  service_empno?: string;
  service_target_cocode?: string;  // ⭐ 新增
}
```

#### C. App.tsx (ConsolidatedReport 介面)
```typescript
export interface ConsolidatedReport {
  // ... 其他欄位
  service_cocode?: string;
  service_company_name?: string;  // 中文名稱
  service_empno?: string;
  service_target_name?: string;
  service_target_cocode?: string;  // ⭐ 新增
  service_deptno?: string;         // ⭐ 新增
}
```

### 3.2 後端修改

#### A. drafts.py

**1. 更新 PUT 端點（第104-106行）：**
```python
service_cocode = update_data.get('service_cocode', '')
service_empno = update_data.get('service_empno', '')
service_target_cocode = update_data.get('service_target_cocode', '')  # ⭐ 新增
service_deptno = update_data.get('service_deptno', '')  # ⭐ 新增
```

**2. 移除自動查詢姓名的邏輯（第154-163行）：**
```python
# ❌ 刪除這段 - 前端直接傳完整資料
# service_empnamec = ""
# if service_empno:
#     emp_sql = text(...)
#     ...

# ✅ 改為直接從前端接收
service_empnamec = update_data.get('service_empnamec', '')
```

**3. 更新 UPDATE SQL（第171-189行）：**
```python
UPDATE jps.tdr_draft
SET ...
    SERVICE_COCODE = :service_cocode,
    SERVICE_EMPNO = :service_empno,
    SERVICE_EMPNAMEC = :service_empnamec,
    SERVICE_TARGET_COCODE = :service_target_cocode,  -- ⭐ 新增
    SERVICE_DEPTNO = :service_deptno,                -- ⭐ 新增
    ...
```

#### B. legacy_reports.py

**1. 查詢 SQL（第543-546行）：**
```python
SELECT d.DAILY_NO, d.CONTENT, d.PLANNO, d.PLAN_SUBJ_C, d.SOPNO, d.SOP_DESC_C,
       d.WORK_ITEM_SEQ, d.SERVICE_COCODE, d.SERVICE_EMPNO, d.SERVICE_EMPNAMEC,
       d.SERVICE_TARGET_COCODE, d.SERVICE_DEPTNO,  -- ⭐ 新增這兩個欄位
       d.EXECUTION_TIME_MINUTES, d.FILES, d.AI_CONTENT, d.STATUS
FROM jps.tdr_draft d
```

**2. 處理邏輯（第572-574行）：**
```python
service_cocode = row[7] or ""
service_empno = row[8] or ""
service_empnamec = row[9] or ""
service_target_cocode = row[10] or ""  # ⭐ 新增
service_deptno = row[11] or ""         # ⭐ 新增
execution_time_minutes = row[12] or 0  # 索引調整
files_json = row[13] or "[]"           # 索引調整
ai_content = row[14]                   # 索引調整
status = row[15]                       # 索引調整
```

**3. 查詢服務公司中文名稱：**
```python
# 查詢服務公司中文名稱
service_company_name = service_cocode
if service_cocode:
    company_sql = text("""
        SELECT coabbv FROM jps.dcd001$master
        WHERE cocode = :cocode
    """)
    company_result = db.execute(company_sql, {"cocode": service_cocode}).fetchone()
    if company_result:
        service_company_name = company_result[0]
```

**4. 返回資料（第657-659行）：**
```python
"service_cocode": service_cocode,
"service_company_name": service_company_name,  # ⭐ 中文名稱
"service_empno": service_empno,
"service_target_name": service_target_name,
"service_target_cocode": service_target_cocode,  # ⭐ 新增
"service_deptno": service_deptno,                # ⭐ 新增
```

**5. 上傳邏輯（第1342-1345行）：**
```python
"service_cocode": draft[10],           # SERVICE_COCODE
"service_empno": draft[11],            # SERVICE_EMPNO
"service_deptno": draft[13],           # SERVICE_DEPTNO
"service_empnamec": draft[12],         # SERVICE_EMPNAMEC
# 索引需要根據新增欄位調整
```

#### C. supervisor.py

**已完成 ✅** - 已經正確從 tdr_detail2 讀取 PPS 欄位

---

## 四、執行步驟

### Step 1: 資料庫修改
```sql
ALTER TABLE jps.tdr_draft
ADD COLUMN service_target_cocode VARCHAR(10);
```

### Step 2: 後端修改（依序）
1. ✅ drafts.py - 更新 PUT endpoint
2. ✅ legacy_reports.py - 更新查詢和處理邏輯
3. ✅ legacy_service_v2.py - 更新 save_draft 邏輯

### Step 3: 前端修改（依序）
1. ✅ App.tsx - 更新 ConsolidatedReport 介面
2. ✅ ServiceSelector.tsx - 修改為傳遞完整物件
3. ✅ DailyReportTab.tsx - 更新狀態和處理邏輯
4. ✅ EmployeeDetailTab.tsx - 更新顯示邏輯（已完成服務公司/對象顯示）

### Step 4: 測試
1. ✅ 新增日報時選擇服務對象
2. ✅ 編輯日報時修改服務對象
3. ✅ 上傳日報後查看服務對象顯示
4. ✅ 確認服務公司顯示中文名稱

---

## 五、風險評估

### 5.1 向後相容性
- ❌ **舊資料問題**：已存在的 tdr_draft 記錄沒有 service_target_cocode
- ✅ **解決方案**：欄位允許 NULL，舊資料自動為 NULL

### 5.2 資料一致性
- ⚠️ **上傳時的對應**：確保從 draft 上傳到 detail2 時，欄位正確對應
  - draft.service_cocode → detail2.PPS_SERVECOCODE
  - draft.service_target_cocode → detail2.PPS_COCODE ⭐

### 5.3 測試重點
- [ ] 選擇服務對象時，所有欄位都正確儲存
- [ ] 編輯時，所有欄位都正確載入和更新
- [ ] 上傳後，detail2 的所有 PPS 欄位都正確
- [ ] 服務公司顯示中文名稱
- [ ] 服務對象顯示正確格式："姓名(工號)"

---

## 六、SQL 索引調整對照表

### legacy_reports.py 的 SELECT 語句調整

**修改前（第543-546行）：**
```python
# 索引: 0   1       2      3           4      5
#       6            7              8              9
#       10                   11     12          13
SELECT d.DAILY_NO, d.CONTENT, d.PLANNO, d.PLAN_SUBJ_C, d.SOPNO, d.SOP_DESC_C,
       d.WORK_ITEM_SEQ, d.SERVICE_COCODE, d.SERVICE_EMPNO, d.SERVICE_EMPNAMEC,
       d.EXECUTION_TIME_MINUTES, d.FILES, d.AI_CONTENT, d.STATUS
```

**修改後：**
```python
# 索引: 0   1       2      3           4      5
#       6            7              8              9
#       10                    11             12
#       13     14          15
SELECT d.DAILY_NO, d.CONTENT, d.PLANNO, d.PLAN_SUBJ_C, d.SOPNO, d.SOP_DESC_C,
       d.WORK_ITEM_SEQ, d.SERVICE_COCODE, d.SERVICE_EMPNO, d.SERVICE_EMPNAMEC,
       d.SERVICE_TARGET_COCODE, d.SERVICE_DEPTNO,  -- ⭐ 新增
       d.EXECUTION_TIME_MINUTES, d.FILES, d.AI_CONTENT, d.STATUS
```

**索引變化：**
- service_cocode: row[7] (不變)
- service_empno: row[8] (不變)
- service_empnamec: row[9] (不變)
- service_target_cocode: row[10] ⭐ 新增
- service_deptno: row[11] ⭐ 新增
- execution_time_minutes: row[10] → row[12] ⚠️
- files_json: row[11] → row[13] ⚠️
- ai_content: row[12] → row[14] ⚠️
- status: row[13] → row[15] ⚠️

---

## 七、檢查清單

### 資料庫
- [ ] 執行 ALTER TABLE 新增欄位

### 後端 API
- [ ] drafts.py - PUT endpoint 接收新欄位
- [ ] drafts.py - UPDATE SQL 包含新欄位
- [ ] legacy_reports.py - SELECT 包含新欄位
- [ ] legacy_reports.py - 索引調整
- [ ] legacy_reports.py - 查詢服務公司中文名稱
- [ ] legacy_reports.py - 返回資料包含新欄位
- [ ] legacy_reports.py - 上傳邏輯正確對應到 detail2
- [ ] legacy_service_v2.py - save_draft 包含新欄位

### 前端元件
- [ ] App.tsx - ConsolidatedReport 介面更新
- [ ] ServiceSelector.tsx - 回調改為傳遞完整物件
- [ ] DailyReportTab.tsx - 新增狀態變數
- [ ] DailyReportTab.tsx - 處理服務對象變更
- [ ] DailyReportTab.tsx - 編輯時載入完整資料
- [ ] DailyReportTab.tsx - 儲存時傳遞完整資料
- [ ] EmployeeDetailTab.tsx - 服務公司顯示中文

### 測試項目
- [ ] 新增日報 → 選擇服務對象 → 儲存草稿 → 檢查資料庫
- [ ] 編輯日報 → 修改服務對象 → 儲存 → 檢查資料庫
- [ ] 草稿上傳 → 檢查 tdr_detail2 的 PPS 欄位
- [ ] 查看已上傳日報 → 確認服務公司/對象正確顯示
- [ ] 服務公司顯示中文名稱，非代碼
