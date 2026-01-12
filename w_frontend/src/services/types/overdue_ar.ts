// frontend/src/services/types/overdue_ar.ts

export interface OverdueARData {
  empno: string;
  deptno: string;
  year: number;
  week_no: number;
  data_date?: string;
  last_updatetime?: string;
  cocode?: string;
  coabbv?: string;  // 公司簡稱
  abbv_c?: string;  // 客戶簡稱
  doc_type?: string;
  doc_no?: string;  // 銷貨單號
  invoice?: string;  // 發票號碼
  doc_date?: string;  // 銷貨日
  ppay_date?: string;  // 預計付款日
  curr?: string;  // 幣別
  curramt2?: number;  // 原幣餘額
}

export interface OverdueARResponse {
  ResponseCmd: string;
  ResponseData: OverdueARData[];
  ResponseNo: string;
  ResponseNa: string;
}
