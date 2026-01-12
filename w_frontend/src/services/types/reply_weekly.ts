// frontend/src/services/types/reply_weekly.ts

/**
 * 回覆週報請求
 */
export interface ReplyWeeklyReportRequest {
  weekly_no: string; // 週報編號
  reply_memo: string; // 回覆內容
  score?: number | null; // 評分（1-5），主管評分時才有
  to_users: string[]; // 回覆給誰的 empno 列表
  forward_users: string[]; // 轉寄給誰的 empno 列表
}

/**
 * 回覆週報回應
 */
export interface ReplyWeeklyReportResponse {
  ResponseCmd: string;
  ResponseData: boolean;
  ResponseNo: string;
  ResponseNa: string;
}
