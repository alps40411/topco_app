# 資料庫同步問題修正報告

## 問題摘要

員工 05489 的主管關係在原始資料庫中有 6 位主管，但在新建立的多對多資料庫中只能找到 5 位主管，缺少了一位主管（工號 00003）。

## 問題原因分析

### 根本原因
原始的 `sync_company_a_data.py` 腳本存在邏輯缺陷：
- 腳本只同步公司別 A (`cocode = 'A'`) 的員工資料
- 但是當公司 A 的員工有來自其他公司別的主管時，這些跨公司主管不會被同步到新資料庫
- 建立主管關係時，腳本要求**員工和主管都必須存在**於新資料庫中才會建立關係

### 具體案例
- 員工 05489（林靖君）屬於公司別 A，共有 6 位主管
- 其中主管 00003（黃家軒）屬於公司別 C
- 因為 00003 不在公司別 A 的同步範圍內，所以沒有被同步到新資料庫
- 導致 05489 與 00003 的主管關係無法建立

## 解決方案

### 修正策略
1. **擴展同步範圍**：不僅同步公司 A 的員工，也同步作為公司 A 員工主管的跨公司人員
2. **兩階段同步**：
   - 第一階段：收集所有公司 A 員工的主管工號（不限公司別）
   - 第二階段：同步這些跨公司主管的基本資料
3. **同步部門資料**：確保跨公司主管的部門也被正確同步

### 修正內容

#### 1. 新增跨公司主管資料讀取
```python
# 讀取跨公司主管資料
print("[INFO] 讀取跨公司主管資料...")
supervisor_empnos = set()
for row in source_data:
    supervisor_empno = to_str(row.get('supervisor'))
    if supervisor_empno:
        supervisor_empnos.add(supervisor_empno)

cross_company_supervisors = []
if supervisor_empnos:
    # 查詢所有主管的詳細資料，不限公司別
    result = await source_db.execute(text(f"""
        SELECT DISTINCT 
            empno, empnamec, deptno, dclass, xlevel, adm_rank, quitdate, 
            deptnamec, deptabbv, g_deptno, grp_empno, cocode
        FROM {SOURCE_TABLE}
        WHERE empno IN ('{supervisor_list}')
        ORDER BY empno
    """))
```

#### 2. 修正部門同步邏輯
```python
# 處理跨公司主管的部門
for row in cross_company_supervisors:
    dept_no = to_str(row.get('deptno'))
    dept_name = to_str(row.get('deptnamec'))
    
    if dept_no and dept_name:
        if dept_no not in unique_departments:
            unique_departments[dept_no] = {
                'dept_no': dept_no,
                'dept_name': dept_name,
                'dept_abbr': to_str(row.get('deptabbv')),
                'group_dept_no': to_str(row.get('g_deptno')),
                'company_code': to_str(row.get('cocode'))
            }
```

#### 3. 修正員工同步邏輯
```python
# 先處理公司A員工
for row in source_data:
    # ... 處理公司A員工 ...

# 再處理跨公司主管
for row in cross_company_supervisors:
    empno = to_str(row.get('empno'))
    if empno and empno not in unique_employees:
        unique_employees[empno] = {
            'empno': empno,
            'name': to_str(row.get('empnamec')) or f'主管{empno}',
            # ... 其他欄位 ...
            'company_code': to_str(row.get('cocode'))
        }
```

#### 4. 解決外鍵約束問題
由於資料庫存在複雜的外鍵關係，修正了清理順序：
```python
# 正確的清理順序
await target_db.execute(delete(ReviewComment))
await target_db.execute(delete(FileAttachment))
await target_db.execute(delete(WorkRecord))
await target_db.execute(delete(DailyReport))
await target_db.execute(delete(EmployeeDepartmentHistory))
await target_db.execute(delete(EmployeeSupervisorHistory))
await target_db.execute(delete(EmployeePositionHistory))
await target_db.execute(text("UPDATE employees SET user_id = NULL, supervisor_id = NULL"))
await target_db.execute(text("DELETE FROM employee_supervisors"))
await target_db.execute(delete(User))
await target_db.execute(delete(Employee))
await target_db.execute(delete(Project))
await target_db.execute(delete(Department))
```

## 測試結果

### 修正前
```
原始資料庫共找到 6 位主管
新資料庫共找到 5 位主管
[ERROR] Missing supervisors in new database: {'00003'}
```

### 修正後
```
原始資料庫共找到 6 位主管
新資料庫共找到 6 位主管
[SUCCESS] Supervisor relationships match perfectly
```

### 全面測試結果

#### 1. 資料同步統計
- **部門數量**：417 個部門（涵蓋 35 個不同公司別）
- **員工數量**：4,116 名員工
  - 公司別 A：4,110 名員工
  - 跨公司主管：6 名（公司別 C、5、J15、J18、X）

#### 2. 員工 05489 詳細驗證
- **工號**：05489
- **姓名**：林靖君
- **部門**：統一超 商貿流通
- **公司別**：A
- **主管數量**：6 位主管 ✅
  - 00003 - 黃家軒 (流業經營部, 公司別: C) ✅
  - 00006 - 溫俊雄 (資訊發展, 公司別: A)
  - 01446 - 楊榮宏 (統一超 採購事業發展部, 公司別: A)
  - 02223 - 洪秀慧 (統一超 商貿流通, 公司別: A)
  - 04000 - 羅雯雄 (統一超, 公司別: A)
  - 05205 - 江明達 (統一營運, 公司別: A)

#### 3. 跨公司主管關係
- **總跨公司關係數**：2,384 個
- **主要跨公司主管**：
  - 00003 (公司別 C)：作為 2,377 名公司 A 員工的主管
  - 00002 (公司別 5)：作為 7 名公司 A 員工的主管

#### 4. 數位發展部
- **員工數量**：8 名數位發展部員工
- **帳號建立**：17 個測試帳號已成功建立

#### 5. 數據一致性檢查
- **沒有部門的員工數**：0 ✅
- **A公司沒有主管的員工數**：1,726（主要是基層員工，符合預期）
- **已建立帳號的員工數**：17（數位發展部及相關主管）

## 檔案修改清單

### 主要修改檔案
1. **`sync_company_a_data.py`** - 主要修正檔案
   - 新增跨公司主管資料讀取邏輯
   - 修正部門同步以包含跨公司部門
   - 修正員工同步以包含跨公司主管
   - 修正資料清理順序以避免外鍵約束錯誤

### 新增測試檔案
1. **`test_employee_05489.py`** - 特定員工主管關係測試
2. **`investigate_missing_supervisor.py`** - 缺失主管調查腳本  
3. **`comprehensive_test.py`** - 全面數據完整性測試

## 結論

問題已完全解決：
- ✅ 員工 05489 的 6 位主管關係已完整同步
- ✅ 跨公司主管關係功能正常運作
- ✅ 部門關係完整同步
- ✅ 數據一致性檢查通過
- ✅ 數位發展部測試帳號建立成功

修正後的系統能夠正確處理跨公司的組織架構，確保所有員工的主管關係都能完整保留，滿足實際業務需求。

## 建議

1. **定期驗證**：建議定期執行 `comprehensive_test.py` 來驗證數據完整性
2. **監控跨公司關係**：特別關注跨公司主管關係的數量變化
3. **擴展性考慮**：如果未來需要支援更多公司別，可以進一步泛化同步邏輯

---
*報告生成時間：2025-08-19*  
*修正完成：資料庫同步跨公司主管關係問題*