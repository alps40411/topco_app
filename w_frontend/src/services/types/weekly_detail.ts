// frontend/src/services/types/weekly_detail.ts

/**
 * 週報主檔
 */
export interface WeeklyReportMaster {
  cocode?: string;
  empno?: string;
  empname?: string; // 員工姓名
  doc_date?: string; // YYYYMMDD
  classify?: string;
  deptno?: string;
  deptabbv?: string; // 部門名稱（小寫）
  DEPTABBV?: string; // 部門名稱（大寫，相容舊格式）
  emergency?: string;
  week_no?: string;
  XUSER?: string; // 使用者名稱
  reply_status?: string;
  JOB_ITEM?: string; // 工作項目
  YY?: string; // 年份
  Week_No?: string; // 週次
  xdate?: string; // 最後修改日期 YYYYMMDD
  xtime?: string; // 最後修改時間 HH:MM:SS
  reviewers?: string[]; // 可評分主管工號陣列
}

/**
 * 週報明細
 */
export interface WeeklyReportDetail {
  weekly_no?: string;
  yy?: string; // 年份
  week_no?: string; // 週次
  cocode_g?: string;
  cocode?: string;
  empno?: string;
  doc_date?: string; // YYYYMMDD
  seq?: string; // 序號
  subject?: string; // 主旨
  job_item?: string; // 工作項目
  projno?: string;
  planno?: string;
  cuno?: string;
  suno?: string;
  cateno1?: string;
  cateno2?: string;
  cateno3?: string;
  cateno4?: string;
  content4?: string;
  xuser?: string; // 建立者
  xdate?: string; // 建立日期 YYYYMMDD
  xtime?: string; // 建立時間 HH:MM:SS
  sdate?: string; // 開始日期 YYYYMMDD
  edate?: string; // 結束日期 YYYYMMDD
  deptno?: string;
  content1?: string;
  content2?: string;
  content?: string; // 內容
}

/**
 * 週報回覆
 */
export interface WeeklyReportReply {
  weekly_no?: string;
  reply_nos?: string; // 回覆編號
  score?: string; // 評分（1-5）
  empno?: string;
  memo?: string; // 回覆內容
  xuser?: string; // 回覆者名稱
  xdate?: string; // 回覆日期 YYYYMMDD
  xtime?: string; // 回覆時間 HH:MM:SS
  memo_1?: string;
  memo_2?: string;
  from_where?: string;
}

/**
 * ShowWeeklyReport API 回傳的資料結構
 */
export interface ShowWeeklyReportResponseData {
  weeklyReportMaster: WeeklyReportMaster;
  weeklyReportDetails: WeeklyReportDetail[];
  weeklyReportReplies: WeeklyReportReply[];
}

/**
 * ShowWeeklyReport API 完整回傳結構
 */
export interface ShowWeeklyReportResponse {
  ResponseCmd: string;
  ResponseData: ShowWeeklyReportResponseData;
  ResponseNo: string;
  ResponseNa: string;
}
