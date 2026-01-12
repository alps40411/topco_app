// frontend/src/services/types/date.ts
/**
 * 日期相關型別定義
 */

export interface DateRange {
  start_date: string; // YYYYMMDD
  end_date: string;   // YYYYMMDD
  current_date?: string;
}

export interface NextDailyNoResponse {
  daily_no: string;
}
