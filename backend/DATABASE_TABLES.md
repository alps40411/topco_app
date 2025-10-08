# 資料庫表名稱參考

## ✅ 正確的資料表名稱

### 主要資料表
- `jps.tjp_master` - 工作計畫主檔 (欄位: planno, plan_subj_c)
- `jps.tpm_sop` - 執行工作主檔 (欄位: sopno, sop_desc_c)
- `jps.tpm_sop_detail` - 工作項目明細 (欄位: sopno, seq, name)
- `jps.dcd003$master` - 員工主檔
- `jps.dcd002$master` - 部門主檔
- `jps.dcd001$master` - 公司主檔

### 日報相關資料表
- `jps.tdr_master` - 日報主檔
- `jps.tdr_detail1` - 日報明細1
- `jps.tdr_detail2` - 日報明細2
- `jps.tdr_draft` - 日報草稿

### 回覆相關資料表
- `jps.tdr_reply` - 回覆記錄
- `jps.tdr_reply_detail` - 回覆明細
- `jps.TDR_REPLY_GENERAL_COMMENT` - 罐頭訊息主檔
- `jps.TDR_REPLY_SPECIAL_COMMENT` - 特殊訊息記錄

### 其他資料表
- `jps.tdr_score` - 評分記錄
- `jps.tdr_msg_send_log` - 轉寄記錄
- `jps.tdr_upload_file` - 附件檔案
- `jps.groupfoodchn` - 主管群組
- `jps.diarysupers` - 日報主管

## ❌ 常見錯誤的表名稱

| 錯誤名稱 | 正確名稱 | 說明 |
|---------|---------|------|
| `jps.tpm_plan_master` | `jps.tjp_master` | 工作計畫主檔 |
| `jps.tpm_sop_master` | `jps.tpm_sop` | 執行工作主檔 |

## 📋 服務公司/對象欄位對照

### tdr_draft (草稿表)
- `SERVICE_COCODE` - 服務公司別
- `SERVICE_EMPNO` - 服務對象工號
- `SERVICE_EMPNAMEC` - 服務對象姓名
- `SERVICE_DEPTNO` - 服務對象部門

### tdr_detail2 (已送出日報)
- `PPS_SERVECOCODE` - 服務公司別
- `PPS_EMPNO` - 服務對象工號
- `PPS_EMPNAMEC` - 服務對象姓名
- `PPS_COCODE` - 服務對象公司別
- `PPS_DEPTNO` - 服務對象部門

## 🔍 查詢範例

### 查詢工作計畫名稱
```sql
SELECT plan_subj_c FROM jps.tjp_master WHERE planno = :planno
```

### 查詢執行工作名稱
```sql
SELECT sop_desc_c FROM jps.tpm_sop WHERE sopno = :sopno
```

### 查詢工作項目名稱
```sql
SELECT name FROM jps.tpm_sop_detail WHERE sopno = :sopno AND seq = :seq
```

### 查詢已送出日報的服務資料
```sql
SELECT
    PPS_SERVECOCODE as service_cocode,
    PPS_EMPNO as service_empno,
    PPS_EMPNAMEC as service_empnamec
FROM jps.tdr_detail2
WHERE daily_no = :daily_no
```

### 查詢草稿的服務資料
```sql
SELECT
    SERVICE_COCODE,
    SERVICE_EMPNO,
    SERVICE_EMPNAMEC
FROM jps.tdr_draft
WHERE daily_no = :daily_no
```
